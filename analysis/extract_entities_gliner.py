"""Nommage des mentions de collaboration par NER zéro-shot (GLiNER, en local).

La passe regex (`analysis/detect_mentions_regex.py`) repère la *tournure* de
collaboration mais laisse `entite`/`typeEntite`/`externe` à NULL. La passe LLM
distante (branche `detect-mentions-poc`) les remplit, au prix d'un appel réseau
par amendement. GLiNER fait le même travail de nommage en local, sans clé d'API
ni throttle : le modèle multilingue tient en ~500 Mo et traite quelques dizaines
de phrases par seconde sur CPU.

On ne relit pas la colonne `citation` des lignes regex : l'exposé sommaire est
livré pré-formaté sur ~80 colonnes, et le détecteur regex coupe ses citations sur
ces retours à la ligne — souvent juste avant l'entité à nommer. On repart donc de
`exposeSommaire`, dont on rend les retours à la ligne de mise en forme
inoffensifs (voir :func:`unwrap`), et on réutilise les motifs de la passe regex
pour retrouver les tournures.

Les lignes produites sont taguées `modele='gliner:v1'` ; celles des autres
modèles (regex, llm) ne sont pas touchées.

Usage:
    uv run python -m analysis.extract_entities_gliner --dossier DLR5L17N53187
    uv run python -m analysis.extract_entities_gliner --limit 200 --persist
    uv run python -m analysis.extract_entities_gliner --persist   # tout le corpus
"""

import argparse
import json
import re
import time
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from analysis.detect_mentions_regex import (
    _WINDOW,
    PATTERNS,
    PUBLIC_ACTORS,
    sentence_around,
)
from etl.database import get_engine
from models.amendement import Amendement
from models.amendement_mention import AmendementMention

MODELE = "gliner:v1"
OUTPUT_DIR = Path("analysis/output")

# Modèle multilingue « small » : bon compromis pour du français (~500 Mo, CPU-friendly).
DEFAULT_MODEL = "urchade/gliner_multi-v2.1"
# 0.45 : calé sur le dossier DLR5L17N53187, où les sigles français peu fréquents
# (AFNUM à 0.46) passent sous 0.5 alors que les marques connues sont au-dessus de
# 0.8. Descendre à 0.35 n'ajoutait aucune entité sur ce dossier.
DEFAULT_THRESHOLD = 0.45

# Nombre de phrases envoyées à GLiNER en un lot, et fréquence des commits.
BATCH_SIZE = 64
COMMIT_EVERY = 200

# Libellés soumis à GLiNER -> vocabulaire `typeEntite` du modèle SQLAlchemy.
# Les libellés sont en français (la langue du corpus) et volontairement proches
# du vocabulaire cible pour limiter le post-traitement. « organisation » sert de
# filet de rappel : il attrape les sigles opaques (AFNUM, Afep…) que les libellés
# spécifiques manquent, au prix d'un type moins précis.
LABELS: dict[str, str] = {
    "entreprise": "entreprise",
    "syndicat": "syndicat",
    "association": "association",
    "ONG": "ong",
    "fédération professionnelle": "federation_professionnelle",
    "think tank": "think_tank",
    "collectif citoyen": "collectif_citoyen",
    "groupe de lobbying": "lobby",
    "institution publique": "organe_public",
    "organisation": "autre",
}

# Types considérés comme des acteurs d'intérêt privé/externe.
EXTERNAL_TYPES = {
    "entreprise",
    "syndicat",
    "association",
    "ong",
    "federation_professionnelle",
    "think_tank",
    "collectif_citoyen",
    "lobby",
}

# Types pour lesquels on ne tranche pas : `autre` vient du libellé générique
# « organisation », qui signifie « type non déterminé » et non « public ». Les y
# assimiler classerait Le Monde ou le CNRS en institution publique, et le
# diagramme (qui filtre sur `externe IS TRUE`) les perdrait silencieusement.
# NULL dit « à vérifier », ce que la colonne autorise explicitement.
UNDETERMINED_TYPES = {"autre", "inconnu"}

