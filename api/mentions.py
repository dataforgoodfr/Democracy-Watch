"""Agrégation des mentions en graphe de flux groupe -> entité externe.

Le SQL rend une ligne par (groupe, entité, type, formulation) ; le diagramme a
besoin de trois collections distinctes — les nœuds de gauche (groupes), ceux de
droite (entités) et les liens entre eux — plus la répartition des formulations.
Ce repliement se fait ici et non en SQL : il faudrait sinon quatre requêtes là
où un seul passage sur les lignes suffit.
"""

from typing import Any


def build_mention_flow(rows: list[dict]) -> dict[str, list[dict[str, Any]]]:
    """Construit `groups`, `sources`, `links` et `formulations` depuis les lignes SQL.

    L'ordre d'insertion est conservé (les lignes arrivent triées par poids
    décroissant), sauf pour `formulations`, retrié explicitement puisqu'un même
    libellé peut être réparti sur plusieurs lignes.
    """
    groups: dict[str, dict] = {}
    sources: dict[str, dict] = {}
    links: dict[tuple[str, str], dict] = {}
    formulations: dict[str, int] = {}

    for row in rows:
        group_key = row["group_key"]
        source_key = row["source_key"]
        value = row["value"]

        group = groups.setdefault(
            group_key, {"key": group_key, "label": row["group_label"], "total": 0}
        )
        group["total"] += value

        source = sources.setdefault(
            source_key,
            {
                "key": source_key,
                "label": row["source_label"],
                "typeEntite": row["type_entite"],
                "total": 0,
                "groupCount": 0,
            },
        )
        source["total"] += value

        link_key = (group_key, source_key)
        if link_key not in links:
            links[link_key] = {"group": group_key, "source": source_key, "value": 0}
            # Compté à la création du lien : `groupCount` mesure le nombre de groupes
            # distincts qui citent l'entité, pas le nombre de lignes agrégées.
            source["groupCount"] += 1
        links[link_key]["value"] += value

        # Une mention sans formulation reste comptée : « autre » est une catégorie
        # visible du diagramme, pas une ligne à ignorer.
        label = row["formulation"] or "autre"
        formulations[label] = formulations.get(label, 0) + value

    return {
        "groups": list(groups.values()),
        "sources": list(sources.values()),
        "links": list(links.values()),
        "formulations": sorted(
            ({"label": label, "count": count} for label, count in formulations.items()),
            key=lambda f: f["count"],
            reverse=True,
        ),
    }
