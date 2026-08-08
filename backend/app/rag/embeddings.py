from chromadb import EmbeddingFunction
from chromadb.utils import embedding_functions
from app.core.config import settings

class MockEmbeddingFunction(EmbeddingFunction):
    @staticmethod
    def name() -> str:
        return "MockEmbeddingFunction"

    def __call__(self, input):
        # Return a list of dummy 384-dimensional vectors
        return [[0.0] * 384 for _ in input]

def get_embedding_function():
    if settings.LLM_MODE == "real" and settings.OPENAI_API_KEY != "mock-key":
        return embedding_functions.OpenAIEmbeddingFunction(
            api_key=settings.OPENAI_API_KEY,
            model_name="text-embedding-3-small"
        )
    else:
        # Avoid downloading a 79MB model in mock mode
        return MockEmbeddingFunction()
