"""Application FastAPI : sert l'interface HTML et l'API JSON dans un seul processus.

Lancement en développement : `just api` (ou `uv run uvicorn api.main:app --reload`).
Les pages HTML (gabarits Jinja de `web/`) appellent directement les fonctions de
service des routeurs, sans passer par HTTP ; l'API `/api/**` reste publiée pour
les consommateurs tiers et pour `/docs`.
"""

import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import JSONResponse

# Chargé avant les imports qui lisent l'environnement au moment de la connexion.
load_dotenv()

from api.config import get_allowed_origins  # noqa: E402
from api.db import dispose_engine, fetch_one  # noqa: E402
from api.queries import health_probe  # noqa: E402
from api.routers import amendements, dossiers, scrutins, stats  # noqa: E402
from api.similarity import similarity_index  # noqa: E402
from web.templates import STATIC_DIR, render  # noqa: E402
from web.views import router as web_router  # noqa: E402

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Charge l'index de similarité au démarrage, libère les ressources à l'arrêt.

    Charger ici plutôt qu'à la première requête : la lecture de la base
    vectorielle prend quelques secondes, autant les payer au démarrage que sur
    une requête utilisateur.
    """
    similarity_index.load()
    yield
    similarity_index.unload()
    dispose_engine()


app = FastAPI(
    title="Democracy Watch API",
    description=(
        "Lecture des données parlementaires chargées par l'ETL. "
        "Les pages HTML de l'application appellent ces mêmes fonctions en direct."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# L'interface étant servie par ce même processus, elle est de même origine et n'a
# pas besoin de CORS : le réglage ne concerne que les consommateurs tiers de
# l'API JSON.
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_methods=["GET"],
    allow_headers=["*"],
)

api_router = APIRouter(prefix="/api")
api_router.include_router(stats.router)
api_router.include_router(dossiers.router)
api_router.include_router(amendements.router)
api_router.include_router(scrutins.router)
app.include_router(api_router)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Monté après /api pour que les routes JSON gardent la priorité ; les vues HTML
# n'ont de toute façon aucun chemin en commun avec elles.
app.include_router(web_router)


@app.exception_handler(StarletteHTTPException)
def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Page d'erreur HTML pour l'interface, JSON pour l'API.

    Le branchement se fait sur le chemin : un client de `/api/**` attend du JSON et
    recevrait sinon une page HTML impossible à décoder, tandis qu'un visiteur
    tombant sur un uid inconnu doit voir une page et non un objet brut.
    """
    if request.url.path.startswith(("/api", "/health")):
        return JSONResponse(
            {"detail": exc.detail}, status_code=exc.status_code, headers=exc.headers
        )

    return render(
        request,
        "error.html.j2",
        {"status_code": exc.status_code, "detail": exc.detail or "Page introuvable"},
        status_code=exc.status_code,
    )


@app.get("/health", tags=["health"])
def health() -> dict:
    """Sonde de disponibilité : état de Postgres et de l'index de similarité."""
    try:
        fetch_one(health_probe())
        database = "ok"
    except Exception as exc:
        # Une base indisponible doit se lire dans la réponse, pas provoquer un 500 :
        # c'est précisément ce que la sonde est censée rapporter.
        database = f"error: {exc}"

    return {
        "status": "ok" if database == "ok" else "degraded",
        "database": database,
        "similarity": "ok" if similarity_index.available else "unavailable",
    }
