"""Fiche scrutin public."""

from fastapi import APIRouter, Request

from api.routers.scrutins import get_scrutin
from web.templates import render

router = APIRouter()


@router.get("/scrutins/{uid}")
def scrutin_detail(request: Request, uid: str):
    """Un scrutin, son résultat et le vote agrégé de chaque groupe sur l'hémicycle."""
    data = get_scrutin(uid)
    return render(
        request,
        "scrutin_detail.html.j2",
        {"scrutin": data["scrutin"], "groupes_votants": data["groupesVotants"]},
    )


__all__ = ["router"]
