from abc import ABC, abstractmethod


class EmbeddingBackend(ABC):
    """A strategy for turning text into dense vectors.

    Embedding models are frequently asymmetric: a search query and an indexed
    document are encoded differently. For instance, some prepend a retrieval
    instruction to queries only. Callers therefore go through the two dedicated
    methods below rather than a single generic `embed`, so each backend can
    apply the right side of that asymmetry.

    Concrete backends register themselves under a name with
    ``@register("...")`` (see :mod:`etl.embedding.registry`) and are created via
    :func:`etl.embedding.create_backend`.
    """

    #: Registry key, assigned by the ``@register`` decorator.
    name: str = ""

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Length of the vectors this backend produces."""

    @abstractmethod
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of documents (corpus side).

        Implementations are expected to batch internally for throughput; pass
        as many texts at once as memory allows.
        """

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        """Embed a single search query (query side)."""
