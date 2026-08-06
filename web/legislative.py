"""Parcours législatif reconstitué depuis les actes de la procédure.

Le parcours vient des `actesLegislatifs` du dossier, pas d'un tableau figé : la
navette n'a pas un nombre d'étapes constant. La loi « fin de vie »
(DLR5L17N51670) en compte dix — deux lectures dans chaque chambre, CMP en
désaccord, nouvelle lecture, lecture définitive, Conseil constitutionnel — là où
un gabarit à cinq cases donnait à chaque texte le même parcours imaginaire.

Les actes forment un arbre : les racines sont les étapes de navette (`codeActe`
AN1, SN1, CMP, ANNLEC, ANLDEF, CC, PROM…) et leurs descendants le détail des
travaux (réunions, séances, rapports, décisions). Une étape est donc une racine,
et son résultat se lit sur l'acte de décision de son sous-arbre.
"""

from web.outcome import deaccent

# --- Libellés des étapes -------------------------------------------------------

#: Libellé lisible par code d'étape. La clé est le `codeActe` de la racine.
STAGE_LABELS = {
    "AN1": "Première lecture",
    "SN1": "Première lecture",
    "AN2": "Deuxième lecture",
    "SN2": "Deuxième lecture",
    "AN3": "Troisième lecture",
    "SN3": "Troisième lecture",
    "ANLUNI": "Lecture unique",
    "SNLUNI": "Lecture unique",
    "ANNLEC": "Nouvelle lecture",
    "SNNLEC": "Nouvelle lecture",
    "ANLDEF": "Lecture définitive",
    "SNLDEF": "Lecture définitive",
    "CMP": "Commission mixte paritaire",
    "CC": "Conseil constitutionnel",
    "PROM": "Promulgation de la loi",
    "AN-APPLI": "Mise en application de la loi",
    "SN-APPLI": "Mise en application de la loi",
}

#: Étapes dont le libellé se complète de la chambre saisie. CMP, Conseil
#: constitutionnel et promulgation portent une `chambre` dans les données sans
#: qu'un « au Sénat » ait le moindre sens : le complément est donc explicite.
CHAMBER_SUFFIXED = {
    "AN1", "SN1", "AN2", "SN2", "AN3", "SN3",
    "ANLUNI", "SNLUNI", "ANNLEC", "SNNLEC", "ANLDEF", "SNLDEF",
}

CHAMBER_SUFFIX = {"AN": "à l'Assemblée nationale", "SN": "au Sénat"}

#: Ordre de procédure, départage les étapes de même date.
STAGE_RANK = {
    "AN1": 10, "SN1": 10,
    "ANLUNI": 15, "SNLUNI": 15,
    "AN2": 20, "SN2": 20,
    "AN3": 30, "SN3": 30,
    "CMP": 40,
    "ANNLEC": 50, "SNNLEC": 50,
    "ANLDEF": 60, "SNLDEF": 60,
    "CC": 70,
    "PROM": 80,
    "AN-APPLI": 90, "SN-APPLI": 90,
}

#: `xsiType` du premier dépôt : l'acte qui ouvre le dossier.
DEPOT_TYPE = "DepotInitiative_Type"


def _stage_label(code: str, group: list[dict]) -> str:
    """Libellé d'une étape : « Deuxième lecture au Sénat », « Promulgation de la loi »…"""
    label = STAGE_LABELS.get(code)
    if not label:
        # Étape hors nomenclature : le libellé source vaut mieux qu'un code brut.
        first = group[0]
        return first.get("nomCanonique") or first.get("libelleCourtActe") or code or "Étape"
    # La chambre vient des actes du groupe : la nomenclature la porte déjà dans le
    # code (AN* / SN*), mais un code inattendu resterait ainsi correctement situé.
    chambre = next((a.get("chambre") for a in group if a.get("chambre")), "")
    suffix = CHAMBER_SUFFIX.get(chambre or "")
    if code in CHAMBER_SUFFIXED and suffix:
        return f"{label} {suffix}"
    return label


