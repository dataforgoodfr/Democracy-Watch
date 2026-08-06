"""Détection par expressions régulières (repérage seul) des mentions de collaboration.

On repère dans l'exposé sommaire les tournures de collaboration / inspiration avec un
acteur externe (« travaillé avec… », « en concertation avec… », « inspiré de… »), à
partir des familles de formulations réellement observées sur une partie du corpus.

Repérage seul : dans la DB on ne remplit que `citation` (la phrase qui matche) et `formulation`
(le libellé canonique de la famille). L'entité et son type sont laissés à NULL.
Les lignes sont taguées `modele='regex:v1'` dans amendement_mentions.

Usage:
    uv run python -m analysis.detect_mentions_regex           # tout le corpus, sans écrire en base
    uv run python -m analysis.detect_mentions_regex --persist # + écriture dans amendement_mentions
    uv run python -m analysis.detect_mentions_regex --limit 50
"""

import argparse
import json
import re
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from etl.database import get_engine
from models.amendement import Amendement
from models.amendement_mention import AmendementMention

MODELE = "regex:v1"
OUTPUT_DIR = Path("analysis/output")

# Apostrophe droite ou typographique.
_APO = "['’]"

# Acteurs publics / internes au Parlement : si l'un d'eux apparaît juste après la
# tournure, la mention n'est pas comptée (collaboration institutionnelle normale,
# pas une influence externe).
PUBLIC_ACTORS = re.compile(
    rf"\b(?:gouvernements?|s[ée]nats?|assembl[ée]e\s+nationale|commissions?|missions?"
    rf"|rapporteure?s?|s[ée]nateurs?|s[ée]natrices?|d[ée]put[ée]\w*"
    rf"|minist(?:res?|ères?)|conseil\s+d{_APO}[ée]tat|cour\s+des\s+comptes"
    rf"|pouvoirs\s+publics|premier\s+ministre|l[ée]gislateur)\b",
    re.IGNORECASE,
)

# Référents non-acteurs après « inspiré de » : inspiration d'un texte, d'un mécanisme
# juridique... et non d'un acteur. Vérifié en tout début de fenêtre (pas de nom
# d'acteur attendu ni de capitalisation exigée).
NON_ACTOR_REFERENT = re.compile(
    rf"^\s*(?:la\s+|le\s+|les\s+|l{_APO}|une?\s+|celle\s+|ceux\s+)?"
    r"(?:lois?|procédures?|rédactions?|directives?|jurisprudences?|dispositifs?"
    r"|mécanismes?|modèles?|systèmes?|droits?|articles?|textes?|expérimentations?"
    r"|exemples?|recherches?|logiques?|principes?|esprit|pratiques?|méthod\w+"
    r"|réglementations?|législations?|régimes?|amendements?|dispositions?)\b",
    re.IGNORECASE,
)

# Référents textuels ou institutionnels après « proposé par », « à la demande de »... :
# le texte de loi lui-même, un rapport, un groupe politique, un rôle administratif —
# pas un acteur externe.
TEXT_REFERENT = re.compile(
    rf"^\s*(?:le\s+|la\s+|les\s+|l{_APO}|ce\s+|cet\s+|cette\s+|d[ue]s?\s+"
    rf"|de\s+la\s+|de\s+l{_APO})*(?:présente?s?\s+)?"
    r"(?:textes?|projets?\s+de\s+loi|propositions?\s+de\s+loi|amendements?|articles?"
    r"|rapports?|études?|dispositifs?|rédactions?|alinéas?|lois?|codes?|groupes?"
    r"|autorités?|représentants?|agents?|présidents?|responsables?"
    r"|fournisseurs?|distributeurs?|cnil)\b",
    re.IGNORECASE,
)

