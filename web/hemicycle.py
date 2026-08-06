"""Placement d'un vote agrégé sur le plan de l'hémicycle."""

from web.seat_coords import SEAT_COORDS

FILL = {
    "pour": "#1d3461",
    "contre": "#ec3013",
    "abstention": "#9c9898",
    "nonVotant": "#c9c5c4",
}
LABEL = {
    "pour": "pour",
    "contre": "contre",
    "abstention": "abstention",
    "nonVotant": "non-votant",
}


def seats_for(groupes_votants: list[dict]) -> list[dict]:
    """Sièges coloriés d'un scrutin : une entrée {x, y, fill, tooltip} par siège.

    Le jeu de données n'a pas de vote nominatif (quel député a voté quoi), mais
    seulement les décomptes agrégés du groupe : la couleur d'un siège est donc une
    *affectation* sur les sièges réels du groupe, pas une affirmation sur qui y
    siège.
    """
    seats: list[dict] = []

    for groupe in groupes_votants:
        # Sièges réellement détenus par le groupe, triés pour que l'ordre de
        # remplissage soit stable d'un rendu à l'autre au lieu de dépendre de
        # l'ordre d'`array_agg` côté SQL.
        group_seats = sorted(
            number
            for number in (_as_int(s) for s in groupe.get("sieges") or [])
            if number is not None and number in SEAT_COORDS
        )

        pour = groupe.get("pour") or 0
        contre = groupe.get("contre") or 0
        abstentions = groupe.get("abstentions") or 0
        non_votants = max(0, len(group_seats) - pour - contre - abstentions)

        index = 0
        for kind, count in (
            ("pour", pour),
            ("contre", contre),
            ("abstention", abstentions),
            ("nonVotant", non_votants),
        ):
            for _ in range(count):
                if index >= len(group_seats):
                    break
                x, y = SEAT_COORDS[group_seats[index]]
                seats.append(
                    {
                        "x": x,
                        "y": y,
                        "fill": FILL[kind],
                        "tooltip": f"{groupe.get('group_abbrev')} · {LABEL[kind]}",
                    }
                )
                index += 1

    return seats


def _as_int(value) -> int | None:
    """`placeHemicycle` est stocké en texte, parfois avec des zéros en tête."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
