import argparse

from dotenv import load_dotenv

from etl.database import create_db
from etl.download import run_download
from etl.etl import run_etl
from etl.embed import run_embed
from etl.embedding import DEFAULT_BACKEND
from etl.vectordb import reset_db as reset_vector_db


def run(parser):
    argv = parser.parse_args()

    if argv.download:
        run_download()
    elif argv.rebuild_database:
        create_db()
    elif argv.run_etl:
        run_etl()
    elif argv.rebuild_db_run_etl:
        create_db()
        run_etl()
    elif argv.rebuild_vector_database:
        reset_vector_db()
    elif argv.embed:
        run_embed(backend_name=argv.backend, model=argv.model, dossier=argv.dossier)
    else:
        parser.print_usage()


def get_argv_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-d",
        "--download",
        action="store_true",
        help="Download all data from API to file",
    )

    parser.add_argument(
        "-r",
        "--rebuild-database",
        action="store_true",
        help="Rebuild the database",
    )

    parser.add_argument(
        "-e",
        "--run-etl",
        action="store_true",
        help="Run etl",
    )

    parser.add_argument(
        "-a",
        "--rebuild-db-run-etl",
        action="store_true",
        help="Rebuild the database and run the etl",
    )
    parser.add_argument(
        "--rebuild-vector-database",
        action="store_true",
        help="Drop the DuckDB vector tables (they are recreated by --embed, at the "
        "dimension of the model in use)",
    )
    parser.add_argument(
        "--embed",
        action="store_true",
        help="Compute and store amendement embeddings (defaults to the local F2LLM model via sentence-transformers)",
    )
    parser.add_argument(
        "--backend",
        default=DEFAULT_BACKEND,
        help="Embedding backend: 'sentence-transformers' (local GPU, default) or 'ollama'",
    )
    parser.add_argument(
        "--dossier",
        default=None,
        help="Restrict --embed to the amendements of a single dossier (its uid, e.g. DLR5L16N47129)",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Override the embedding model id (default depends on the backend)",
    )
    return parser


def main():
    parser = get_argv_parser()
    run(parser)


if __name__ == "__main__":
    load_dotenv()
    main()
