"""Disposition verticale partagée du diagramme de flux des mentions.

La page et le diagramme SVG ont besoin exactement des mêmes positions de bandes
pour que les libellés texte s'alignent sur les barres. D'où une seule
implémentation appelée par les deux : dupliquer TRACK et GAP de chaque côté fait
qu'une modification de l'un désynchronise silencieusement l'autre.
"""

TRACK = 340
GAP = 8
MIN_BAND = 2


def compute_bands(items: list[dict]) -> dict[str, dict[str, float]]:
    """Répartit TRACK verticalement entre `items`, au prorata de leur `total`.

    Renvoie une correspondance clé -> {'y', 'h'} dans l'ordre reçu. La hauteur
    totale est garantie de rester dans TRACK, ce qui demande une passe explicite :
    le plancher MIN_BAND et l'arrondi par bande ajoutent tous deux de la hauteur,
    donc une longue traîne de petites sources (ou beaucoup d'items) débordait
    sinon du viewBox de 340 unités et les libellés dérivaient par rapport aux
    barres.
    """
    if not items:
        return {}

    total_val = sum(float(item["total"]) for item in items)
    count = len(items)

    # Avec beaucoup d'items, les seuls écarts peuvent dépasser TRACK ; on les
    # réduit plutôt que de laisser la hauteur disponible devenir négative.
    gap = min(GAP, TRACK / (2 * (count - 1))) if count > 1 else GAP
    available = max(0.0, TRACK - (count - 1) * gap)

    heights = []
    for item in items:
        share = float(item["total"]) / total_val if total_val > 0 else 1 / count
        heights.append(max(min(MIN_BAND, available / count), share * available))

    # Rééchelonne pour que les planchers et l'arrondi ne poussent pas la dernière
    # bande au-delà de TRACK.
    total_height = sum(heights)
    scale = available / total_height if total_height > available else 1.0

    bands: dict[str, dict[str, float]] = {}
    y = 0.0
    for item, height in zip(items, heights, strict=True):
        h = height * scale
        bands[item["key"]] = {"y": round(y, 2), "h": round(h, 2)}
        y += h + gap
    return bands


def compute_ribbons(
    groups: list[dict],
    sources: list[dict],
    links: list[dict],
) -> list[dict]:
    """Chemins SVG des rubans reliant un groupe à une entité citée.

    Chaque ruban part d'une tranche de la bande du groupe et arrive sur une
    tranche de celle de la source, proportionnelles à sa valeur : les décalages
    cumulés (`g_offset` / `s_offset`) empilent les rubans sans chevauchement.
    """
    group_pos = compute_bands(groups)
    source_pos = compute_bands(sources)
    source_by_key = {s["key"]: s for s in sources}

    g_sum: dict[str, float] = {}
    s_sum: dict[str, float] = {}
    for link in links:
        g_sum[link["group"]] = g_sum.get(link["group"], 0) + link["value"]
        s_sum[link["source"]] = s_sum.get(link["source"], 0) + link["value"]

    g_offset: dict[str, float] = {}
    s_offset: dict[str, float] = {}
    ribbons = []

    for link in links:
        gp = group_pos.get(link["group"])
        sp = source_pos.get(link["source"])
        if not gp or not sp:
            continue

        gh = (link["value"] / g_sum[link["group"]]) * gp["h"]
        sh = (link["value"] / s_sum[link["source"]]) * sp["h"]

        a1 = gp["y"] + g_offset.get(link["group"], 0.0)
        a2 = a1 + gh
        g_offset[link["group"]] = g_offset.get(link["group"], 0.0) + gh

        b1 = sp["y"] + s_offset.get(link["source"], 0.0)
        b2 = b1 + sh
        s_offset[link["source"]] = s_offset.get(link["source"], 0.0) + sh

        mx = 210
        source = source_by_key.get(link["source"], {})
        plural = "s" if link["value"] > 1 else ""

        ribbons.append(
            {
                "d": (
                    f"M10,{a1:.2f} C{mx},{a1:.2f} {mx},{b1:.2f} 410,{b1:.2f} "
                    f"L410,{b2:.2f} C{mx},{b2:.2f} {mx},{a2:.2f} 10,{a2:.2f} Z"
                ),
                "highlight": is_highlighted(source.get("typeEntite")),
                "opacity": round(0.1 + min(link["value"], 5) * 0.045, 3),
                "tooltip": (
                    f"{link['group']} → {link['source']} : "
                    f"{link['value']} amendement{plural}"
                ),
            }
        )

    return ribbons


def is_highlighted(type_entite: str | None) -> bool:
    """Les entités d'intérêt professionnel ressortent en accent dans le diagramme."""
    return type_entite in ("syndicat", "federation_professionnelle")
