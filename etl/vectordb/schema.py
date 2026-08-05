"""Schéma déclaratif des tables vectorielles."""

from dataclasses import dataclass


@dataclass(frozen=True)
class VectorTable:
    """Une table `(clé, vecteur)` de la base DuckDB."""

    #: Nom de la table.
    name: str
    #: Colonne clé primaire, référence vers la table Postgres d'origine.
    key_column: str
    #: Colonne FLOAT[N] portant le vecteur.
    vector_column: str
    #: Table Postgres dont cette table dérive (documentaire).
    source_table: str

    def create_sql(self, dimension: int) -> str:
        """DDL de création de la table pour des vecteurs de `dimension` réels."""
        return (
            f"CREATE TABLE IF NOT EXISTS {self.name} ("
            f"{self.key_column} VARCHAR PRIMARY KEY, "
            f"{self.vector_column} FLOAT[{dimension}]"
            f")"
        )

    def drop_sql(self) -> str:
        """DDL de suppression de la table."""
        return f"DROP TABLE IF EXISTS {self.name}"


AMENDEMENT_EMBEDDINGS = VectorTable(
    name="amendement_embeddings",
    key_column="uid",
    vector_column="embedding",
    source_table="amendements",
)

VECTOR_TABLES: dict[str, VectorTable] = {
    table.name: table for table in (AMENDEMENT_EMBEDDINGS,)
}
