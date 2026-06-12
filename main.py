import argparse

from etl.download import run_download


def run(parser):
    argv = parser.parse_args()

    if argv.download:
        run_download()
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
    return parser


def main():
    parser = get_argv_parser()
    run(parser)


if __name__ == "__main__":
    main()