# Libellé générique : on lui préfère tout libellé spécifique sur le même empan.
GENERIC_LABEL = "organisation"

# L'acteur suit la tournure (« travaillé avec X ») : on ne retient que les
# entités commençant après elle, dans cette fenêtre de caractères.
ACTOR_WINDOW = 120

# Un sigle seul (AFNUM, CNIL) est un nom valide ; en dessous de 3 caractères,
# c'est du bruit de tokenisation.
MIN_ENTITY_LEN = 3


def unwrap(text: str) -> str:
    """Neutralise les retours à la ligne de mise en forme de l'exposé sommaire.

    Le texte source est livré replié sur ~80 colonnes. Comme `\\n` fait office de
    borne de phrase dans :func:`sentence_around`, ces coupures tronquent les
    citations en plein milieu. On remplace donc les retours à la ligne isolés par
    une espace, en préservant les lignes vides (vraies frontières de paragraphe)
    et les espaces insécables du corpus.
    """
    text = text.replace("\r\n", "\n").replace("\xa0", " ")
    # Marque les frontières de paragraphe, replie le reste, puis restaure.
    text = re.sub(r"\n[ \t]*\n+", "\x00", text)
    text = re.sub(r"\n[ \t]*", " ", text)
    return text.replace("\x00", "\n")


def triggers(expose: str) -> list[tuple[str, int, int]]:
    """Occurrences de tournures de collaboration : (formulation, début, fin).

    Reprend les motifs *et* les exclusions contextuelles de la passe regex : sans
    elles, GLiNER nomme volontiers une entité qui se trouve après la tournure sans
    en être le collaborateur (« des services tels que YouTube ou WhatsApp »).
    Contrairement à la passe regex, on garde toutes les occurrences d'une même
    famille : chacune peut nommer un acteur différent.
    """
    found = []
    for formulation, pattern, exclude_public, extra_exclude in PATTERNS:
        for m in pattern.finditer(expose):
            window = expose[m.end() : m.end() + _WINDOW]
            if exclude_public and PUBLIC_ACTORS.search(window):
                continue
            if extra_exclude is not None and extra_exclude.match(window):
                continue
            found.append((formulation, m.start(), m.end()))
    return sorted(found, key=lambda t: t[1])


def _rank(entity: dict) -> tuple[bool, float]:
    """Clé de préférence à empan égal : libellé spécifique d'abord, puis score.

    GLiNER note le même empan sous plusieurs libellés (« AFNUM » en organisation
    *et* en association). On préfère le libellé spécifique, qui porte
    l'information de type, même quand le générique score plus haut.
    """
    return (entity["label"] != GENERIC_LABEL, entity["score"])


def _pick_label(entities: list[dict]) -> list[dict]:
    """Déduplique les empans en préférant un libellé spécifique au libellé générique."""
    best: dict[tuple[int, int], dict] = {}
    for e in entities:
        key = (e["start"], e["end"])
        kept = best.get(key)
        if kept is None or _rank(e) > _rank(kept):
            best[key] = e
    return sorted(best.values(), key=lambda e: e["start"])


def actors_after(entities: list[dict], trigger_end: int) -> list[dict]:
    """Entités nommées situées juste après la tournure.

    Renvoie une liste : les collaborateurs sont souvent coordonnés
    (« avec l'AFNUM et de Samsung »), et ne garder que le premier perdrait
    la moitié des acteurs. Écarte les acteurs publics repérés par la liste de la
    passe regex : GLiNER type « Assemblée nationale » en institution, mais pas
    toujours « rapporteur » ou « Gouvernement ».
    """
    actors = []
    for e in _pick_label(entities):
        if e["start"] < trigger_end or e["start"] > trigger_end + ACTOR_WINDOW:
            continue
        name = e["text"].strip(" \t.,;:«»\"'()")
        if len(name) < MIN_ENTITY_LEN or name.islower():
            continue
        if PUBLIC_ACTORS.search(name):
            continue
        type_entite = LABELS.get(e["label"], "inconnu")
        actors.append(
            {
                "entite": name,
                "typeEntite": type_entite,
                "externe": None
                if type_entite in UNDETERMINED_TYPES
                else type_entite in EXTERNAL_TYPES,
                "score": round(float(e["score"]), 3),
            }
        )
    return actors