# --- Résultat d'une étape ------------------------------------------------------


def conclusion_outcome(conclusion: str | None) -> tuple[str, str]:
    """Sort et libellé court d'une conclusion d'étape.

    Les conclusions du jeu source sont très verbeuses (« adoptée, dans les
    conditions prévues à l'article 45, alinéa 3, de la Constitution ») et
    genrées selon que l'objet est un projet ou une proposition : on ne peut ni
    les afficher telles quelles, ni les comparer à une énumération. Le test se
    fait donc sur des radicaux, la négation d'abord — « considéré comme rejeté »
    contient bien « adopté » plus loin dans la phrase.
    """
    text = deaccent(conclusion)
    if not text:
        return "unknown", ""
    if "desaccord" in text:
        return "rejected", "Désaccord"
    if "accord" in text:
        return "adopted", "Accord"
    if "rejet" in text:
        return "rejected", "Texte rejeté"
    if "non conforme" in text:
        return "rejected", "Non conforme"
    if "partiellement conforme" in text:
        return "pending", "Partiellement conforme"
    if "conforme avec reserve" in text:
        return "adopted", "Conforme avec réserve"
    if "conforme" in text:
        return "adopted", "Conforme"
    if "adopte" in text:
        if "modification" in text and "sans modification" not in text:
            return "adopted", "Texte modifié"
        return "adopted", "Texte adopté"
    if "modifi" in text:
        return "adopted", "Texte modifié"
    if "definitive" in text:
        return "adopted", "Texte définitif"
    # Conclusion inconnue : on montre le libellé source, tronqué par le gabarit.
    return "unknown", (conclusion or "").strip().capitalize()


# --- Construction du parcours --------------------------------------------------


def _stage_code(acte: dict) -> str:
    """Code de l'étape à laquelle appartient un acte.

    Le regroupement se fait sur le préfixe du `codeActe` (« AN1-DEBATS-DEC » →
    « AN1 ») et non en remontant `parentUid` : sur les dossiers ouverts sous une
    législature antérieure, une partie des actes référence un parent absent du
    jeu de données (69 actes de la L17), et chacun d'eux serait alors pris pour
    une étape à part entière.
    """
    code = (acte.get("codeActe") or "").strip()
    # « AN-APPLI » et « SN-APPLI » sont des codes d'étape en deux segments : ils
    # sont reconnus tels quels avant la coupe au premier tiret.
    if code in STAGE_LABELS:
        return code
    return code.split("-", 1)[0]


def _date(acte: dict) -> str:
    """Date de l'acte en chaîne triable ('' si absente : ces actes existent)."""
    return str(acte.get("dateActe") or "")


def _stage_date(code: str, group: list[dict]) -> str | None:
    """Date d'ouverture d'une étape : celle de son acte de tête.

    L'acte de tête est celui dont le `codeActe` est exactement le code de l'étape
    (« AN1 », « CMP »…) : il porte la saisine de la chambre. Le plus ancien acte du
    groupe ne convient pas — les travaux préparatoires d'une commission peuvent
    être datés d'avant la saisine, ce qui ferait commencer la première lecture
    avant le dépôt du texte.
    """
    heads = [a for a in group if (a.get("codeActe") or "").strip() == code and _date(a)]
    if heads:
        return min(_date(a) for a in heads)
    return None


def _conclusion(group: list[dict]) -> dict | None:
    """Acte de décision d'une étape : le dernier acte conclu du groupe.

    Une étape porte parfois plusieurs conclusions — motions rejetées avant le vote
    sur l'ensemble, et pour une CMP l'accord en commission (`CMP-DEC`) puis le vote
    de son texte dans chaque chambre (`CMP-DEBATS-*-DEC`). La dernière dans le
    temps est celle qui décide du sort du texte à cette étape.
    """
    concluded = [a for a in group if a.get("libelleStatutConclusion")]
    if not concluded:
        return None
    return max(concluded, key=lambda a: (_date(a), a.get("uid") or ""))