# (formulation canonique, motif, exclure si acteur public ensuite, exclusion supplémentaire).
PATTERNS: list[tuple[str, re.Pattern, bool, re.Pattern | None]] = [
    # participe d'élaboration (+ éventuel « en lien/concertation... ») + « avec »
    (
        "travaillé avec",
        re.compile(
            r"\b(?:travaill(?:é|ée|és|ées)|(?:co-?)?constru(?:it|ite|its|ites)"
            r"|(?:co-?)?rédig(?:é|ée|és|ées)|(?:co-?)?écrit(?:e|s|es)?"
            r"|élabor(?:é|ée|és|ées)|conçu(?:e|s|es)?|prépar(?:é|ée|és|ées)"
            r"|réalis(?:é|ée|és|ées)|bâti(?:e|s|es)?)"
            r"(?:\s+(?:en\s+(?:lien|concertation|collaboration|partenariat|coopération)"
            r"|conjointement|étroitement))?\s+avec\b",
            re.IGNORECASE,
        ),
        True,
        None,
    ),
    # « en collaboration / concertation / partenariat avec » (sans participe devant)
    (
        "en collaboration avec",
        re.compile(
            r"\ben\s+(?:collaboration|concertation|partenariat|coopération)\s+avec\b",
            re.IGNORECASE,
        ),
        True,
        None,
    ),
    # « avec le concours / l'appui / le soutien / l'aide de »
    (
        "avec le concours de",
        re.compile(
            rf"\bavec\s+(?:le\s+concours|l{_APO}appui|le\s+soutien|l{_APO}aide)\s+d",
            re.IGNORECASE,
        ),
        True,
        None,
    ),
    # « inspiré de / s'inspire de » — seulement si le référent n'est pas un objet
    # juridique (loi, article, procédure...)
    (
        "inspiré de",
        re.compile(
            rf"\b(?:inspir(?:é|ée|és|ées)|s{_APO}inspir\w+)"
            rf"(?:\s+\w+ment)?\s+(?:de\s+|d{_APO}|du\s+|des\s+|par\s+)",
            re.IGNORECASE,
        ),
        True,
        NON_ACTOR_REFERENT,
    ),
    # « sur proposition / suggestion / recommandation de »
    (
        "sur proposition de",
        re.compile(
            r"\bsur\s+(?:proposition|suggestion|recommandation)s?\s+d", re.IGNORECASE
        ),
        True,
        TEXT_REFERENT,
    ),
    # « issu d'une proposition / des travaux de »
    (
        "issu d'une proposition de",
        re.compile(
            rf"\biss\w+\s+(?:d{_APO}une\s+proposition|des\s+travaux|de\s+propositions)\b",
            re.IGNORECASE,
        ),
        True,
        None,
    ),
    # « reprend … la demande / recommandation / proposition de »
    (
        "reprend la demande de",
        re.compile(
            r"\breprend\w*\b[^.]{0,30}?\b(?:proposition|recommandation|demande)s?\s+d",
            re.IGNORECASE,
        ),
        True,
        TEXT_REFERENT,
    ),
    # « recommandation(s) / préconisation(s) de X » ou « formulées par X »
    (
        "recommandation de",
        re.compile(
            rf"\b(?:recommandation|préconisation)s?\s+(?:de\s+|du\s+|des\s+|d{_APO}"
            r"|formulées?\s+par\s+)",
            re.IGNORECASE,
        ),
        True,
        TEXT_REFERENT,
    ),
    # « proposé / validé / demandé / formulé / suggéré / préconisé par X »
    (
        "proposé par",
        re.compile(
            r"\b(?:proposé|validé|recommandé|préconisé|suggéré|demandé"
            r"|formulé)(?:e|s|es)?\s+par\b",
            re.IGNORECASE,
        ),
        True,
        TEXT_REFERENT,
    ),
    # « à la demande de X »
    (
        "à la demande de",
        re.compile(rf"\bà\s+la\s+demande\s+d(?:e\s+|u\s+|es\s+|{_APO})", re.IGNORECASE),
        True,
        TEXT_REFERENT,
    ),
]

_BOUNDARIES = ".!?\n"

# Taille de la fenêtre inspectée après la tournure pour les exclusions contextuelles.
_WINDOW = 60


