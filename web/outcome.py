"""Interprétation des libellés de sort et de statut.

Ces fonctions existent parce que `"adopt" in libelle` est un piège sur ce jeu de
données : les deux libellés de scrutin sont « l'Assemblée nationale a adopté » et
« L'Assemblée nationale n'a pas adopté ». Un test de sous-chaîne rapporte donc
les DEUX comme adoptés, et les votes rejetés se retrouvent affichés avec le style
« adopté ». La négation est par conséquent toujours testée en premier.
"""

import unicodedata

Outcome = str  # 'adopted' | 'rejected' | 'pending' | 'unknown'


def deaccent(value: str | None) -> str:
    """Minuscule sans accents, pour comparer des libellés saisis à la main."""
    if not value:
        return ""
    decomposed = unicodedata.normalize("NFD", value)
    return "".join(c for c in decomposed if not unicodedata.combining(c)).lower().strip()


def scrutin_outcome(scrutin: dict | None) -> Outcome:
    """Sort d'un scrutin. Privilégie `scrutins.code`, énumération propre."""
    if not scrutin:
        return "unknown"

    code = (scrutin.get("code") or "").strip().lower()
    if code in ("adopté", "adopte"):
        return "adopted"
    if code in ("rejeté", "rejete"):
        return "rejected"

    # Repli sur le libellé : la négation est testée EN PREMIER.
    libelle = deaccent(scrutin.get("libelle"))
    if not libelle:
        return "unknown"
    if "n'a pas adopte" in libelle or "n a pas adopte" in libelle:
        return "rejected"
    if "a adopte" in libelle:
        return "adopted"
    return "unknown"


def sort_outcome(sort: str | None) -> Outcome:
    """Sort d'un amendement (`sortAmendement`).

    Les valeurs de ce jeu de données sont des libellés simples : Adopté, Rejeté,
    En traitement, Retiré, Irrecevable, Tombé, A discuter, Irrecevable 40,
    Non soutenu.
    """
    s = deaccent(sort)
    if not s:
        return "unknown"
    if s.startswith("adopte"):
        return "adopted"
    if s.startswith(
        ("rejete", "irrecevable", "tombe", "non soutenu", "retire")
    ):
        return "rejected"
    if s.startswith(("en traitement", "a discuter")):
        return "pending"
    return "unknown"


def statut_outcome(statut: str | None) -> Outcome:
    """Statut d'un dossier (« Texte adopté », « Texte rejeté »…)."""
    s = deaccent(statut)
    if not s:
        return "unknown"
    if "rejete" in s or "retrait" in s:
        return "rejected"
    if "adopte" in s:
        return "adopted"
    if any(k in s for k in ("lecture", "depose", "commission", "saisine")):
        return "pending"
    return "unknown"


def outcome_tag_class(outcome: Outcome) -> str:
    """Classe `ds.css` correspondant à un sort, pour les pastilles de statut."""
    return "tag-accent" if outcome == "adopted" else "tag-neutral"
