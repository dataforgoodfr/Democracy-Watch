"""Scrutins publics et vote agrégé par groupe."""

from fastapi import APIRouter, HTTPException

from api.db import fetch_all, fetch_one
from api.queries import scrutins as queries
from api.schemas import ScrutinDetail

router = APIRouter(prefix="/scrutins", tags=["scrutins"])


def load_groupes_votants(scrutin_uid: str) -> list[dict]:
    """Vote agrégé de chaque groupe, dans l'ordre de préséance.

    Partagé avec la fiche amendement, qui affiche le même bloc de vote.
    """
    return fetch_all(queries.groupes_votants(scrutin_uid))


def load_scrutin(uid: str) -> dict | None:
    """Un scrutin par uid, ou None. Partagé avec la fiche amendement."""
    return fetch_one(queries.scrutin_by_uid(uid))


@router.get("/{uid}", response_model=ScrutinDetail)
def get_scrutin(uid: str) -> dict:
    """Un scrutin et le détail de son vote par groupe."""
    scrutin = load_scrutin(uid)
    if scrutin is None:
        raise HTTPException(status_code=404, detail="Scrutin introuvable")

    return {"scrutin": scrutin, "groupesVotants": load_groupes_votants(uid)}