def fetch_amendements(limit: int | None, dossier: str | None):
    """(uid, exposeSommaire) des amendements éligibles, comme la passe regex."""
    query = (
        select(Amendement.uid, Amendement.exposeSommaire)
        .where(
            Amendement.exposeSommaire.is_not(None),
            func.length(Amendement.exposeSommaire) > 40,
        )
        .order_by(Amendement.numeroOrdreDepot)
    )
    if dossier:
        query = query.where(Amendement.dossierRefUid == dossier)
    if limit:
        query = query.limit(limit)
    with get_engine().connect() as conn:
        return conn.execute(query).all()


def build_units(rows):
    """Aplatit les amendements en unités (uid, formulation, citation, offset).

    Une unité = une occurrence de tournure à nommer. On les met à plat pour
    envoyer à GLiNER des lots de taille régulière, indépendamment du nombre de
    tournures par amendement.
    """
    units = []
    for uid, expose in rows:
        text = unwrap(expose)
        for formulation, start, end in triggers(text):
            citation = sentence_around(text, start, end)
            # Offset de la tournure à l'intérieur de la citation transmise à GLiNER.
            offset = citation.find(text[start:end])
            if offset == -1:
                continue
            units.append(
                {
                    "uid": uid,
                    "formulation": formulation,
                    "citation": citation,
                    "trigger_end": offset + (end - start),
                }
            )
    return units


def annotate(units, model, labels, threshold):
    """Nomme les unités par lots, en place (clé `actors`). Yield (fait, total)."""
    total = len(units)
    for i in range(0, total, BATCH_SIZE):
        chunk = units[i : i + BATCH_SIZE]
        predictions = model.batch_predict_entities(
            [u["citation"] for u in chunk], labels, threshold=threshold
        )
        for unit, entities in zip(chunk, predictions):
            unit["actors"] = actors_after(entities, unit["trigger_end"])
        yield min(i + BATCH_SIZE, total), total


def mentions_by_amendement(units) -> dict[str, list[dict]]:
    """Regroupe les unités nommées par amendement, en dédupliquant.

    Deux familles de tournures peuvent matcher la même phrase (« écrit avec le
    soutien de » déclenche *travaillé avec* et *avec le concours de*) : sans
    déduplication, le même acteur produirait deux lignes pour une seule
    collaboration et serait compté double dans le diagramme de flux. On garde une
    ligne par (entité, citation), la première formulation rencontrée faisant foi.
    """
    by_uid: dict[str, list[dict]] = {}
    for u in units:
        for actor in u.get("actors", []):
            mentions = by_uid.setdefault(u["uid"], [])
            key = (actor["entite"], u["citation"])
            if any((m["entite"], m["citation"]) == key for m in mentions):
                continue
            mentions.append(
                {**actor, "citation": u["citation"], "formulation": u["formulation"]}
            )
    return by_uid


def persist(session: Session, uid: str, mentions: list[dict]):
    """Réécrit les lignes gliner d'un amendement, sans toucher aux autres modèles."""
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
                entite=m["entite"],
                typeEntite=m["typeEntite"],
                externe=m["externe"],
                modele=MODELE,
            )
        )


