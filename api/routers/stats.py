"""Compteurs globaux du bandeau d'accueil."""

from fastapi import APIRouter

from api.db import fetch_one
from api.queries import stats as queries
from api.schemas import Stats

router = APIRouter(tags=["stats"])


def load_stats() -> dict:
    """Compteurs globaux. Partagés par la route JSON et la page d'accueil HTML."""
    # Les quatre sous-requêtes sont des agrégats : la ligne existe toujours.
    return fetch_one(queries.global_counts()) or {}


@router.get("/stats", response_model=Stats)
def get_stats() -> dict:
    """Nombre de dossiers, amendements, mentions et scrutins en base."""
    return load_stats()
