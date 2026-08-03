from etl.embedding.base import EmbeddingBackend
from etl.embedding.config import DEFAULT_MODEL
from etl.embedding.registry import register


@register("sentence-transformers")
class SentenceTransformersBackend(EmbeddingBackend):
    """Local, in-process embedding via the sentence-transformers library.

    Because the model runs in this process, large batches
    keep the GPU saturated instead of idling between requests. Raise
    ``batch_size`` until you hit a VRAM limit for best throughput.

    Uses the model's own ``encode_query`` / ``encode_document`` helpers to
    ensure asymmetric models are prompted correctly without the caller having
    to know the details.
    """

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        device: str | None = None,
        batch_size: int = 32,
        dtype: str = "bfloat16",
        normalize: bool = True,
        max_seq_length: int = 1024,
    ):
        import torch
        from sentence_transformers import SentenceTransformer

        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"

        self._model = SentenceTransformer(
            model, device=device, model_kwargs={"torch_dtype": dtype}
        )
        # Model limit: 40960 tokens. Rare outliers (100k+ chars) truncated to
        # max_seq_length (p99 of ~4.8k chars for summary fields, no loss in practice).
        self._model.max_seq_length = max_seq_length
        self.batch_size = batch_size
        self.normalize = normalize
        self._dimension = self._model.get_sentence_embedding_dimension()

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        embeddings = self._model.encode_document(
            texts,
            batch_size=self.batch_size,
            normalize_embeddings=self.normalize,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return embeddings.tolist()

    def embed_query(self, text: str) -> list[float]:
        embedding = self._model.encode_query(
            text,
            normalize_embeddings=self.normalize,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return embedding.tolist()
