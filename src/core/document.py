"""Document processing functionality."""
import logging
from pathlib import Path
from typing import List
from langchain_community.document_loaders import PyPDFLoader, TextLoader, word_document
from langchain_text_splitters import RecursiveCharacterTextSplitter
# LangChain standard Word loaders
from langchain_community.document_loaders import UnstructuredWordDocumentLoader 

logger = logging.getLogger(__name__)

class DocumentProcessor:
    """Handles PDF document loading and processing."""
    
    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 100):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
    
    def load_pdf(self, file_path: Path) -> List:
        """Load PDF document."""
        try:
            logger.info(f"Loading PDF from {file_path}")
            loader = PyPDFLoader(str(file_path))
            return loader.load()
        except Exception as e:
            logger.error(f"Error loading PDF: {e}")
            raise
    def load_txt(self, file_path: Path) -> List:
        """Load TXT document."""
        try:
            logger.info(f"Loading TXT from {file_path}")
            
            loader = TextLoader(
                str(file_path),
                encoding="utf-8"  # important for Windows safety
            )
            
            return loader.load()

        except Exception as e:
            logger.error(f"Error loading TXT: {e}")
            raise
    def load_word(self, file_path: Path) -> List:
        """Load WORD document."""
        try:
            logger.info(f"Loading WORD from {file_path}")

            loader = UnstructuredWordDocumentLoader(
                str(file_path),
                mode="elements"  # ✅ preserves structure like tables, headings
            )
            documents = loader.load()
            # ✅ Clean metadata for every document
            for doc in documents:
                doc.metadata = self.clean_metadata(doc.metadata)
            return documents
        except Exception as e:
            logger.error(f"Error loading WORD: {e}")
            raise

    def split_documents(self, documents: List) -> List:
        """Split documents into chunks."""
        try:
            logger.info("Splitting documents into chunks")
            return self.splitter.split_documents(documents)
        except Exception as e:
            logger.error(f"Error splitting documents: {e}")
            raise 

    def clean_metadata(self, metadata: dict) -> dict:
        """Remove or flatten metadata values that ChromaDB cannot handle."""
        cleaned = {}
        for key, value in metadata.items():
            
            # ✅ Keep simple types as-is
            if isinstance(value, (str, int, float, bool)):
                cleaned[key] = value
            
            # ✅ Convert list of dicts (like links) to a JSON string
            elif isinstance(value, list):
                cleaned[key] = str(value)  # or use json.dumps(value)
            
            # ✅ Convert dict to string
            elif isinstance(value, dict):
                cleaned[key] = str(value)
            
            # ✅ Skip None values
            elif value is None:
                cleaned[key] = ""
            
            else:
                cleaned[key] = str(value)  # fallback
        
        return cleaned