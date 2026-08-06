"""Filtres et fonctions Jinja : formats français, dates, mise en évidence."""

from datetime import date, datetime

from markupsafe import Markup, escape


def _as_datetime(value) -> datetime | None:
    """Normalise une valeur de date venant de la base ou d'une URL.

    Les vues HTML lisent les lignes brutes du driver : une colonne `date` ou
    `timestamp` arrive donc en objet Python, là où l'API JSON ne voyait que des
    chaînes ISO produites par Pydantic. Les deux formes doivent être acceptées.
    """
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day)
    if not value:
        return None
    try:
        # Les dates du jeu source finissent parfois en 'Z', que `fromisoformat`
        # n'accepte qu'à partir de 3.11 ; le remplacement garde la compatibilité.
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def fr_number(value) -> str:
    """Entier avec séparateur de milliers insécable (`1 234`), ou tiret cadratin."""
    if value is None:
        return "—"
    try:
        return f"{int(value):,}".replace(",", " ")
    except (TypeError, ValueError):
        return str(value)


def fr_date(value) -> str:
    """Date en JJ/MM/AAAA. Renvoie la valeur brute si elle est illisible."""
    parsed = _as_datetime(value)
    if parsed is None:
        return "" if not value else str(value)
    return parsed.strftime("%d/%m/%Y")


def fr_short_date(value) -> str:
    """Date en JJ/MM/AA, pour les colonnes serrées du tableau d'amendements."""
    parsed = _as_datetime(value)
    if parsed is None:
        return "" if not value else str(value)
    return parsed.strftime("%d/%m/%y")


def fr_month(value) -> str:
    """Date en 'JJ/MM', pour les axes serrés."""
    parsed = _as_datetime(value)
    if parsed is None:
        return "" if not value else str(value)
    return parsed.strftime("%d/%m")


# Abrégés de mois : `strftime('%b')` dépend de la locale du processus, qui n'est pas
# garantie française sur le serveur. La table évite de dépendre de `locale.setlocale`,
# qui est un état global du processus et n'est pas sûr avec plusieurs threads.
_MONTH_ABBR = [
    "janv.", "févr.", "mars", "avr.", "mai", "juin",
    "juil.", "août", "sept.", "oct.", "nov.", "déc.",
]


_MONTHS = [
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
]


def fr_week(value) -> str:
    """Seau d'histogramme 'YYYY-MM-DD' en '01 juin 26'."""
    parsed = _as_datetime(value)
    if parsed is None:
        return "" if not value else str(value)
    return f"{parsed.day:02d} {_MONTH_ABBR[parsed.month - 1]} {parsed.year % 100:02d}"


def fr_long_date(value) -> str:
    """Date en '3 juin 2026', pour les titres de scrutin."""
    parsed = _as_datetime(value)
    if parsed is None:
        return "" if not value else str(value)
    return f"{parsed.day} {_MONTHS[parsed.month - 1]} {parsed.year}"


def percent(score, digits: int = 0) -> str:
    """Score de similarité 0..1 affiché en pourcentage."""
    if score is None:
        return "—"
    try:
        return f"{round(float(score) * 100, digits):.{digits}f} %"
    except (TypeError, ValueError):
        return "—"


def highlight(text: str | None, needle: str | None, style: str = "") -> Markup:
    """Entoure chaque occurrence de `needle` d'un `<strong>`.

    Le texte vient de la base : il est échappé AVANT d'ajouter le balisage, sinon
    un exposé sommaire contenant du HTML serait interprété. L'auto-échappement de
    Jinja ne suffit pas ici : la fonction renvoie volontairement du balisage, donc
    elle doit échapper elle-même ce qui ne doit pas en être.
    """
    if not text:
        return Markup("")
    if not needle:
        return Markup(escape(text))

    safe_text = str(escape(text))
    safe_needle = str(escape(needle))

    lowered = safe_text.lower()
    target = safe_needle.lower()
    if not target or target not in lowered:
        return Markup(safe_text)

    # `style` est un littéral du gabarit, jamais une donnée de la base : il n'est
    # donc pas échappé, contrairement au texte et à l'aiguille.
    attr = f' style="{style}"' if style else ""

    out: list[str] = []
    start = 0
    while True:
        found = lowered.find(target, start)
        if found == -1:
            out.append(safe_text[start:])
            break
        out.append(safe_text[start:found])
        match = safe_text[found : found + len(safe_needle)]
        out.append(f"<strong{attr}>{match}</strong>")
        start = found + len(safe_needle)

    return Markup("".join(out))


def split_citation(text: str | None, citation: str | None) -> dict:
    """Découpe l'exposé sommaire autour de la citation détectée.

    L'index est calculé une seule fois pour que `before` et `after` ne puissent
    pas diverger sur l'emplacement de la citation. Citation introuvable :
    `found` est faux et `before` porte le texte entier, la vue rend alors l'exposé
    sans encadré. Un index de 0 (citation en tête) laisse `before` vide — le
    portage naïf renvoyait dans ce cas l'exposé complet et le dupliquait
    au-dessus de l'encadré.
    """
    body = text or ""
    if not citation:
        return {"found": False, "before": body, "after": ""}
    index = body.find(citation)
    if index < 0:
        return {"found": False, "before": body, "after": ""}
    return {
        "found": True,
        "before": body[:index],
        "after": body[index + len(citation) :],
    }


def strip_tags(value: str | None) -> str:
    """Texte brut d'un champ pouvant contenir du HTML (dispositif, exposé).

    Utilisé pour les extraits et les attributs `title`, où le balisage n'a pas de
    sens. Le rendu complet passe par `| safe` dans le gabarit concerné.
    """
    if not value:
        return ""
    out: list[str] = []
    depth = 0
    for char in value:
        if char == "<":
            depth += 1
        elif char == ">":
            depth = max(0, depth - 1)
        elif depth == 0:
            out.append(char)
    return " ".join("".join(out).split())


def truncate_words(value: str | None, count: int = 40) -> str:
    """Tronque à `count` mots, avec une ellipse si la coupe a lieu."""
    if not value:
        return ""
    words = value.split()
    if len(words) <= count:
        return " ".join(words)
    return " ".join(words[:count]) + "…"


def pluralize(count, plural: str = "s", singular: str = "") -> str:
    """Marque du pluriel français : au-delà de 1 seulement (0 reste au singulier)."""
    try:
        return plural if abs(int(count)) > 1 else singular
    except (TypeError, ValueError):
        return singular
