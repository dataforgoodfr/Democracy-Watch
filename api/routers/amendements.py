"""Fiche amendement : auteur, mentions, vote, amendements proches."""

from fastapi import APIRouter, HTTPException, Query

from api.db import fetch_all, fetch_one
from api.queries import amendements as queries
from api.queries.amendements import DEFAULT_SIMILAR_LIMIT, SIMILAR_CANDIDATE_LIMIT
from api.routers.scrutins import load_groupes_votants, load_scrutin
from api.schemas import AmendementDetail, Similar
from api.similarity import similarity_index

router = APIRouter(prefix="/amendements", tags=["amendements"])

__all__ = [
    "DEFAULT_SIMILAR_LIMIT",
    "SIMILAR_CANDIDATE_LIMIT",
    "get_amendement",
    "get_amendement_similars",
    "load_similars",
    "router",
]


def load_similars(amendement: dict, limit: int) -> list[dict]:
    """Amendements proches de `amendement`, triés par similarité décroissante.

    Le score est une similarité cosinus entre embeddings (voir
    `api/similarity.py`). Les candidats sans vecteur sont écartés : leur afficher
    un score de 0 les ferait passer pour « sans rapport » alors qu'ils n'ont
    simplement pas encore été embeddés.
    """
    if not similarity_index.available:
        return []

    candidates = fetch_all(
        queries.similar_candidates(
            dossier=amendement["dossierRefUid"],
            uid=amendement["uid"],
        )
    )
    if not candidates:
        return []

    scores = similarity_index.scores_for(
        amendement["uid"], [c["uid"] for c in candidates]
    )
    scored = [
        {**candidate, "score": scores[candidate["uid"]]}
        for candidate in candidates
        if candidate["uid"] in scores
    ]
    scored.sort(key=lambda c: c["score"], reverse=True)
    return scored[:limit]


def load_amendement_detail(uid: str, similar_limit: int = DEFAULT_SIMILAR_LIMIT) -> dict:
    """Fiche amendement complète. Partagée par la route JSON et la vue HTML.

    Lève `HTTPException(404)` si l'amendement n'existe pas : la vue HTML la
    traduit en page d'erreur via le gestionnaire d'exception de `api/main.py`.
    """
    amendement = fetch_one(queries.amendement_detail(uid))
    if amendement is None:
        raise HTTPException(status_code=404, detail="Amendement introuvable")

    scrutin = None
    groupes_votants: list[dict] = []
    if amendement["scrutinRefUid"]:
        scrutin = load_scrutin(amendement["scrutinRefUid"])
        if scrutin is not None:
            groupes_votants = load_groupes_votants(scrutin["uid"])

    return {
        "amendement": amendement,
        "mentions": fetch_all(queries.mentions_for_amendement(uid)),
        "scrutin": scrutin,
        "groupesVotants": groupes_votants,
        "similars": load_similars(amendement, similar_limit),
        "similarityAvailable": similarity_index.available,
    }


@router.get("/{uid}", response_model=AmendementDetail)
def get_amendement(
    uid: str,
    similar_limit: int = Query(DEFAULT_SIMILAR_LIMIT, ge=0, le=50),
) -> dict:
    """Un amendement, ses mentions, son scrutin éventuel et ses voisins textuels."""
    return load_amendement_detail(uid, similar_limit)


@router.get("/{uid}/similar", response_model=list[Similar])
def get_amendement_similars(
    uid: str,
    k: int = Query(DEFAULT_SIMILAR_LIMIT, ge=1, le=50),
    threshold: float = Query(0.0, ge=0.0, le=1.0),
) -> list[dict]:
    """Voisins d'un amendement seuls, pour recharger la liste sans la fiche entière.

    `threshold` est un ratio 0..1 (le curseur de l'UI est en pourcentage) et
    filtre après le tri, donc moins de `k` résultats peuvent revenir.
    """
    amendement = fetch_one(queries.amendement_similarity_keys(uid))
    if amendement is None:
        raise HTTPException(status_code=404, detail="Amendement introuvable")

    similars = load_similars(amendement, k)
    return [s for s in similars if s["score"] >= threshold]
