"""Connexion et cycle de vie de la base vectorielle DuckDB."""

import re

import duckdb

from etl.vectordb.config import (
    DUCKDB_EXTENSIONS,
    get_duckdb_path,
    is_duckdb_read_only,
    get_duckdb_threads,
)
from etl.vectordb.schema import VECTOR_TABLES, VectorTable


class VectorDimensionMismatch(ValueError):
    """Une table existe déjà avec une longueur de vecteur différente.

    Une table ne peut porter qu'une seule dimension, donc un seul modèle
    d'embedding : mélanger deux modèles produirait des distances qui n'ont
    aucun sens. Le rebuild (`create_db`) est la porte de sortie.
    """


def get_connection(read_only: bool | None = None) -> duckdb.DuckDBPyConnection:
    """Retourne une connexion DuckDB configurée.

    Crée le répertoire parent au besoin (DuckDB échoue sinon), applique les
    réglages d'environnement et charge les extensions déclarées.
    """
    path = get_duckdb_path()
    read_only = is_duckdb_read_only() if read_only is None else read_only
    if not read_only:
        path.parent.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect(str(path), read_only=read_only)

    threads = get_duckdb_threads()
    if threads:
        con.execute(f"SET threads = {threads}")

    for extension in DUCKDB_EXTENSIONS:
        if not read_only:
            con.execute(f"INSTALL {extension}")
        con.execute(f"LOAD {extension}")

    return con


def table_exists(con: duckdb.DuckDBPyConnection, table: VectorTable) -> bool:
    """Indique si la table vectorielle existe déjà dans la base."""
    return (
        con.execute(
            "SELECT 1 FROM information_schema.tables WHERE table_name = ?",
            [table.name],
        ).fetchone()
        is not None
    )


def table_dimension(con: duckdb.DuckDBPyConnection, table: VectorTable) -> int | None:
    """Longueur des vecteurs stockés, ou None si la table n'existe pas encore."""
    if not table_exists(con, table):
        return None
    row = con.execute(
        f"SELECT column_type FROM (DESCRIBE {table.name}) WHERE column_name = ?",
        [table.vector_column],
    ).fetchone()
    if row is None:
        return None
    match = re.search(r"\[(\d+)\]", row[0])  # ex. 'FLOAT[768]'
    return int(match.group(1)) if match else None


def create_table(
    con: duckdb.DuckDBPyConnection, table: VectorTable, dimension: int
) -> None:
    """Crée la table si absente, après avoir vérifié la dimension existante."""
    assert_dimension(con, table, dimension)
    con.execute(table.create_sql(dimension))


def assert_dimension(
    con: duckdb.DuckDBPyConnection, table: VectorTable, dimension: int
) -> None:
    """Vérifie que la `dimension` est compatible avec la table déjà en place.

    Lève :class:`VectorDimensionMismatch` sinon, à charge de l'appelant de le
    présenter comme il l'entend.
    """
    existing = table_dimension(con, table)
    if existing is not None and existing != dimension:
        raise VectorDimensionMismatch(
            f"La table '{table.name}' de '{get_duckdb_path()}' contient des vecteurs "
            f"de dimension {existing}, mais ce backend en produit de dimension "
            f"{dimension}. Un seul modèle par table : relancer un rebuild "
            f"(`uv run main.py --rebuild-vector-database`) pour ré-embedder."
        )


def get_tables_definition() -> list[VectorTable]:
    """Descripteurs des tables gérées par la base vectorielle."""
    return list(VECTOR_TABLES.values())


def create_db() -> dict[str, VectorTable]:
    """Détruit les tables vectorielles pour repartir d'une base vide."""
    print("Creating vector DB")
    tables = get_tables_definition()
    print([table.name for table in tables])
    with get_connection(read_only=False) as con:
        for table in tables:
            con.execute(table.drop_sql())
    print(f"Vector db was created ({get_duckdb_path()})")
    return VECTOR_TABLES
