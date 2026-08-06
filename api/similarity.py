"""Similarité entre amendements, calculée sur les embeddings.

Les embeddings comparent le sens plutôt que le vocabulaire : deux amendements
peuvent dire la même chose sans partager de mots, ce qu'un Jaccard mot-à-mot ne
voit pas.

La matrice est chargée une fois depuis DuckDB et gardée en mémoire : ~13k
vecteurs de 1024 dimensions en float32 tiennent dans ~50 Mo, et un produit
scalaire sur 200 candidats est immédiat. L'alternative — une requête DuckDB par
appel — rouvrirait la base à chaque requête HTTP.
"""

import logging
import threading

import numpy as np

from etl.vectordb import EmbeddingStore

logger = logging.getLogger(__name__)


class SimilarityIndex:
    """Index en mémoire des embeddings d'amendements, interrogeable par uid.

    Les vecteurs sont normalisés au chargement, si bien qu'une similarité
    cosinus se réduit à un produit scalaire.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._loaded = False
        self._index: dict[str, int] = {}
        self._matrix: np.ndarray = np.empty((0, 0), dtype=np.float32)

    # --- Cycle de vie ---

    def load(self) -> None:
        """Charge la matrice depuis DuckDB. Idempotent, sûr entre threads.

        Une base absente ou vide n'est pas une erreur : l'API doit démarrer sur
        un projet où `just embed` n'a pas encore tourné. Les routes répondent
        alors avec une liste de similaires vide, `available` à False.
        """
        with self._lock:
            if self._loaded:
                return
            self._loaded = True
            try:
                with EmbeddingStore(read_only=True) as store:
                    uids, matrix = store.load_matrix()
            except Exception as exc:  # base absente, table absente, verrou…
                logger.warning(
                    "Embeddings indisponibles (%s) : la similarité est désactivée. "
                    "Lancer `just embed` pour l'activer.",
                    exc,
                )
                return

            if not uids:
                logger.warning(
                    "Base vectorielle vide : la similarité est désactivée. "
                    "Lancer `just embed` pour l'activer."
                )
                return

            self._index = {uid: i for i, uid in enumerate(uids)}
            self._matrix = _normalize_rows(matrix)
            logger.info(
                "Index de similarité chargé : %d vecteurs de dimension %d",
                self._matrix.shape[0],
                self._matrix.shape[1],
            )

    def unload(self) -> None:
        """Libère la matrice (arrêt de l'application)."""
        with self._lock:
            self._loaded = False
            self._index = {}
            self._matrix = np.empty((0, 0), dtype=np.float32)

    # --- Lecture ---

    @property
    def available(self) -> bool:
        """True si des vecteurs sont chargés et exploitables."""
        return self._matrix.size > 0

    def __contains__(self, uid: str) -> bool:
        return uid in self._index

    def scores_for(self, uid: str, candidates: list[str]) -> dict[str, float]:
        """Similarité cosinus entre `uid` et chaque candidat, par uid.

        Les candidats sans vecteur sont absents du résultat plutôt que scorés à
        0 : l'appelant distingue ainsi « pas encore embeddé » de « rien à voir ».
        Retourne un dictionnaire vide si `uid` lui-même n'a pas de vecteur.
        """
        reference = self._index.get(uid)
        if reference is None or not self.available:
            return {}

        known = [(c, self._index[c]) for c in candidates if c in self._index]
        if not known:
            return {}

        rows = self._matrix[[i for _, i in known]]
        # Vecteurs normalisés => le produit scalaire EST la similarité cosinus.
        scores = rows @ self._matrix[reference]
        # Le cosinus vit dans [-1, 1] ; l'UI attend un ratio 0..1 (elle l'affiche en
        # pourcentage), donc on écrase les valeurs négatives — « opposé » et « sans
        # rapport » sont tous deux « non similaire » ici.
        scores = np.clip(scores, 0.0, 1.0)
        return {uid: round(float(score), 4) for (uid, _), score in zip(known, scores)}


def _normalize_rows(matrix: np.ndarray) -> np.ndarray:
    """Normalise chaque ligne en norme L2, en laissant les lignes nulles à zéro."""
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    # Un vecteur nul (texte vide à l'embedding) diviserait par zéro ; on le laisse
    # tel quel, il obtiendra un score de 0 contre tout le monde.
    np.divide(matrix, norms, out=matrix, where=norms > 0)
    return matrix


#: Index partagé par le processus, chargé au démarrage (voir `api/main.py`).
similarity_index = SimilarityIndex()
