from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from etl.database import get_engine


def load(table, data):
    """Load into the database the data for the given_fields"""
    with Session(get_engine()) as session:
        insert_statement = insert(table).values(data).on_conflict_do_nothing()
        session.execute(insert_statement)
        session.commit()
