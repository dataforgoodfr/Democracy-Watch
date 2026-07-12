"""Détection exploratoire (v1, utilsant uniquement un llm) des mentions de collaboration externe dans les amendements.

On envoie l'exposé sommaire de chaque amendement à un modèle (API OpenAI-compatible) et on lui demande de repérer les passages où l'auteur déclare
avoir « travaillé avec », « été inspiré par », etc. une entité externe (lobby,
association, syndicat, entreprise, fédération professionnelle, ONG...).

Usage:
    uv run python -m analysis.detect_mentions --limit 50
    uv run python -m analysis.detect_mentions --limit 100 --offset 100
"""

import argparse
import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from openai import RateLimitError
from sqlalchemy import delete, text
from sqlalchemy.orm import Session

from etl.database import get_engine
from models.amendement_mention import AmendementMention

OUTPUT_DIR = Path("analysis/output")

SYSTEM_PROMPT = """\
Tu analyses des amendements de l'Assemblée nationale française. On te donne l'exposé
sommaire d'un amendement (le texte par lequel l'auteur justifie sa proposition).

Ta tâche : repérer chaque passage où l'auteur déclare que l'amendement a été élaboré,
travaillé, inspiré, proposé ou suggéré EN LIEN AVEC UN ACTEUR EXTERNE — par exemple un
lobby, une association, un syndicat, une entreprise, une fédération professionnelle, une
ONG, un think tank, un collectif citoyen. Signale aussi les cas ambigus.

Ne compte PAS comme mention le simple fait de citer un acteur (« comme le rappelle
l'INSEE »). Cherche une déclaration de COLLABORATION ou d'INSPIRATION revendiquée par
l'auteur de l'amendement.

Réponds UNIQUEMENT avec un objet JSON valide de la forme :
{
  "mentions": [
    {
      "citation": "<la phrase exacte tirée du texte, recopiée sans reformulation>",
      "formulation": "<l'expression déclencheuse, ex: 'travaillé avec', 'à l'initiative de'>",
      "entite": "<le nom de l'entité citée, ou null si non nommée>",
      "type_entite": "<lobby|association|syndicat|entreprise|federation_professionnelle|ong|think_tank|collectif_citoyen|organe_public|autre|inconnu>",
      "externe": <true si acteur d'intérêt privé/externe, false si institution publique>
    }
  ]
}
Si aucune mention, renvoie {"mentions": []}.
"""

USER_TEMPLATE = 'Exposé sommaire de l\'amendement :\n\n"""\n{expose}\n"""'


def get_config():
    api_key = os.getenv("LLM_API_KEY")
    base_url = os.getenv("LLM_BASE_URL")
    model = os.getenv("LLM_MODEL")
    if not api_key:
        raise SystemExit(
            "LLM_API_KEY manquante. Renseigne la clé du provider dans le fichier .env."
        )
    return api_key, base_url, model


def fetch_amendements(limit: int, offset: int, random_sample: bool = False):
    """Return a sample of (uid, numero, expose) with a non-trivial exposé sommaire.

    Par défaut, échantillon ordonné par `numeroOrdreDepot` (déterministe, paginable
    via offset). Avec random_sample=True, tirage aléatoire sur tout le corpus — utile
    en phase d'observation car les mentions sont rares et concentrées nulle part.
    """
    order_by = "random()" if random_sample else '"numeroOrdreDepot"'
    query = text(
        'SELECT uid, "numeroOrdreDepot", "exposeSommaire" '
        "FROM amendements "
        'WHERE "exposeSommaire" IS NOT NULL AND length("exposeSommaire") > 40 '
        f"ORDER BY {order_by} "
        "LIMIT :limit OFFSET :offset"
    )
    with get_engine().connect() as conn:
        rows = conn.execute(query, {"limit": limit, "offset": offset}).all()
    return rows


def parse_json(content: str) -> dict:
    """Extract a JSON object from a model reply, tolerating fences and prose.

    Les modèles OpenRouter ne supportent pas tous le mode `json_object` ; on
    n'impose donc aucun `response_format` et on récupère l'objet JSON à la main.
    """
    if not content or not content.strip():
        # Réponse vide du modèle : on considère qu'il n'y a pas de mention.
        return {"mentions": []}
    text = content.strip()
    if text.startswith("```"):
        # Retire un éventuel bloc ```json ... ```
        text = text.split("```", 2)[1] if text.count("```") >= 2 else text
        text = text.removeprefix("json").strip()
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1 and end > start:
        text = text[start : end + 1]
    return json.loads(text)