def run(
    limit: int | None = None,
    dossier: str | None = None,
    persist_db: bool = False,
    threshold: float = DEFAULT_THRESHOLD,
    model_name: str = DEFAULT_MODEL,
):
    load_dotenv()
    rows = fetch_amendements(limit, dossier)
    units = build_units(rows)
    dest = "base + JSONL" if persist_db else "JSONL"
    scope = f"dossier {dossier}" if dossier else "corpus"
    print(
        f"Nommage GLiNER de {len(units)} tournures "
        f"({len(rows)} amendements, {scope}, sortie: {dest})..."
    )

    from gliner import GLiNER  # import tardif : chargement lourd (torch)

    started = time.monotonic()
    model = GLiNER.from_pretrained(model_name)
    print(
        f"\tmodele={model_name} seuil={threshold} ({time.monotonic() - started:.1f}s)"
    )

    started = time.monotonic()
    for done, total in annotate(units, model, list(LABELS), threshold):
        print(f"\tnommé {done}/{total}")
    elapsed = time.monotonic() - started
    rate = len(units) / elapsed if elapsed else 0
    print(f"\t{elapsed:.1f}s ({rate:.0f} tournures/s)")

    # Regroupe par amendement : la persistance est idempotente par amendement.
    by_uid = mentions_by_amendement(units)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / "mentions_gliner.jsonl"
    session = Session(get_engine()) if persist_db else None
    types: dict[str, int] = {}
    nb_mentions = 0

    try:
        with out_path.open("w", encoding="utf-8") as out:
            for i, (uid, mentions) in enumerate(by_uid.items(), start=1):
                out.write(
                    json.dumps(
                        {
                            "uid": uid,
                            "mentions": [
                                {
                                    "citation": m["citation"],
                                    "formulation": m["formulation"],
                                    "entite": m["entite"],
                                    "typeEntite": m["typeEntite"],
                                    "externe": m["externe"],
                                    "score": m["score"],
                                }
                                for m in mentions
                            ],
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
                if session is not None:
                    persist(session, uid, mentions)
                    if i % COMMIT_EVERY == 0:
                        session.commit()
                nb_mentions += len(mentions)
                for m in mentions:
                    types[m["typeEntite"]] = types.get(m["typeEntite"], 0) + 1
        if session is not None:
            session.commit()
    finally:
        if session is not None:
            session.close()

    named = sum(1 for u in units if u.get("actors"))
    pct = 100 * named / len(units) if units else 0
    print(f"\n{nb_mentions} mentions nommées sur {len(units)} tournures ({pct:.0f}%).")
    print(f"{len(by_uid)}/{len(rows)} amendements avec au moins une mention nommée.")

    # Le diagramme de flux ne retient que `externe IS TRUE` : on explicite les
    # trois populations pour que les mentions à trancher ne passent pas inaperçues.
    flat = [m for mentions in by_uid.values() for m in mentions]
    externe = sum(1 for m in flat if m["externe"] is True)
    public = sum(1 for m in flat if m["externe"] is False)
    undetermined = sum(1 for m in flat if m["externe"] is None)
    print(
        f"  externes : {externe} · publics (écartés) : {public} "
        f"· type non déterminé (externe=NULL, à vérifier) : {undetermined}"
    )
    print("Types d'entités (fréquence) :")
    for type_entite, count in sorted(types.items(), key=lambda kv: -kv[1]):
        print(f"  {count:4d}  {type_entite}")
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
        "--dossier",
        default=None,
        help="Restreindre à un dossier, ex. DLR5L17N53187",
    )
    parser.add_argument(
        "--persist",
        action="store_true",
        help=f"Écrit aussi les mentions dans amendement_mentions (modele='{MODELE}')",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=DEFAULT_THRESHOLD,
        help=f"Seuil de confiance GLiNER (défaut : {DEFAULT_THRESHOLD})",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Modèle GLiNER (défaut : {DEFAULT_MODEL})",
    )
    args = parser.parse_args()
    run(args.limit, args.dossier, args.persist, args.threshold, args.model)


if __name__ == "__main__":
    main()
