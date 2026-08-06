"""Dossiers législatifs : liste filtrée, fiche, amendements, mentions.

Les routes ne portent plus de SQL : elles appellent les constructeurs de
`api/queries/dossiers.py` et les exécutent. Les vues HTML (`web/views/`)
réutilisent les mêmes fonctions de service définies ici.
"""

from fastapi import APIRouter, HTTPException, Query

from api.db import fetch_all, fetch_one
from api.mentions import build_mention_flow
from api.queries import dossiers as queries
from api.queries.dossiers import (
    AMENDEMENTS_MAX_PAGE_SIZE,
    DOSSIERS_PAGE_SIZE,
    LEGISLATURE,
)
from api.schemas import (
    AmendementList,
    DossierDetail,
    DossierList,
    DossierMentions,
)

# `web.legislative` ne dépend que de `web.outcome` : l'importer ici n'introduit pas
# de cycle avec `web.views`, qui consomme ce module. Le parcours est reconstitué au
# niveau du service pour que l'API JSON et la page HTML montrent les mêmes étapes.
from web.legislative import legislative_steps

router = APIRouter(prefix="/dossiers", tags=["dossiers"])

__all__ = [
    "AMENDEMENTS_MAX_PAGE_SIZE",
    "DOSSIERS_PAGE_SIZE",
    "LEGISLATURE",
    "get_dossier",
    "get_dossier_mentions",
    "list_dossier_amendements",
    "list_dossiers",
    "router",
]


@router.get("", response_model=DossierList)
def list_dossiers(
    q: str = "",
    page: int = Query(1, ge=1),
    procedure: str | None = None,
    statut: str | None = None,
    withMentions: bool = False,  # noqa: N803  # nom de query string côté UI
) -> dict:
    """Dossiers de la législature courante, filtrés et paginés.

    `q` cherche dans le titre et l'uid, `withMentions` ne garde que les dossiers
    dont au moins un amendement porte une mention détectée.
    """
    limit = DOSSIERS_PAGE_SIZE
    filters = {
        "q": q,
        "procedure": procedure,
        "statut": statut,
        "with_mentions": withMentions,
    }

    rows = fetch_all(queries.dossiers_page(page=page, limit=limit, **filters))
    # Même prédicat que la requête de page => le total colle toujours au jeu de lignes.
    total = fetch_one(queries.dossiers_count(**filters)) or {"total": 0}

    return {
        "dossiers": rows,
        "total": total["total"],
        "page": page,
        "limit": limit,
    }


@router.get("/{uid}", response_model=DossierDetail)
def get_dossier(uid: str) -> dict:
    """Fiche dossier : métadonnées, compteurs, dépôts par semaine, mentions par groupe."""
    dossier = fetch_one(queries.dossier_by_uid(uid))
    if dossier is None:
        raise HTTPException(status_code=404, detail="Dossier introuvable")

    return {
        "dossier": dossier,
        "stats": fetch_one(queries.dossier_stats(uid)) or {},
        "histogram": fetch_all(queries.dossier_histogram(uid)),
        "mentionsByGroup": fetch_all(queries.dossier_mentions_by_group(uid)),
        # Le repli sur `statut` couvre les bases dont `actesLegislatifs` n'a pas
        # encore été chargé : une seule étape plutôt qu'un parcours vide.
        "steps": legislative_steps(
            fetch_all(queries.dossier_actes(uid)),
            statut=dossier.get("statut"),
            last_acte_date=dossier.get("dateDernierActe"),
        ),
    }


@router.get("/{uid}/amendements", response_model=AmendementList)
def list_dossier_amendements(
    uid: str,
    q: str = "",
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=AMENDEMENTS_MAX_PAGE_SIZE),
    sort: str = "relevance",
    article: str | None = None,
    groupe: str | None = None,
    sort_filter: str | None = None,
    withMentions: bool = False,  # noqa: N803  # nom de query string côté UI
) -> dict:
    """Amendements d'un dossier, filtrés, triés et paginés.

    `sort` ordonne la liste (`date`, `numero`, `relevance`) tandis que
    `sort_filter` filtre sur le *sort* de l'amendement (adopté, rejeté…) — deux
    notions distinctes malgré la proximité des noms, héritée de l'URL de l'UI.
    """
    filters = {
        "q": q,
        "article": article,
        "groupe": groupe,
        "sort_filter": sort_filter,
        "with_mentions": withMentions,
    }

    rows = fetch_all(queries.amendements_page(uid, page=page, limit=limit, sort=sort, **filters))
    # Mêmes prédicats et mêmes jointures que la requête de page.
    total = fetch_one(queries.amendements_count(uid, **filters)) or {"total": 0}
    with_mentions = fetch_one(queries.amendements_with_mentions_count(uid)) or {"total": 0}

    return {
        "amendements": rows,
        "total": total["total"],
        "totalWithMentions": with_mentions["total"],
        "page": page,
        "limit": limit,
    }


@router.get("/{uid}/mentions", response_model=DossierMentions)
def get_dossier_mentions(uid: str) -> dict:
    """Flux groupe politique -> entité externe mentionnée, pour le diagramme."""
    counts = fetch_one(queries.mention_counts(uid)) or {"detected": 0, "named": 0}
    links = fetch_all(queries.mention_links(uid))

    flow = build_mention_flow(links)
    return {
        **flow,
        "detectedCount": counts["detected"],
        "namedCount": counts["named"],
    }
