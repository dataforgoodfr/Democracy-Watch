"""Configuration de la base vectorielle (DuckDB), lue depuis l'environnement."""

from os import getenv
from pathlib import Path

DEFAULT_DUCKDB_PATH = "./data/vectors.duckdb"
DUCKDB_EXTENSIONS = ("vss",)  # Index pour la recherche approximative de vecteurs


def get_duckdb_path() -> Path:
    """Chemin de la base vectorielle"""
    return Path(getenv("DUCKDB_PATH") or DEFAULT_DUCKDB_PATH)


def is_duckdb_read_only() -> bool:
    """Indique si la base vectorielle est en lecture seule (`DUCKDB_READ_ONLY`)."""
    return getenv("DUCKDB_READ_ONLY", "").strip().lower() == "true"


def get_duckdb_threads() -> int | None:
    """Nombre de threads DuckDB (`DUCKDB_THREADS`), ou None pour son défaut."""
    raw = (getenv("DUCKDB_THREADS") or "").strip()
    return int(raw) if raw else None