def sentence_around(txt: str, start: int, end: int) -> str:
    """Retourne la phrase englobant le match [start:end] (bornes = . ! ? ou saut de ligne)."""
    left = max((txt.rfind(b, 0, start) for b in _BOUNDARIES), default=-1)
    rights = [pos for b in _BOUNDARIES if (pos := txt.find(b, end)) != -1]
    right = min(rights) if rights else len(txt)
    return txt[left + 1 : right + 1].strip()


def detect(expose: str) -> list[dict]:
    """Retourne une mention par famille de formulation trouvée (dédupliquée par libellé).

    Pour chaque famille, on parcourt toutes les occurrences : une occurrence exclue
    (acteur public, référent non-acteur) n'empêche pas une occurrence valide plus loin.
    """
    mentions: dict[str, dict] = {}
    for formulation, pattern, exclude_public, extra_exclude in PATTERNS:
        for m in pattern.finditer(expose):
            window = expose[m.end() : m.end() + _WINDOW]
            if exclude_public and PUBLIC_ACTORS.search(window):
                continue
            if extra_exclude is not None and extra_exclude.match(window):
                continue
            mentions[formulation] = {
                "citation": sentence_around(expose, m.start(), m.end()),
                "formulation": formulation,
            }
            break
    return list(mentions.values())


def fetch_amendements(limit: int | None):
    """Return (uid, exposeSommaire) for all eligible amendments."""
    query = (
        select(Amendement.uid, Amendement.exposeSommaire)
        .where(
            Amendement.exposeSommaire.is_not(None),
            func.length(Amendement.exposeSommaire) > 40,
        )
        .order_by(Amendement.numeroOrdreDepot)
    )
    if limit:
        query = query.limit(limit)
    with get_engine().connect() as conn:
        return conn.execute(query).all()


def persist_mentions(session: Session, uid: str, mentions: list[dict]):
    """Réécrit les lignes regex d'un amendement, sans toucher celles des autres modèles."""
    session.execute(
        delete(AmendementMention).where(
            AmendementMention.amendementUid == uid,
            AmendementMention.modele == MODELE,
        )
    )
    for m in mentions:
        session.add(
            AmendementMention(
                amendementUid=uid,
                citation=m["citation"],
                formulation=m["formulation"],
                modele=MODELE,
            )
        )
    session.commit()


def run(limit: int | None = None, persist: bool = False):
    load_dotenv()
    rows = fetch_amendements(limit)
    dest = "base + JSONL" if persist else "JSONL"
    print(f"Analyse regex de {len(rows)} amendements (sortie: {dest})...")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / "mentions_regex.jsonl"

    formulations: dict[str, int] = {}
    nb_avec_mention = 0
    session = Session(get_engine()) if persist else None

    try:
        with out_path.open("w", encoding="utf-8") as out:
            for uid, expose in rows:
                mentions = detect(expose)
                out.write(
                    json.dumps({"uid": uid, "mentions": mentions}, ensure_ascii=False)
                    + "\n"
                )
                if session is not None:
                    persist_mentions(session, uid, mentions)
                if mentions:
                    nb_avec_mention += 1
                    for m in mentions:
                        f = m["formulation"]
                        formulations[f] = formulations.get(f, 0) + 1
    finally:
        if session is not None:
            session.close()

    print(f"\n{nb_avec_mention}/{len(rows)} amendements avec au moins une mention.")
    print("Formulations rencontrées (fréquence) :")
    for formulation, count in sorted(
        formulations.items(), key=lambda kv: kv[1], reverse=True
    ):
        print(f"  {count:3d}  {formulation}")
    print(f"\nRésultats détaillés : {out_path}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limiter le nombre d'amendements (défaut : tout le corpus)",
    )
    parser.add_argument(
        "--persist",
        action="store_true",
        help="Écrit aussi les mentions dans amendement_mentions (modele='regex:v1')",
    )
    args = parser.parse_args()
    run(args.limit, args.persist)


if __name__ == "__main__":
    main()
