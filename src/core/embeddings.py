"""Vector embeddings and database functionality."""
import logging
import os
from typing import List
from pathlib import Path
from langchain_ollama import OllamaEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_openai import AzureOpenAIEmbeddings, OpenAIEmbeddings
from openai import AzureOpenAI

from src.api.config import settings

logger = logging.getLogger(__name__)

class VectorStore:
    """Manages vector embeddings and database operations."""

    def __init__(self, embedding_model: str = "text-embedding-3-small", persist_directory: str = "data/vectors"):
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
        self.embeddings = client
        self.persist_directory = persist_directory
        self.vector_db = None
        # Ensure persist directory exists
        Path(persist_directory).mkdir(parents=True, exist_ok=True)

    def create_vector_db(self, documents: List, collection_name: str = "local-rag") -> Chroma:
        """Create vector database from documents with persistence."""
        try:
            logger.info(f"Creating vector database with collection: {collection_name}")
            logger.info(f"Persisting to: {self.persist_directory}")
            logger.info(f"Number of documents: {len(documents)}")

            # vector_db = Chroma.from_documents(
            #     documents=documents,
            #     embedding=self.embeddings,
            #     collection_name=collection_name,
            #     persist_directory=self.persist_directory
            # )
            vector_db = Chroma(
                collection_name=collection_name,
                embedding_function=self.embeddings,
                persist_directory=self.persist_directory,
            )

            # ✅ Add documents in batches to avoid ChromaDB batch size limit
            batch_size = 5000
            total_batches = (len(documents) // batch_size) + 1
            
            for i in range(0, len(documents), batch_size):
                batch = documents[i:i+batch_size]
                vector_db.add_documents(batch)
                logger.info(f"✅ Batch {i//batch_size + 1}/{total_batches} added ({len(batch)} documents)")


            logger.info(f"✅ Vector database created successfully with {len(documents)} documents")
            return self.vector_db
        except Exception as e:
            logger.error(f"❌ Error creating vector database: {e}")
            raise
    
    def delete_collection(self) -> None:
        """Delete vector database collection."""
        if self.vector_db:
            try:
                logger.info("Deleting vector database collection")
                self.vector_db.delete_collection()
                self.vector_db = None
            except Exception as e:
                logger.error(f"Error deleting collection: {e}")
                raise 