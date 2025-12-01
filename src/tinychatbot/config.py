import os

from dotenv import load_dotenv

load_dotenv(override=True)


class Config:
    """Simple configuration holder that reads from environment variables.

    This centralizes provider selection for LLM and vector stores.
    """

    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai").lower()
    VECTOR_PROVIDER = os.getenv(
        "VECTOR_PROVIDER", os.getenv("VECTOR_DB", "faiss")
    ).lower()

    # Provider-specific keys
    OPENAI_API_BASE = os.getenv(
        "OPENAI_API_BASE",
        "http://localhost:11434/v1" if LLM_PROVIDER == "ollama" else None,
    )
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
    PINECONE_ENV = os.getenv("PINECONE_ENV")
    CHROMA_DIR = os.getenv("CHROMA_DIR", "./chroma_db")

    CONTENT_DIR = os.getenv("CONTENT_DIR", "content")
    # Model name used for tokenizer selection (tiktoken). Keep as an env var so it's easy to change.
    LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
    # Embedding model used by the LLM client (can be overridden via env)
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    # Chunking controls (token counts, defaults align with .env.example)
    CHUNK_SIZE_TOKENS = int(os.getenv("CHUNK_SIZE", "1000"))
    CHUNK_OVERLAP_TOKENS = int(os.getenv("CHUNK_OVERLAP", "200"))

    PERSONAS_DIR = os.getenv("PERSONAS_DIR", "src/tinychatbot/personas")
    DEFAULT_PERSONA_ID = os.getenv("DEFAULT_PERSONA_ID", "default")
