"""Pages dossiers : accueil, fiche, explorateur d'amendements, mentions."""

from fastapi import APIRouter, Query, Request

from api.db import fetch_one
from api.queries.dossiers import amendements_facets
from api.routers.dossiers import (
    DOSSIERS_PAGE_SIZE,
    get_dossier,
    get_dossier_mentions,
    list_dossier_amendements,
    list_dossiers,
)
from api.routers.stats import load_stats
from web import facets
from web.templates import is_htmx, render

router = APIRouter()

AMENDEMENTS_PAGE_SIZE = 10


def amendement_facet_values(uid: str) -> dict[str, list[str]]:
    """Valeurs proposées par les menus de facettes, triées et sans trous.

    `array_agg` renvoie `None` quand aucune ligne ne correspond (dossier sans
    amendement chargé) : le repli sur une liste vide évite d'itérer sur `None`
    dans le gabarit. Le tri est fait ici et non en SQL, `array_agg(DISTINCT …)`
    ordonnant déjà par valeur brute — l'ordre voulu côté UI est insensible à la
    casse.
    """
    row = fetch_one(amendements_facets(uid)) or {}

    def values(key: str) -> list[str]:
        return sorted(
            (value for value in (row.get(key) or []) if value),
            key=lambda value: value.casefold(),
        )

    return {
        "articles": values("articles"),
        "groupes": values("groupes"),
        "sorts": values("sorts"),
    }


@router.get("/")
def index(
    request: Request,
    q: str = "",
    page: int = 1,
    withMentions: bool = False,  # noqa: N803  # nom de query string, aligné sur l'API
):
    """Accueil : compteurs globaux et liste de dossiers filtrable.

    Répond soit la page entière, soit le seul bloc de résultats quand HTMX le
    demande — même contexte de gabarit dans les deux cas, donc un rechargement
    d'URL filtrée produit exactement ce qu'un échange HTMX aurait produit.
    """
    page = facets.clamp_page(page)
    data = list_dossiers(q=q, page=page, withMentions=withMentions)

    # Page au-delà du dernier index : on rejoue sur la dernière page réelle plutôt
    # que d'afficher un tableau vide surmonté d'un « 21–8 sur 8 ». Le cas se
    # produit dès qu'un lien construit avant un changement de filtre est rejoué.
    last = facets.last_page(data["total"], data["limit"])
    if page > last:
        page = last
        data = list_dossiers(q=q, page=page, withMentions=withMentions)

    params = {"q": q, "withMentions": withMentions, "page": page if page > 1 else None}
    context = {
        "dossiers": data["dossiers"],
        "total": data["total"],
        "page": page,
        "limit": data["limit"],
        "params": params,
        "path": "/",
        "chips": facets.dossier_chips("/", params),
        "url_for_page": facets.page_url_builder("/", params),
        "range_label": facets.range_label(page, data["limit"], data["total"]),
    }

    if is_htmx(request):
        return render(request, "partials/dossier_results.html.j2", context)

    return render(request, "index.html.j2", {**context, "stats": load_stats()})


@router.get("/dossiers/{uid}")
def dossier_detail(request: Request, uid: str):
    """Fiche dossier : compteurs, parcours législatif, dépôts, mentions par groupe."""
    data = get_dossier(uid)
    stats = data["stats"]

    # Les COUNT(*) de Postgres peuvent arriver en chaîne selon le driver ; la
    # conversion évite une division de chaînes.
    total = int(stats.get("amendment_count") or 0)
    adopted = int(stats.get("adopted_count") or 0)

    return render(
        request,
        "dossier_detail.html.j2",
        {
            "dossier": data["dossier"],
            "stats": stats,
            "histogram": data["histogram"],
            "mentions_by_group": data["mentionsByGroup"],
            "adopted_pct": round((adopted / total) * 100) if total else 0,
            # Reconstitué par le service : la page et `/api/dossiers/{uid}`
            # montrent donc exactement les mêmes étapes.
            "steps": data["steps"],
        },
    )


@router.get("/dossiers/{uid}/amendements")
def dossier_amendements(
    request: Request,
    uid: str,
    q: str = "",
    page: int = 1,
    sort: str = "relevance",
    article: str | None = None,
    groupe: str | None = None,
    sort_filter: str | None = None,
    withMentions: bool = False,  # noqa: N803  # nom de query string, aligné sur l'API
    limit: int = Query(AMENDEMENTS_PAGE_SIZE, ge=1, le=100),
):
    """Explorateur d'amendements d'un dossier.

    Les facettes vivent dans la query string : `useSearchFacets` les y gardait
    déjà, la lecture est donc simplement le parsing de la requête et l'écriture la
    construction des liens `hx-get`.
    """
    page = facets.clamp_page(page)
    sort = facets.normalise_sort(sort)

    def fetch(page: int) -> dict:
        return list_dossier_amendements(
            uid,
            q=q,
            page=page,
            limit=limit,
            sort=sort,
            article=article,
            groupe=groupe,
            sort_filter=sort_filter,
            withMentions=withMentions,
        )

    data = fetch(page)

    # Même repli que sur l'accueil : au-delà de la dernière page, on rejoue la
    # requête sur la dernière page réelle plutôt que de servir un tableau vide.
    last = facets.last_page(data["total"], data["limit"])
    if page > last:
        page = last
        data = fetch(page)

    # Lève 404 si le dossier n'existe pas — la liste d'amendements, elle, revient
    # simplement vide pour un uid inconnu.
    dossier_data = get_dossier(uid)

    path = f"/dossiers/{uid}/amendements"
    params = {
        "q": q,
        "withMentions": withMentions,
        "article": article,
        "groupe": groupe,
        "sort_filter": sort_filter,
        "sort": sort,
        "page": page if page > 1 else None,
    }

    context = {
        "amendements": data["amendements"],
        "total": data["total"],
        "total_with_mentions": data["totalWithMentions"],
        "dossier_amendment_count": dossier_data["stats"].get("amendment_count") or 0,
        "page": page,
        "limit": data["limit"],
        "params": params,
        "path": path,
        "chips": facets.amendement_chips(path, params),
        "url_for_page": facets.page_url_builder(path, params),
        "range_label": facets.range_label(page, data["limit"], data["total"]),
        # Valeurs proposées par les menus de facettes. Elles décrivent le dossier
        # entier et non la page courante : une facette déjà appliquée ne doit pas
        # vider les autres menus.
        "facets": amendement_facet_values(uid),
    }

    if is_htmx(request):
        # Le tableau ET la barre de contrôle : sans la seconde, les pastilles et
        # les boutons `+` resteraient sur l'état précédent (la barre est hors de
        # `#amendement-results`, la cible de l'échange).
        return render(request, "partials/amendement_swap.html.j2", context)

    return render(
        request,
        "dossier_amendements.html.j2",
        {**context, "dossier": dossier_data["dossier"]},
    )


@router.get("/dossiers/{uid}/mentions")
def dossier_mentions(request: Request, uid: str):
    """Diagramme de flux groupe politique -> acteur extérieur cité."""
    data = get_dossier_mentions(uid)
    dossier_data = get_dossier(uid)

    return render(
        request,
        "dossier_mentions.html.j2",
        {
            "dossier": dossier_data["dossier"],
            "groups": data["groups"],
            "sources": data["sources"],
            "links": data["links"],
            "formulations": data["formulations"],
            "detected_count": data["detectedCount"],
            "named_count": data["namedCount"],
        },
    )


__all__ = ["DOSSIERS_PAGE_SIZE", "router"]