def detect(client: OpenAI, model: str, expose: str, max_retries: int = 4) -> dict:
    """Ask the model to extract collaboration mentions from one exposé sommaire.

    Réessaie sur 429 (rate limit) avec un backoff exponentiel plafonné : utile sur
    les modèles `:free` d'OpenRouter, très limités en requêtes/minute.
    """
    for attempt in range(max_retries + 1):
        try:
            response = client.chat.completions.create(
                model=model,
                temperature=0,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": USER_TEMPLATE.format(expose=expose)},
                ],
            )
            break
        except RateLimitError:
            if attempt == max_retries:
                raise
            wait = min(2**attempt, 30)
            print(f"    429 rate-limited, nouvelle tentative dans {wait}s...")
            time.sleep(wait)
    content = response.choices[0].message.content
    return parse_json(content)


def persist_mentions(session: Session, uid: str, mentions: list[dict], model: str):
    """Ecrit ou réécrit les mentions d'un amendement en base (delete puis insert).

    Idempotent : un re-run sur le même amendement remplace ses lignes existantes.
    """
    session.execute(
        delete(AmendementMention).where(AmendementMention.amendementUid == uid)
    )
    for m in mentions:
        externe = m.get("externe")
        session.add(
            AmendementMention(
                amendementUid=uid,
                citation=str(m.get("citation") or ""),
                formulation=m.get("formulation"),
                entite=m.get("entite"),
                typeEntite=m.get("type_entite"),
                externe=externe if isinstance(externe, bool) else None,
                modele=model,
            )
        )
    session.commit()


def run(
    limit: int,
    offset: int,
    random_sample: bool = False,
    delay: float = 4.0,
    persist: bool = False,
):
    load_dotenv()
    api_key, base_url, model = get_config()
    client = OpenAI(api_key=api_key, base_url=base_url)

    rows = fetch_amendements(limit, offset, random_sample)
    dest = "base + JSONL" if persist else "JSONL"
    print(f"Analyse de {len(rows)} amendements (modèle: {model}, sortie: {dest})...")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / "mentions_sample.jsonl"

    formulations: dict[str, int] = {}
    nb_avec_mention = 0
    session = Session(get_engine()) if persist else None

    try:
        with out_path.open("w", encoding="utf-8") as out:
            for i, (uid, numero, expose) in enumerate(rows, start=1):
                if i > 1:
                    time.sleep(delay)
                try:
                    result = detect(client, model, expose)
                    mentions = result.get("mentions", [])
                except Exception as e:  # noqa: BLE001 - on veut continuer le run
                    print(f"  [{i}/{len(rows)}] {uid}: erreur -> {e}")
                    out.write(
                        json.dumps({"uid": uid, "error": str(e)}, ensure_ascii=False)
                        + "\n"
                    )
                    continue

                out.write(
                    json.dumps(
                        {"uid": uid, "numero": numero, "mentions": mentions},
                        ensure_ascii=False,
                    )
                    + "\n"
                )

                if session is not None:
                    persist_mentions(session, uid, mentions, model)

                if mentions:
                    nb_avec_mention += 1
                    for m in mentions:
                        formulation = (m.get("formulation") or "?").strip().lower()
                        formulations[formulation] = formulations.get(formulation, 0) + 1
                    print(f"  [{i}/{len(rows)}] {uid}: {len(mentions)} mention(s)")
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
        "--limit", type=int, default=50, help="Nombre d'amendements à analyser"
    )
    parser.add_argument(
        "--offset", type=int, default=0, help="Décalage dans le jeu de données"
    )
    parser.add_argument(
        "--random",
        action="store_true",
        help="Tirage aléatoire sur tout le corpus (ignore l'offset)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=4.0,
        help="Pause en secondes entre deux appels (throttle anti rate-limit)",
    )
    parser.add_argument(
        "--persist",
        action="store_true",
        help="Écrit aussi les mentions dans la table amendement_mentions",
    )
    args = parser.parse_args()
    run(args.limit, args.offset, args.random, args.delay, args.persist)


if __name__ == "__main__":
    main()
