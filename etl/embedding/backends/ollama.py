import httpx

from etl.embedding.base import EmbeddingBackend
from etl.embedding.registry import register


@register("ollama")
class OllamaBackend(EmbeddingBackend):
    """Embed via a running Ollama server over HTTP.

    Convenient (no local model management) but throughput is bounded by the
    HTTP round-trip and Ollama's own batching, so the GPU is often under-fed.
    For heavy indexing prefer the local ``sentence-transformers`` backend.
    """

    def __init__(
        self,
        model: str = "embeddinggemma",
        dimension: int = 768,
        url: str = "http://localhost:11434/api/embed",
        query_prompt: str = "",
        timeout: float = 120,
    ):
        self.model = model
        self._dimension = dimension
        self.url = url
        # Prepended to queries only (symmetric models like bge-m3 leave "").
        self.query_prompt = query_prompt
        self.timeout = timeout

    @property
    def dimension(self) -> int:
        return self._dimension

    def _embed(self, texts: list[str]) -> list[list[float]]:
        response = httpx.post(
            self.url,
            json={"model": self.model, "input": texts},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()["embeddings"]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._embed(texts)

    def embed_query(self, text: str) -> list[float]:
        return self._embed([self.query_prompt + text])[0]
