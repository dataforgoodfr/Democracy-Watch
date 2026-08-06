"""Routes JSON, une par ressource, et les fonctions de service qui les alimentent.

Ces fonctions (`list_dossiers`, `get_dossier`, …) sont aussi appelées directement
par les vues HTML de `web/views/`, de sorte que les deux interfaces partagent une
seule implémentation des requêtes.
"""

from api.routers import amendements, dossiers, scrutins, stats

__all__ = ["amendements", "dossiers", "scrutins", "stats"]
