"""Pluggable text-embedding backends.

Pick a backend by name and encode text without caring how it runs::

    from etl.embedding import create_backend

    backend = create_backend("sentence-transformers")   # local GPU, F2LLM
    vectors = backend.embed_documents(["some text", ...])
    query = backend.embed_query("what am I looking for?")

New backends are added by dropping a module in ``backends/`` that subclasses
:class:`EmbeddingBackend` and decorates it with ``@register("name")``.
"""

from etl.embedding.base import EmbeddingBackend
from etl.embedding.config import DEFAULT_BACKEND, DEFAULT_MODEL
from etl.embedding.registry import available_backends, create_backend, register

__all__ = [
    "EmbeddingBackend",
    "DEFAULT_BACKEND",
    "DEFAULT_MODEL",
    "available_backends",
    "create_backend",
    "register",
]
