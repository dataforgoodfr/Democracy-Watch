from sqlalchemy import select
from sqlalchemy.orm import Session

from etl.database import get_engine
from etl.embedding import DEFAULT_BACKEND, create_backend
from etl.vectordb import EmbeddingStore, VectorDimensionMismatch
from models.amendement import Amendement

# Number of rows to embed before committing to the database.
# This is a tradeoff between speed and memory usage.
# It also acts as a checkpoint in case of failure.
COMMIT_EVERY = 1000


def _text_for(amendement):
    expose = amendement.get("exposeSommaire") or ""
    return f"{expose}".strip()


def load_amendements(dossier=None):
    """Load data from Postgres.

    When `dossier` is given, only the amendements attached to that dossier
    (`amendements.dossierRefUid`) are loaded.
    """
    engine = get_engine()
    stmt = select(Amendement.uid, Amendement.exposeSommaire, Amendement.dispositif)
    if dossier:
        stmt = stmt.where(Amendement.dossierRefUid == dossier)
    with Session(engine) as session:
        rows = session.execute(stmt).mappings()
        return [dict(row) for row in rows]


def pending_amendements(amendements, embedded):
    """Amendements from `amendements` whose UID is not in the `embedded` set."""
    return [a for a in amendements if a["uid"] not in embedded]


def embed_into(store, backend, amendements):
    """Embed already-pending `amendements` into `store`, committing every
    :data:`COMMIT_EVERY` rows.

    Yields ``(done, total)`` after each committed chunk so callers can report
    progress. Assumes the table exists and its dimension matches the backend
    (see :meth:`EmbeddingStore.ensure_table`).
    """
    total = len(amendements)
    for i in range(0, total, COMMIT_EVERY):
        chunk = amendements[i : i + COMMIT_EVERY]
        texts = [_text_for(a) for a in chunk]
        embeddings = backend.embed_documents(texts)
        store.upsert((a["uid"], emb) for a, emb in zip(chunk, embeddings))
        yield min(i + COMMIT_EVERY, total), total


def run_embed(backend_name=DEFAULT_BACKEND, model=None, dossier=None):
    amendements = load_amendements(dossier)
    if dossier:
        print(f"\tdossier={dossier}")
        if not amendements:
            raise SystemExit(f"No amendement attached to dossier {dossier}")

    backend = create_backend(backend_name, **({"model": model} if model else {}))
    print(f"\tbackend={backend.name} dim={backend.dimension}")

    with EmbeddingStore(read_only=False) as store:
        try:
            store.ensure_table(backend.dimension)
        except VectorDimensionMismatch as e:
            raise SystemExit(str(e))

        pending = pending_amendements(amendements, store.keys())
        print(
            f"\t{len(amendements) - len(pending)} already embedded, "
            f"{len(pending)} pending"
        )

        for done, total in embed_into(store, backend, pending):
            print(f"\tembedded {done}/{total}")


if __name__ == "__main__":
    run_embed()
