"""Routes HTML, montées à la racine de l'application.

Elles appellent directement les fonctions de service de `api/routers/` : pas de
saut HTTP, pas de SQL dupliqué. Un `HTTPException(404)` levé par ces fonctions
remonte jusqu'au gestionnaire de `api/main.py`, qui rend la page d'erreur.
"""

from fastapi import APIRouter

from web.views import amendements, dossiers, scrutins

router = APIRouter(include_in_schema=False)
router.include_router(dossiers.router)
router.include_router(amendements.router)
router.include_router(scrutins.router)

__all__ = ["router"]
