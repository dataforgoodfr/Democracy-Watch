"""Accès applicatif aux tables vectorielles.

`EmbeddingStore` est la seule porte d'entrée sur les vecteurs : ni l'ETL ni le
dashboard n'écrivent de SQL DuckDB. Ils manipulent des clés et des vecteurs, le
store s'occupe du schéma, de la dimension et du format de lecture.
"""

import numpy as np

from etl.vectordb.database import (
    assert_dimension,
    create_table,
    get_connection,
    table_dimension,
)
from etl.vectordb.schema import AMENDEMENT_EMBEDDINGS, VectorTable


class EmbeddingStore:
    """Lecture/écriture d'une table `(clé, vecteur)`.

    S'utilise comme un context manager (`with EmbeddingStore() as store:`), qui
    ferme la connexion en sortie. Une instance n'est pas partageable entre
    threads : voir :meth:`cursor`.
    """

    def __init__(
        self,
        table: VectorTable = AMENDEMENT_EMBEDDINGS,
        con=None,
        read_only: bool | None = None,
    ):
        self.table = table
        self.con = get_connection(read_only=read_only) if con is None else con

    def __enter__(self) -> "EmbeddingStore":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def close(self) -> None:
        """Ferme la connexion DuckDB."""
        self.con.close()

    def cursor(self) -> "EmbeddingStore":
        """Store indépendant sur la même base, sûr dans un autre thread.

        Une connexion DuckDB ne supporte pas les accès concurrents ; un curseur
        est une poignée distincte sur la même base, ce qui permet à une tâche de
        fond de lire pendant que le thread principal interroge la connexion
        partagée.
        """
        return EmbeddingStore(self.table, con=self.con.cursor())

    # --- Schéma ---

    @property
    def dimension(self) -> int | None:
        """Longueur des vecteurs stockés, ou None si la table n'existe pas."""
        return table_dimension(self.con, self.table)

    def exists(self) -> bool:
        """Indique si la table vectorielle existe déjà dans la base."""
        return self.dimension is not None

    def assert_dimension(self, dimension: int) -> None:
        """Lève :class:`VectorDimensionMismatch` si la table est incompatible."""
        assert_dimension(self.con, self.table, dimension)

    def ensure_table(self, dimension: int) -> None:
        """Crée la table à `dimension` si elle n'existe pas déjà."""
        create_table(self.con, self.table, dimension)

    # --- Lecture ---

    def keys(self) -> set[str]:
        """Clés déjà présentes (vide si la table n'existe pas encore)."""
        if not self.exists():
            return set()
        rows = self.con.execute(
            f"SELECT {self.table.key_column} FROM {self.table.name}"
        ).fetchall()
        return {row[0] for row in rows}

    def count(self) -> int:
        """Nombre de lignes déjà présentes (0 si la table n'existe pas encore)."""
        if not self.exists():
            return 0
        return self.con.execute(f"SELECT count(*) FROM {self.table.name}").fetchone()[0]

    def load_matrix(self) -> tuple[list[str], np.ndarray]:
        """Retourne `(clés, matrice float32)` triés par clé.

        La matrice est vide (shape `(0, 0)`) tant que rien n'est stocké, pour
        que les appelants démarrent sans cas particulier sur un projet neuf.
        """
        empty = ([], np.empty((0, 0), dtype=np.float32))
        if not self.exists():
            return empty

        res = self.con.execute(
            f"SELECT {self.table.key_column}, {self.table.vector_column} "
            f"FROM {self.table.name} ORDER BY {self.table.key_column}"
        ).fetchnumpy()
        keys = res[self.table.key_column].tolist()

        if not keys:
            return empty
        # Conversion en float32 pour réduire la mémoire utilisée.
        return keys, np.stack(res[self.table.vector_column]).astype(np.float32)

    # --- Écriture ---

    def upsert(self, rows) -> None:
        """Insère ou remplace des couples `(clé, vecteur)`.

        `INSERT OR REPLACE` plutôt qu'`INSERT` : ré-embedder une clé existante
        doit la mettre à jour, pas violer la clé primaire.
        """
        self.con.executemany(
            f"INSERT OR REPLACE INTO {self.table.name} VALUES (?, ?)",
            list(rows),
        )
