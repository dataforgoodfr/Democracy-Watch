from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from etl.database import get_engine

# Nombre de lignes par INSERT. Le protocole Postgres plafonne à 65 535 paramètres
# par requête : avec ~40 colonnes, 1 000 lignes restent largement sous la limite.
# Indispensable pour les tables volumineuses (mandats, coSignatairesDocument…) qui
# dépasseraient sinon la limite en un seul INSERT.
BATCH_SIZE = 1000


def load(table, data):
    """Load into the database the data for the given fields, in batches."""
    with Session(get_engine()) as session:
        for start in range(0, len(data), BATCH_SIZE):
            batch = data[start : start + BATCH_SIZE]
            session.execute(insert(table).values(batch).on_conflict_do_nothing())
        session.commit()
