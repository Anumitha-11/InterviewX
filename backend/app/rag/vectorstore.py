import os
import chromadb
from app.core.config import settings

class VectorStoreManager:
    _client = None

    @classmethod
    def get_client(cls):
        if cls._client is None:
            os.makedirs(settings.CHROMA_PATH, exist_ok=True)
            cls._client = chromadb.PersistentClient(path=settings.CHROMA_PATH)
        return cls._client

    @classmethod
    def get_collection(cls, name="interview_prep"):
        client = cls.get_client()
        # Get or create collection
        return client.get_or_create_collection(name=name)
