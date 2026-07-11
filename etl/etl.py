from etl.database import get_tables_definition
from etl.extraction import extract
from etl.loading import load


def _get_table_metadata(table):
    tablename = table.name
    fields = [field.name for field in table.columns]
    return tablename, fields


def run_etl():
    """
    Extract from JSON files in './data' and persist(load) data in the databse.

    It uses the database schema to know what files to open, fields to read, and columns to populate.
    This requires that the JSON file's names and fields have a 1:1 correspondance in the DB.
        * filename => tablename
        * JSON fields => table columns
    """
    tables = get_tables_definition()
    for table in tables:
        tablename, fields = _get_table_metadata(table)
        data = extract(tablename, fields)
        load(table, data)
