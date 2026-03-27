"""
FAST RAG PIPELINE (<2s at scale)

Key features:
- Single global vector index (Chroma)
- Single query embedding (no MultiQueryRetriever)
- Metadata filtering
- Small context window (top 6–8 chunks)
- No chain-of-thought leakage
- Fast Ollama models

Requirements:
pip install langchain langchain-community chromadb ollama
"""

from typing import List, Optional
from langchain_ollama import ChatOllama,OllamaEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate


class FastRAGService:
    def __init__(
        self,
        persist_directory: str,
        embedding_model: str = "nomic-embed-text",
        llm_model: str = "phi3",
    ):
        # Create embeddings ONCE
        self.embeddings = OllamaEmbeddings(model=embedding_model)

        # Single global vector store
        self.vector_db = Chroma(
            persist_directory=persist_directory,
            embedding_function=self.embeddings,
        )

        # Fast answering model
        self.llm = ChatOllama(
            model=llm_model,
            temperature=0,
        )

        self.prompt = ChatPromptTemplate.from_template(
        """You are a document-grounded assistant.

        CRITICAL RULES (MANDATORY):
        - Use ONLY the information explicitly present in the Context
        - Do NOT use prior knowledge
        - Do NOT make assumptions
        - Every factual statement MUST be followed by a source citation
        - Source format: [Source: <pdf_name>]
        - If the Context does NOT contain the answer, respond EXACTLY with:
        "I don't know based on the provided documents."

        Context:
        {context}

        Question:
        {question}

        Answer (with citations only):"""
        )


    def query(
        self,
        question: str,
        pdf_ids: Optional[List[str]] = None,
        k: int = 40,
        max_chunks: int = 8,
    ) -> str:
        # Metadata filtering (optional)
        search_kwargs = {"k": k}

        if pdf_ids and len(pdf_ids) > 0:
            search_kwargs["filter"] = {"pdf_id": {"$in": pdf_ids}}

        print(pdf_ids)  # Debug: Check search parameters

        # Single ANN search
        docs = self.vector_db.similarity_search(
            question,
            **search_kwargs,
        )

        # Hard cap context
        docs = docs[:max_chunks]

        # print(docs)
        print(f"Filtering with pdf_ids: {pdf_ids}")
        docs = self.vector_db.similarity_search(question, **search_kwargs)
        print(f"Found {len(docs)} documents")

        # Format context
        context = "\n---\n".join(
            f"[Source: {d.metadata.get('name','Unknown')}]\n{d.page_content}"
            for d in docs
        )

        # Generate answer
        chain = self.prompt | self.llm
        response = chain.invoke({"context": context, "question": question})

        # return response.content
        response = response.content.strip()
        print(response)

        # Reject meta answers
        forbidden_phrases = [
            "cannot access",
            "external attachments",
            "outside of our conversation",
            "provided by user"
        ]

        if any(p in response.lower() for p in forbidden_phrases):
            return "I don't know based on the provided documents."

        # Enforce citations
        if "[Source:" not in response:
            return "I don't know based on the provided documents."

        # Reject placeholder citations
        if "<pdf_name>" in response:
            return "I don't know based on the provided documents."


# Example usage
if __name__ == "__main__":
    rag = FastRAGService(persist_directory="./chroma_db")

    answer = rag.query(
        question="What is the return policy?",
        pdf_ids=["pdf_123", "pdf_456"],
    )
    
    print(answer)
