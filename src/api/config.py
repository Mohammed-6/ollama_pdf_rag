"""Configuration settings for FastAPI application."""
from typing import Dict
from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    """Application settings."""

    # Paths
    PROJECT_ROOT: Path = Path(__file__).parent.parent.parent
    PDF_STORAGE_DIR: str = "data/pdfs/uploads"
    VECTOR_DB_DIR: str = "data/vectors"

    # Database
    DATABASE_URL: str = "sqlite:///./data/api.db"

    # Ollama
    OLLAMA_HOST: str = "http://localhost:11434"
    EMBEDDING_MODEL: str = "nomic-embed-text"
    DEFAULT_CHAT_MODEL: str = "llama3.2"

    # config.py

    LLM_PROVIDER: str = "openai"   # "ollama" | "openai"

    # ---- Ollama ----
    OLLAMA_MODEL: str = "qwen2.5:3b"
    OLLAMA_OPTIONS: Dict[str, any] = {
        "temperature": 0,
        "top_p": 1,
        "num_predict": 20,
        "repeat_penalty": 1.1,
        "stop": ["\n", " ", "."],
    }

    # ---- OpenAI ----
    OPENAI_MODEL: str = "gpt-4.1-mini"
    OPENAI_API_VERSION: str = "2024-05-01-preview"
    OPENAI_API_ENDPOINT: str = ""
    OPENAI_API_KEY: str = ""

    AZURE_EMBEDDING_DEPLOYMENT: str = "text-embedding-3-small"
    AZURE_EMBEDDING_ENDPOINT: str = ""
    AZURE_EMBEDDING_API_KEY: str = ""
    AZURE_EMBEDDING_API_VERSION: str = "2024-02-01"

    AZURE_TENANT_ID: str = ""
    AZURE_CLIENT_ID: str = ""
    AZURE_CLIENT_SECRET: str = ""

    # ---- Azure Storage ----
    AZURE_STORAGE_CONNECTION_STRING: str = ""
    AZURE_STORAGE_CONTAINER: str = ""
    AZURE_STORAGE_SHARE_NAME: str = ""

    # ---- Dashboard ----
    BASE_DASHBOARD_API: str = ""

    # ---- Email ----
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    REPORT_EMAIL_FROM: str = ""
    REPORT_EMAIL_TO: str = ""


    class Config:
        """Pydantic config."""
        env_file = ".env"
        extra = "allow"


settings = Settings()
