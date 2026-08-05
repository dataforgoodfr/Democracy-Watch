from etl.embedding.base import EmbeddingBackend

_BACKENDS: dict[str, type[EmbeddingBackend]] = {}


def register(name: str):
    """Class decorator that registers an :class:`EmbeddingBackend` under `name`."""

    def decorator(cls: type[EmbeddingBackend]) -> type[EmbeddingBackend]:
        cls.name = name
        _BACKENDS[name] = cls
        return cls

    return decorator


def available_backends() -> list[str]:
    _load_builtin_backends()
    return sorted(_BACKENDS)


def create_backend(name: str, **kwargs) -> EmbeddingBackend:
    """Instantiate the backend registered under `name`.

    Extra keyword arguments (e.g. ``model=...``, ``batch_size=...``) are passed
    straight to the backend's constructor.
    """
    _load_builtin_backends()
    try:
        cls = _BACKENDS[name]
    except KeyError:
        raise ValueError(
            f"Unknown embedding backend {name!r}. "
            f"Available: {', '.join(available_backends())}"
        )
    return cls(**kwargs)


def _load_builtin_backends() -> None:
    """Import the built-in backend modules so their ``@register`` calls run.

    Done lazily (rather than at package import) so that merely importing the
    registry never drags in heavy optional dependencies such as torch.
    """
    import etl.embedding.backends  # noqa: F401