def _depot_step(actes: list[dict]) -> dict | None:
    """Étape de dépôt initial, extraite de l'acte `DepotInitiative_Type`."""
    depots = [a for a in actes if a.get("xsiType") == DEPOT_TYPE]
    if not depots:
        return None
    depot = min(depots, key=lambda a: (_date(a) or "9999", a.get("uid") or ""))
    suffix = CHAMBER_SUFFIX.get(depot.get("chambre") or "")
    return {
        "label": f"Dépôt {suffix}" if suffix else "Dépôt du texte",
        "date": depot.get("dateActe"),
        "outcome": "unknown",
        "outcome_label": "",
        "detail": "",
    }


def steps_from_actes(actes: list[dict]) -> list[dict]:
    """Étapes du parcours, une par étape de la procédure, dans l'ordre chronologique.

    L'étape est datée de son *premier* acte (la saisine de la chambre) et triée sur
    son *dernier* : la nouvelle lecture s'ouvre au dépôt du texte en navette, qui
    précède la CMP dont elle découle, si bien qu'un tri sur la date d'ouverture
    intervertirait les deux. `STAGE_RANK` ne sert qu'à départager deux étapes
    achevées le même jour — coder l'ordre en dur serait faux dès qu'un texte part
    du Sénat.
    """
    if not actes:
        return []

    groups: dict[str, list[dict]] = {}
    for acte in actes:
        groups.setdefault(_stage_code(acte), []).append(acte)

    steps: list[dict] = []
    for code, group in groups.items():
        conclusion = _conclusion(group)
        outcome, outcome_label = conclusion_outcome(
            conclusion.get("libelleStatutConclusion") if conclusion else None
        )
        dates = sorted(d for d in (_date(a) for a in group) if d)
        rank = STAGE_RANK.get(code, 999)
        steps.append(
            {
                "label": _stage_label(code, group),
                "date": _stage_date(code, group) or (dates[0] if dates else None),
                "outcome": outcome,
                "outcome_label": outcome_label,
                # Libellé source complet, pour l'infobulle : « adoptée, dans les
                # conditions prévues à l'article 45, alinéa 3… ».
                "detail": (conclusion or {}).get("libelleStatutConclusion") or "",
                "sort_key": (dates[-1] if dates else "", rank),
            }
        )

    # Le dépôt initial est une étape à part entière alors qu'il n'est qu'un acte
    # au sein de la première lecture : il est daté du jour où le texte arrive, là
    # où l'étape qui le contient court jusqu'au vote.
    depot = _depot_step(actes)
    if depot:
        # Rang 0 et date du dépôt : le dépôt précède l'étape qui le contient, même
        # quand des travaux de commission antérieurs traînent dans le même groupe.
        steps.append({**depot, "sort_key": (str(depot["date"] or ""), 0)})

    steps.sort(key=lambda s: s["sort_key"])

    # La dernière étape est celle où en est le texte ; les précédentes sont
    # franchies. Aucune étape « à venir » n'est inventée : la suite d'une navette
    # dépend du vote qui n'a pas eu lieu.
    for index, step in enumerate(steps):
        step["state"] = "current" if index == len(steps) - 1 else "done"
        step.pop("sort_key", None)

    return steps


def legislative_steps(
    actes: list[dict] | None = None,
    statut: str | None = None,
    last_acte_date: str | None = None,
) -> list[dict]:
    """Parcours du texte, déduit des actes, avec repli sur le statut.

    Le repli couvre les dossiers dont les actes ne sont pas encore chargés (l'ETL
    ne les reprend que depuis l'ajout d'`actesLegislatifs`) : on montre alors la
    seule étape connue, celle du `statut`, plutôt que rien.
    """
    steps = steps_from_actes(actes or [])
    if steps:
        return steps
    if not statut:
        return []
    return [
        {
            "label": statut,
            "date": last_acte_date,
            "outcome": "unknown",
            "outcome_label": "",
            "detail": "",
            "state": "current",
        }
    ]
