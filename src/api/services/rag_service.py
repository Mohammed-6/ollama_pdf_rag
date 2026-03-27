"""RAG query service."""
import json
import os
from typing import List, Dict, Tuple, Optional
from sqlalchemy.orm import Session
from datetime import datetime

from langchain_ollama import ChatOllama
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
import ollama
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from src.api.helpers.action import plan_action
from src.api.helpers.azure_file_upload import extract_upload_parameters
from src.api.helpers.fast_rag_pipeline import FastRAGService
from src.api.helpers.llm_client import chat_completion
try:
    from langchain_chroma import Chroma
except ImportError:
    from langchain_community.vectorstores import Chroma
from langchain_ollama import OllamaEmbeddings

from ..database import PDFMetadata, ChatSession, ChatMessage
from ..config import settings
from ..helpers.classify_intent import classify_intent, Intent
from openai import AzureOpenAI


azure_client = AzureOpenAI(
    api_key=os.getenv("AZURE_API_KEY"),
    azure_endpoint=os.getenv("AZURE_API_BASE"),
    api_version="2024-05-01-preview" # Use a supported API version
)


class RAGService:
    """Service for RAG operations."""

    def __init__(self):
        """Initialize RAG service."""
        self.persist_directory = settings.VECTOR_DB_DIR

    def query_multi_pdf(
        self,
        question: str,
        model: str,
        pdf_ids: Optional[List[str]] = None,
        file: bytes = None,
        share_name: Optional[str] = None,
        db: Session = None
    ) -> Tuple[str, List[Dict], List[str]]:
        """Query across multiple PDFs with source attribution.

        Args:
            question: User question
            model: LLM model to use
            pdf_ids: List of PDF IDs to query (None = all PDFs)
            db: Database session

        Returns:
            Tuple of (answer, sources, reasoning_steps)
        """
        reasoning_steps = []

        # uploaded file handling (if file is provided, we assume i`t's a new PDF to be processed and queried)
        if file:
            reasoning_steps.append("📎 File uploaded with the question. (File handling not implemented in this snippet.)")
            extract = extract_upload_parameters(question, file, share_name)
            print(f"Extracted upload parameters: {extract}")
            if(extract):
                reasoning_steps.append("✅ Successfully extracted parameters from uploaded file.")
                return str(extract), [], reasoning_steps

        
        query = db.query(PDFMetadata)
        if pdf_ids:
            print(f"🔍 Filtering by pdf_ids: {pdf_ids}")
            query = query.filter(PDFMetadata.pdf_id.in_(pdf_ids))
        else:
            print("🔍 No pdf_ids provided - querying ALL PDFs")

        pdfs = query.all()
        # print(f"Total PDFs found: {pdf_ids}")
        # return "RAG query processing not implemented in this snippet.", [], reasoning_steps
        if pdfs and pdf_ids is not None:
            # Cache embeddings and vector dbs globally
            if not hasattr(self, '_embeddings_cache'):
                endpoint = settings.AZURE_EMBEDDING_ENDPOINT
                deployment = settings.AZURE_EMBEDDING_DEPLOYMENT
                api_version = settings.AZURE_EMBEDDING_API_VERSION
                client = AzureOpenAIEmbeddings(
                    azure_endpoint=endpoint,
                    api_key=settings.AZURE_EMBEDDING_API_KEY,
                    api_version=api_version,
                    azure_deployment=deployment,
                    chunk_size=30
                )
                self._embeddings_cache = client

            if not hasattr(self, '_vector_dbs_cache'):
                self._vector_dbs_cache = {}

            reasoning_steps.append(f"📚 Searching across {len(pdfs)} PDF(s): {', '.join([p.name for p in pdfs])}")

            reasoning_steps.append(f"🤖 Using AzureOpenAI: {settings.OPENAI_MODEL}")

            # Pre-load vector dbs (unchanged)
            all_docs = []
            embeddings = self._embeddings_cache

            def load_vector_db(pdf):  # Unchanged
                try:
                    if pdf.collection_name not in self._vector_dbs_cache:
                        self._vector_dbs_cache[pdf.collection_name] = Chroma(
                            persist_directory=self.persist_directory,
                            embedding_function=embeddings,
                            collection_name=pdf.collection_name
                        )
                    vector_db = self._vector_dbs_cache[pdf.collection_name]
                    retriever = vector_db.as_retriever(search_kwargs={"k": 5})
                    docs = retriever.invoke(question)
                    
                    for doc in docs:
                        doc.metadata.setdefault("pdf_name", pdf.name)
                        doc.metadata.setdefault("pdf_id", pdf.pdf_id)
                    return docs
                except Exception as e:
                    reasoning_steps.append(f"⚠️ Error retrieving from {pdf.name}: {str(e)}")
                    return []


            # Parallel retrieval (unchanged)
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=min(4, len(pdfs))) as executor:
                futures = [executor.submit(load_vector_db, pdf) for pdf in pdfs]
                for future in futures:
                    all_docs.extend(future.result())

            reasoning_steps.append(f"📊 Total chunks retrieved: {len(all_docs)}")

            # Context preparation (unchanged)
            context_parts = []
            for doc in all_docs[:5]:
                source = doc.metadata.get("pdf_name", "Unknown")
                context_parts.append(f"[Source: {source}]\n{doc.page_content}")
            formatted_context = "\n---\n".join(context_parts)

            # ⚡ DIRECT Azure ChatCompletions (no LangChain overhead)
            def azure_chat(context, question):
                messages = [
                            {
                                "role": "system",
                                "content": """You are a helpful assistant.

                                RULES:
                                1. If the answer is found in the provided Context, answer using it and cite sources like [Source: PDF_NAME].
                                2. If the Context does NOT contain the answer, use your general knowledge to answer.
                                3. When using general knowledge, clearly say: "Based on general knowledge".
                                4. Do NOT hallucinate or invent sources.
                                5. Keep the answer concise."""
                            },
                            {
                                "role": "user",
                                "content": f"Context:\n{context}\n\nQuestion: {question}"
                            }
                        ]
                
                response = azure_client.chat.completions.create(
                    model=settings.OPENAI_MODEL,  # "gpt-4o-mini"
                    messages=messages,
                    temperature=0,
                    max_tokens=1500,
                    stream=False
                )
                return response.choices[0].message.content

            reasoning_steps.append("⚡ Fast AzureOpenAI RAG...")
            response = azure_chat(formatted_context, question)

            return response, [], reasoning_steps




        # rag = FastRAGService(persist_directory=self.persist_directory)
        # answer = rag.query(
        #     question=question,
        #     pdf_ids=pdf_ids
        # )
        # return answer, [], reasoning_steps

        print("No PDFs found, running direct LLM answer...")
        # Classify intent of the user question
        intent = classify_intent(question)
        reasoning_steps.append(f"🕵️ Classified intent: {intent}")
        # return intent, [], reasoning_steps
        print(f"Classified intent: {intent}")
        # If intent is not DOCUMENT_QA, return early with clarification
        if intent == Intent.ACTION:
            reasoning_steps.append("❗ Intent is ACTION.")
            plan = plan_action(question)
            # plan = "Processing action intent. (Action planning not implemented in this snippet.)"

            # print(plan)
            return plan, [], reasoning_steps
        
        if not pdfs and intent != Intent.DOCUMENT_QA:
            reasoning_steps.append("⚠️ No PDFs found to query.")
            reasoning_steps.append(" Intent is Question.")
            ans = self.run_direct_llm_answer(question)
            return ans["answer"], [], reasoning_steps
        
        if intent == Intent.GENERAL_QA:
            reasoning_steps.append(" Intent is Question.")
            ans = self.run_direct_llm_answer(question)
            return ans["answer"], [], reasoning_steps



        return "Proceeding with DOCUMENT_QA intent.", [], reasoning_steps
        reasoning_steps.append(f"📚 Searching across {len(pdfs)} PDF(s): {', '.join([p.name for p in pdfs])}")

        # Initialize LLM
        llm = AzureChatOpenAI(deployment_name=model)
        reasoning_steps.append(f"🤖 Using model: {model}")

        # Query prompt for multi-query retriever
        QUERY_PROMPT = PromptTemplate(
            input_variables=["question"],
            template="""You are an AI language model assistant. Your task is to generate 2
            different versions of the given user question to retrieve relevant documents from
            a vector database. By generating multiple perspectives on the user question, your
            goal is to help the user overcome some of the limitations of the distance-based
            similarity search. Provide these alternative questions separated by newlines.
            Original question: {question}"""
        )

        reasoning_steps.append("🔍 Generating alternative search queries...")

        # Retrieve from all collections
        all_docs = []
        embeddings = OllamaEmbeddings(model="nomic-embed-text")
        for pdf in pdfs:
            print(pdf)
            vector_db = Chroma(
                persist_directory=self.persist_directory,
                embedding_function=embeddings,
                collection_name=pdf.collection_name
            )

            retriever = vector_db.as_retriever(
                search_kwargs={"k": 40}
            )
            # docs = retriever.invoke(question)


            try:
                reasoning_steps.append(f"📄 Retrieving from: {pdf.name}")
                # Use invoke instead of deprecated get_relevant_documents
                docs = retriever.invoke(question)
                # Ensure metadata is present
                for doc in docs:
                    if "pdf_name" not in doc.metadata:
                        doc.metadata["pdf_name"] = pdf.name
                    if "pdf_id" not in doc.metadata:
                        doc.metadata["pdf_id"] = pdf.pdf_id
                all_docs.extend(docs)
                reasoning_steps.append(f"✅ Found {len(docs)} relevant chunks in {pdf.name}")
            except Exception as e:
                reasoning_steps.append(f"⚠️ Error retrieving from {pdf.name}: {str(e)}")
                print(f"Error retrieving from {pdf.name}: {e}")

        reasoning_steps.append(f"📊 Total chunks retrieved: {len(all_docs)}")

        # Format context with source labels
        context_parts = []
        for doc in all_docs[:10]:
            source = doc.metadata.get("pdf_name", "Unknown")
            context_parts.append(f"[Source: {source}]\n{doc.page_content}\n")

        formatted_context = "\n---\n".join(context_parts)
        reasoning_steps.append(f"🔗 Using top {min(len(all_docs), 10)} chunks for context")

        # RAG prompt template with chain-of-thought
        template = """Answer the question based ONLY on the following context from multiple PDF documents.
        Each section is marked with its source document.

        Use chain-of-thought reasoning:
        1. First, identify which parts of the context are relevant to the question
        2. Analyze the information from each source document
        3. Synthesize the information to form a comprehensive answer
        4. Ensure you cite the source document name for each piece of information
        5. If information comes from multiple sources, mention all relevant sources
        6. If sources contradict, note the discrepancy and cite both sources

        Context:
        {context}

        Question: {question}

        Think step-by-step and provide your answer with source citations:"""

        prompt = ChatPromptTemplate.from_template(template)
        chain = (
            {"context": lambda x: formatted_context, "question": lambda x: x}
            | prompt
            | llm
            | StrOutputParser()
        )

        reasoning_steps.append("💭 Generating answer with source citations...")

        # Check if model supports thinking (e.g., qwen3, deepseek-r1)
        thinking_models = ['qwen3', 'deepseek-r1', 'qwen', 'deepseek']
        supports_thinking = any(tm in model.lower() for tm in thinking_models)

        if supports_thinking:
            reasoning_steps.append("🧠 Using thinking-enabled model with chain-of-thought reasoning...")
            try:
                # Enhanced system message for chain-of-thought reasoning
                cot_system_message = f"""You are an expert AI assistant that uses chain-of-thought reasoning.

                Answer the question based ONLY on the provided context from PDF documents.

                CHAIN-OF-THOUGHT PROCESS:
                1. **Read and understand** the question carefully
                2. **Scan the context** to identify all relevant information
                3. **Break down** the information by source document
                4. **Analyze** how each piece relates to the question
                5. **Synthesize** a comprehensive answer
                6. **Cite sources** explicitly for every claim

                Context from PDF documents:
                {formatted_context}

                Think through each step carefully, showing your reasoning process."""

                # Use Ollama client directly for thinking-capable models
                ollama_response = chat_completion(
                    system_prompt=cot_system_message,
                    user_input=f"Question: {question}\n\nThink step-by-step and provide a detailed answer with source citations.",
                )

                response = ollama_response
            except Exception as e:
                print(f"Error using thinking mode, falling back to standard: {e}")
                response = chain.invoke(question)
        else:
            response = chain.invoke(question)

        # Extract source information
        sources = [
            {
                "pdf_name": doc.metadata.get("pdf_name"),
                "pdf_id": doc.metadata.get("pdf_id"),
                "chunk_index": doc.metadata.get("chunk_index", 0)
            }
            for doc in all_docs[:10]
        ]

        reasoning_steps.append("✨ Answer generated successfully!")

        return response, sources, reasoning_steps

    def save_message(
        self,
        session_id: str,
        role: str,
        content: str,
        sources: Optional[List[Dict]],
        db: Session
    ) -> ChatMessage:
        """Save chat message to database.

        Args:
            session_id: Chat session identifier
            role: Message role (user or assistant)
            content: Message content
            sources: Source documents (for assistant messages)
            db: Database session

        Returns:
            Saved chat message
        """
        # Ensure session exists
        session = db.query(ChatSession).filter(ChatSession.session_id == session_id).first()
        if not session:
            session = ChatSession(
                session_id=session_id,
                created_at=datetime.now(),
                last_active=datetime.now()
            )
            db.add(session)
        else:
            session.last_active = datetime.now()

        # Save message
        message = ChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            sources=sources,
            timestamp=datetime.now()
        )
        db.add(message)
        db.commit()
        db.refresh(message)

        return message

    def get_session_messages(self, session_id: str, db: Session) -> List[ChatMessage]:
        """Get all messages for a session.

        Args:
            session_id: Chat session identifier
            db: Database session

        Returns:
            List of chat messages
        """
        return db.query(ChatMessage).filter(
            ChatMessage.session_id == session_id
        ).order_by(ChatMessage.timestamp).all()


    def run_direct_llm_answer(self, user_input: str) -> Dict[str, str]:
        """
        Handles non-document questions directly using LLM (no RAG).
        Optimized for speed and safety.
        """

        if not user_input or not user_input.strip():
            return {
                "status": "ERROR",
                "answer": "Please provide a valid question."
            }

        system_prompt = (
            "You are a concise, helpful assistant.\n"
            "Answer the user's question directly.\n"
            "If the question is unclear, ask for clarification.\n"
            "Do NOT mention documents or sources."
        )

        try:
            answer = chat_completion(
                system_prompt=system_prompt,
                user_input=user_input.strip(),
            )

            return {
                "status": "OK",
                "answer": answer
            }

        except Exception as e:
            return {
                "status": "ERROR",
                "answer": f"Failed to generate response: {str(e)}"
            }
