import argparse

from dotenv import load_dotenv

from etl.database import create_db
from etl.download import run_download
from etl.etl import run_etl


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
    return parser


def main():
    parser = get_argv_parser()
    run(parser)


if __name__ == "__main__":
    load_dotenv()
    main()
