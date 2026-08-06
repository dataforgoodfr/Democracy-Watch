"""Barres de l'histogramme des dépôts par semaine.

Les décomptes de Postgres arrivent parfois en `Decimal` ou en chaîne selon le
driver, d'où la conversion explicite : comparer
des chaînes désignerait la mauvaise semaine comme pic ('9' > '124').
"""

from web.filters import fr_week


def histogram_bars(histogram: list[dict]) -> dict:
    """Barres, pic et libellés d'axe pour un histogramme hebdomadaire.

    Renvoie `{'bars': [...], 'peak': {...}, 'axis': [...]}`. Une hauteur
    plancher de 4 % garde les semaines à un seul dépôt visibles.
    """
    if not histogram:
        return {"bars": [], "peak": {"week": "", "cnt": 0}, "axis": []}

    counts = [int(bucket["cnt"] or 0) for bucket in histogram]
    max_cnt = max(max(counts), 1)
    peak_index = counts.index(max_cnt) if max_cnt in counts else 0
    peak = {"week": histogram[peak_index]["week"], "cnt": counts[peak_index]}

    bars = []
    for bucket, cnt in zip(histogram, counts, strict=True):
        plural = "s" if cnt > 1 else ""
        bars.append(
            {
                "pct": max(4, round((cnt / max_cnt) * 100)),
                "color": (
                    "var(--color-accent)"
                    if bucket["week"] == peak["week"]
                    else "var(--color-neutral-400)"
                ),
                "label": f"Semaine du {fr_week(bucket['week'])} : {cnt} amendement{plural}",
            }
        )

    # Dédoublonné pour qu'un histogramme d'un seul seau ne répète pas trois fois
    # le même libellé.
    raw_axis = [
        fr_week(histogram[0]["week"]),
        fr_week(histogram[len(histogram) // 2]["week"]),
        fr_week(histogram[-1]["week"]),
    ]
    axis = list(dict.fromkeys(label for label in raw_axis if label))

    return {"bars": bars, "peak": peak, "axis": axis}


def mentions_by_group_rows(rows: list[dict]) -> list[dict]:
    """Barres « mentions par groupe » : largeur relative au groupe le plus cité."""
    if not rows:
        return []
    counts = [int(row["cnt"] or 0) for row in rows]
    max_cnt = max(max(counts), 1)
    return [
        {
            "group_abbrev": row["group_abbrev"],
            "cnt": cnt,
            "pct": round((cnt / max_cnt) * 100),
            "accent": index == 0,
        }
        for index, (row, cnt) in enumerate(zip(rows, counts, strict=True))
    ]


def vote_share(groupe: dict, key: str) -> int:
    """Part en pourcentage d'un décompte de vote dans le total du groupe."""
    total = sum(
        int(groupe.get(field) or 0)
        for field in ("pour", "contre", "abstentions", "nonVotants")
    )
    value = int(groupe.get(key) or 0)
    if not total or not value:
        return 0
    return round((value / total) * 100)
