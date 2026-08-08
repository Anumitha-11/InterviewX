import os
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "InterviewX Backend"
    API_V1_STR: str = "/api"

    # Environment configs loaded from .env
    DATABASE_URL: str = "sqlite:///./interviewx.db"

    # LLM configuration
    LLM_MODE: str = "mock"
    OPENAI_API_KEY: str = "mock-key"

    # Authentication
    JWT_SECRET: str = "4f63c87e83dfca103db81289de61d9a24bbfe384918e9102c91823ab9128abf1"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 180

    # RAG / ChromaDB
    CHROMA_PATH: str = "./chroma_db"

    # Frontend
    FRONTEND_URL: str = "http://localhost:8000"

    # File storage
    UPLOAD_DIR: str = "./uploads"
    KNOWLEDGE_BASE_DIR: str = "./knowledge_base"

    class Config:
        env_file = os.path.join(
            os.path.dirname(
                os.path.dirname(
                    os.path.dirname(__file__)
                )
            ),
            ".env"
        )
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()

# Ensure required directories exist
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.KNOWLEDGE_BASE_DIR, exist_ok=True)