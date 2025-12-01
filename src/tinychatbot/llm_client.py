import os
from typing import List


class LLMClient:
    """Adapter for multiple LLM providers. For now, only wraps OpenAI via 'openai' package.

    Future: add Anthropic, Google, HF adapters under the same interface.
    """

    def __init__(self):
        provider = os.getenv("LLM_PROVIDER", "openai").lower()
        self.provider = provider
        if provider == "openai":
            # Lazy import to avoid hard dependency during package import
            from openai import OpenAI

            self.client = OpenAI()
        else:
            raise NotImplementedError(f"LLM provider '{provider}' not implemented yet")

    def chat(self, messages: List[dict], **kwargs) -> dict:
        if self.provider == "openai":
            return self.client.chat.completions.create(messages=messages, **kwargs)
        raise NotImplementedError()

    def embed(self, texts: List[str], **kwargs) -> List[List[float]]:
        if self.provider == "openai":
            from .config import Config
            resp = self.client.embeddings.create(input=texts, model=kwargs.get("model", Config.EMBEDDING_MODEL))
            return [d.embedding for d in resp.data]
        raise NotImplementedError()

