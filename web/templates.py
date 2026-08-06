"""Environnement Jinja de l'application : filtres, fonctions et rendu.

`Jinja2Templates` vient de Starlette (dépendance de FastAPI) : aucun paquet
supplémentaire n'est nécessaire. L'auto-échappement est actif par défaut sur les
gabarits `.html.j2`, donc toute valeur issue de la base est inerte sauf marquage
explicite (`| safe`, ou un filtre renvoyant `Markup`).
"""

from pathlib import Path

from fastapi import Request
from fastapi.templating import Jinja2Templates

from web import filters
from web.facets import SORT_OPTIONS, build_url
from web.flow_layout import compute_bands, compute_ribbons, is_highlighted
from web.hemicycle import seats_for
from web.histogram import histogram_bars, mentions_by_group_rows, vote_share
from web.outcome import (
    outcome_tag_class,
    scrutin_outcome,
    sort_outcome,
    statut_outcome,
)
from web.seat_coords import SEAT_VIEWBOX

TEMPLATES_DIR = Path(__file__).parent / "templates"
STATIC_DIR = Path(__file__).parent / "static"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# --- Filtres (`{{ value | fr_number }}`) ---
templates.env.filters.update(
    {
        "fr_number": filters.fr_number,
        "fr_date": filters.fr_date,
        "fr_short_date": filters.fr_short_date,
        "fr_long_date": filters.fr_long_date,
        "fr_month": filters.fr_month,
        "fr_week": filters.fr_week,
        "percent": filters.percent,
        "strip_tags": filters.strip_tags,
        "truncate_words": filters.truncate_words,
        "pluralize": filters.pluralize,
    }
)

# `int` accepte ici les décomptes que Postgres renvoie en chaîne ou en Decimal :
# comparer ou additionner ces valeurs telles quelles donnerait '9' > '124'.
templates.env.filters["as_int"] = lambda value: int(value or 0)

# --- Fonctions globales (`{{ sort_outcome(x) }}`) ---
templates.env.globals.update(
    {
        "SEAT_VIEWBOX": SEAT_VIEWBOX,
        "SORT_OPTIONS": SORT_OPTIONS,
        "build_url": build_url,
        "compute_bands": compute_bands,
        "compute_ribbons": compute_ribbons,
        "highlight": filters.highlight,
        "histogram_bars": histogram_bars,
        "is_highlighted": is_highlighted,
        "mentions_by_group_rows": mentions_by_group_rows,
        "outcome_tag_class": outcome_tag_class,
        "scrutin_outcome": scrutin_outcome,
        "seats_for": seats_for,
        "sort_outcome": sort_outcome,
        "split_citation": filters.split_citation,
        "statut_outcome": statut_outcome,
        "vote_share": vote_share,
    }
)


def render(
    request: Request,
    template: str,
    context: dict | None = None,
    status_code: int = 200,
):
    """Rend un gabarit avec le contexte donné.

    `request` est requis par Starlette (il alimente `url_for` dans les gabarits)
    et passé en premier argument, signature recommandée depuis Starlette 0.29.
    """
    return templates.TemplateResponse(
        request, template, context or {}, status_code=status_code
    )


def is_htmx(request: Request) -> bool:
    """True si la requête vient d'HTMX et attend donc un fragment, pas une page.

    HTMX pose l'en-tête `HX-Request` sur toutes ses requêtes ; s'y fier permet à
    une même route de servir la page entière (navigation, rechargement, partage
    d'URL) et le seul bloc de résultats (filtre, tri, pagination).
    """
    return request.headers.get("HX-Request") == "true"
