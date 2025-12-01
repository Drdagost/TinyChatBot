import os
from typing import List


class VectorStore:
    """A minimal vector store abstraction. Currently provides an in-memory fallback.

    Concrete providers (FAISS, Pinecone, Chroma) are planned and can be selected via
    `VECTOR_PROVIDER` env var.
    """

    def __init__(self):
        provider = os.getenv("VECTOR_PROVIDER", "memory").lower()
        self.provider = provider
        if provider == "memory":
            self._vectors = []
        else:
            raise NotImplementedError(
                f"Vector provider '{provider}' not implemented in this minimal refactor"
            )

    def upsert(self, id: str, embedding: List[float], metadata: dict | None = None):
        # Replace existing vector with same id if present (upsert semantics)
        for i, v in enumerate(self._vectors):
            if v.get("id") == id:
                self._vectors[i] = {
                    "id": id,
                    "embedding": embedding,
                    "metadata": metadata or {},
                }
                return
        self._vectors.append(
            {"id": id, "embedding": embedding, "metadata": metadata or {}}
        )

    def clear(self):
        """Clear all vectors (useful to isolate per-request indexes)."""
        self._vectors = []

    def query(self, embedding: List[float], top_k: int = 5):
        # naive cosine distance ranking
        from math import sqrt

        def dot(a, b):
            return sum(x * y for x, y in zip(a, b))

        def norm(a):
            return sqrt(sum(x * x for x in a))

        scored = []
        for v in self._vectors:
            score = dot(embedding, v["embedding"]) / (
                norm(embedding) * norm(v["embedding"]) + 1e-12
            )
            scored.append((score, v))

        scored.sort(key=lambda t: t[0], reverse=True)
        return [v for _, v in scored[:top_k]]
