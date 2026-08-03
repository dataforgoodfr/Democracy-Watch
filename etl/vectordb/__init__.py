"""Base vectorielle des embeddings.

Pendant de `etl/database.py` + `models/` pour les vecteurs : la configuration
vient de l'environnement (`etl.vectordb.config`), le schéma est déclaré une
seule fois (`etl.vectordb.schema`), et les appelants passent par un store
plutôt que par du SQL DuckDB::

    from etl.vectordb import EmbeddingStore

    with EmbeddingStore() as store:
        store.ensure_table(backend.dimension)
        store.upsert([(uid, vector), ...])
        uids, matrix = store.load_matrix()

Postgres reste la source de vérité : ces tables ne stockent qu'une donnée
dérivée (`uid` -> vecteur), reconstructible.
"""

from etl.vectordb.config import (
    DEFAULT_DUCKDB_PATH,
    get_duckdb_path,
    is_duckdb_read_only,
)
from etl.vectordb.database import (
    VectorDimensionMismatch,
    create_db,
    get_connection,
    get_tables_definition,
    table_dimension,
)
from etl.vectordb.schema import AMENDEMENT_EMBEDDINGS, VECTOR_TABLES, VectorTable
from etl.vectordb.store import EmbeddingStore

__all__ = [
    "AMENDEMENT_EMBEDDINGS",
    "DEFAULT_DUCKDB_PATH",
    "EmbeddingStore",
    "VECTOR_TABLES",
    "VectorDimensionMismatch",
    "VectorTable",
    "create_db",
    "get_connection",
    "get_duckdb_path",
    "is_duckdb_read_only",
    "get_tables_definition",
    "table_dimension",
]
