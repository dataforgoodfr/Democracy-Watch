"""Requêtes de lecture, construites avec SQLAlchemy Core.

Aucun SQL n'est écrit en chaîne de caractères ici : chaque requête est un
`Select` bâti sur les modèles ORM de `models/`. Trois conséquences :

- les valeurs passent toujours en paramètres liés, y compris les motifs `ILIKE`,
  donc aucune injection n'est possible même sur les filtres facultatifs ;
- les filtres se composent en liste de conditions puis `and_(*conditions)`, là où
  la version précédente concaténait des fragments de SQL et les injectait avec
  `str.format()` ;
- les noms de colonnes sont vérifiés à l'import contre les modèles, ce qui
  transforme une faute de frappe en `AttributeError` au démarrage plutôt qu'en
  erreur Postgres à la première requête.

Les fonctions renvoient le `Select` sans l'exécuter, pour que les routes JSON
(`api/routers/`) et les vues HTML (`web/views/`) partagent exactement la même
requête.
"""

from api.queries.amendements import (
    amendement_detail,
    amendement_similarity_keys,
    mentions_for_amendement,
    similar_candidates,
)
from api.queries.dossiers import (
    amendements_count,
    amendements_page,
    amendements_with_mentions_count,
    dossier_by_uid,
    dossier_histogram,
    dossier_mentions_by_group,
    dossier_stats,
    dossiers_count,
    dossiers_page,
    mention_counts,
    mention_links,
)
from api.queries.scrutins import groupes_votants, scrutin_by_uid
from api.queries.stats import global_counts, health_probe

__all__ = [
    "amendement_detail",
    "amendement_similarity_keys",
    "amendements_count",
    "amendements_page",
    "amendements_with_mentions_count",
    "dossier_by_uid",
    "dossier_histogram",
    "dossier_mentions_by_group",
    "dossier_stats",
    "dossiers_count",
    "dossiers_page",
    "global_counts",
    "groupes_votants",
    "health_probe",
    "mention_counts",
    "mention_links",
    "mentions_for_amendement",
    "scrutin_by_uid",
    "similar_candidates",
]
