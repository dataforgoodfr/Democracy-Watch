"""Fiche amendement."""

from fastapi import APIRouter, Request

from api.routers.amendements import load_amendement_detail
from web.templates import render

router = APIRouter()


@router.get("/amendements/{uid}")
def amendement_detail(request: Request, uid: str):
    """Un amendement : exposé, mentions, vote éventuel, voisins textuels."""
    data = load_amendement_detail(uid)
    amendement = data["amendement"]

    return render(
        request,
        "amendement_detail.html.j2",
        {
            "amendement": amendement,
            "mentions": data["mentions"],
            "scrutin": data["scrutin"],
            "groupes_votants": data["groupesVotants"],
            "similars": data["similars"],
            "similarity_available": data["similarityAvailable"],
            # Poussé dans l'historique local par `dwHistory()` au chargement, via
            # l'attribut `data-dw-entry` du gabarit.
            "history_entry": {
                "uid": uid,
                "numeroLong": amendement.get("numeroLong") or uid,
                "article": amendement.get("divisionArticleDesignation") or "",
                "groupeAbbrev": amendement.get("group_abbrev") or "",
                "sort": amendement.get("sortAmendement") or "",
            },
        },
    )


__all__ = ["router"]
