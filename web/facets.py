"""Facettes de recherche, portées par la query string.

L'état des filtres vit dans l'URL et nulle part ailleurs : la lecture est le
parsing des paramètres de la requête, l'écriture la construction des liens
`hx-get`. Un rechargement complet et un échange HTMX partent donc exactement du
même état, et toute URL filtrée est partageable.
"""

from urllib.parse import urlencode

SORT_OPTIONS = [
    {"value": "relevance", "label": "Pertinence"},
    {"value": "date", "label": "Date"},
    {"value": "numero", "label": "N°"},
]
SORT_VALUES = {option["value"] for option in SORT_OPTIONS}


def clamp_page(page) -> int:
    """Page >= 1. `?page=0` ou `?page=-3` produirait sinon un OFFSET négatif."""
    try:
        return max(1, int(page))
    except (TypeError, ValueError):
        return 1


def last_page(total, page_size: int) -> int:
    """Dernier index de page pour un total donné, jamais inférieur à 1."""
    total = int(total or 0)
    return max(1, -(-total // page_size))


def normalise_sort(sort: str | None) -> str:
    """Tri connu, sinon le défaut. Un `?sort=` arbitraire ne doit rien casser."""
    return sort if sort in SORT_VALUES else "relevance"


def build_url(path: str, params: dict, **overrides) -> str:
    """URL avec `params` fusionnés à `overrides`, valeurs vides retirées.

    Les valeurs `None`, `False` et `""` sont omises au lieu d'être sérialisées :
    l'URL reste lisible et un filtre retiré disparaît réellement de la query
    string plutôt que d'y rester sous la forme `withMentions=false`.
    """
    merged = {**params, **overrides}
    query = {
        key: ("true" if value is True else str(value))
        for key, value in merged.items()
        if value not in (None, False, "", 0)
    }
    encoded = urlencode(query)
    return f"{path}?{encoded}" if encoded else path


def dossier_chips(path: str, params: dict) -> list[dict]:
    """Pastilles de filtre actives de la liste de dossiers.

    `remove_url` remet toujours `page` à 1 : retirer un filtre réduit le jeu de
    résultats, garder l'ancien numéro de page pouvait pointer sur une page qui
    n'existe plus.
    """
    chips = []
    if params.get("withMentions"):
        chips.append(
            {
                "key": "withMentions",
                "label": "Avec mentions externes",
                "accent": True,
                "remove_url": build_url(path, params, withMentions=None, page=None),
            }
        )
    return chips


#: Longueur maximale d'un libellé de pastille. Les désignations d'article sont des
#: phrases entières (« APRÈS L'ARTICLE 10, insérer l'article suivant: ») : sans
#: coupe, une seule pastille occupait toute la largeur de la barre.
CHIP_LABEL_MAX = 32


def _short(value: str) -> str:
    """Libellé écourté à `CHIP_LABEL_MAX`, l'entier restant dans l'infobulle."""
    text = " ".join(str(value).split())
    if len(text) <= CHIP_LABEL_MAX:
        return text
    return text[: CHIP_LABEL_MAX - 1].rstrip(" ,;:") + "…"


def amendement_chips(path: str, params: dict) -> list[dict]:
    """Pastilles de filtre actives de l'explorateur d'amendements.

    `title` porte la valeur entière quand `label` est écourté : l'infobulle reste
    le seul endroit où lire une désignation d'article complète.
    """
    chips = []
    if params.get("withMentions"):
        chips.append(
            {
                "key": "withMentions",
                "label": "Avec mentions externes",
                "title": "Avec mentions externes",
                "accent": True,
                "remove_url": build_url(path, params, withMentions=None, page=None),
            }
        )
    if params.get("article"):
        chips.append(
            {
                "key": "article",
                "label": _short(params["article"]),
                "title": params["article"],
                "accent": False,
                "remove_url": build_url(path, params, article=None, page=None),
            }
        )
    if params.get("groupe"):
        chips.append(
            {
                "key": "groupe",
                "label": f"Groupe : {params['groupe']}",
                "title": f"Groupe : {params['groupe']}",
                "accent": False,
                "remove_url": build_url(path, params, groupe=None, page=None),
            }
        )
    if params.get("sort_filter"):
        chips.append(
            {
                "key": "sort_filter",
                "label": f"Sort : {params['sort_filter']}",
                "title": f"Sort : {params['sort_filter']}",
                "accent": False,
                "remove_url": build_url(path, params, sort_filter=None, page=None),
            }
        )
    return chips


def page_url_builder(path: str, params: dict):
    """Fonction `page -> url` passée aux gabarits de pagination."""

    def url_for_page(page: int) -> str:
        return build_url(path, params, page=page if page > 1 else None)

    return url_for_page


def range_label(page: int, limit: int, total: int) -> str:
    """« 11–20 sur 824 », ou « aucun résultat »."""
    total = int(total or 0)
    if not total:
        return "aucun résultat"
    first = (page - 1) * limit + 1
    last = min(page * limit, total)
    return f"{first}–{last} sur {total}"
