#!/usr/bin/env python

"""Zoomcamp docker'n'sql preparation

Usage:
  homework.py ingest [options] (--append | --replace) <url> <database> <table>
  homework.py (-h | --help)
  homework.py --version

Options:
  --append                 Insert new values to the existing table.
  --replace                Drop the table before inserting new values.
  --dt-columns=<col1,col2> Comma-separated list of columns to convert to datetime.
  -d --download_dir=<dir>  Where downloaded files are stored [default: data/raw].
  -c --chunksize=<n>       Chunk size to write to db [default: 10000].
  -h --help                Show this screen.
  -v --version             Show version.
"""

import os
import pathlib
import urllib.parse
from operator import attrgetter
from typing import Literal

import pandas as pd
import sqlalchemy as sa
import sqlalchemy.future
from cytoolz import do, first, keyfilter, partial, thread_last, valfilter
from docopt import docopt
from tqdm import tqdm


def create_engine(
    host: str, port: int, user: str, password: str, database: str
) -> sa.future.engine.Engine:
    return sa.create_engine(
        f"postgresql://{user}:{password}@{host}:{port}/{database}", future=True
    )


def download_source(url, directory: str) -> pathlib.Path:
    dst_filepath = thread_last(
        url,
        urllib.parse.urlparse,
        attrgetter("path"),
        os.path.basename,
        (pathlib.Path, directory),
    )

    if not dst_filepath.exists():
        print("Downloading...")
        os.system(f"wget -q {url} --directory-prefix={directory}")
        print("Download completed")

    return dst_filepath


def ingest_command(
    url: str,
    database: str,
    table: str,
    *,
    if_exists: Literal["append", "replace"],
    download_dir: str,
    chunksize: int,
    datetime_columns: list[int] | None,
) -> int:
    """Ingests data into the PG database and returns the number of rows inserted"""
    filepath = download_source(url, download_dir)
    engine = create_engine(
        os.getenv("POSTGRES_HOST", "localhost"),
        int(os.getenv("POSTGRES_PORT", "5432")),
        os.getenv("POSTGRES_USER"),
        os.getenv("POSTGRES_PASSWORD"),
        database,
    )

    if if_exists == "replace":
        query = sa.text(f"DROP TABLE IF EXISTS {table}")
        thread_last(
            engine.connect(),
            (do, partial(sa.future.Connection.execute, statement=query)),
            (do, sa.future.Connection.commit),
            (do, sa.future.Connection.close),
        )

    ingest_chunk = partial(
        pd.DataFrame.to_sql, con=engine, name=table, if_exists="append", index=False
    )

    iterator = pd.read_csv(
        filepath,
        parse_dates=datetime_columns,
        iterator=True,
        chunksize=chunksize,
    )

    print(f"Launch data ingestion into the {database}.{table}")
    return thread_last(iterator, (map, ingest_chunk), tqdm, sum)


if __name__ == "__main__":
    arguments = docopt(__doc__, version="Zoomcamp docker'n'sql week1 homework")
    if arguments["ingest"]:
        if dt_columns := arguments["--dt-columns"]:
            dt_columns = thread_last(dt_columns.split(","), (map, str.strip), list)

        if_exists = thread_last(
            arguments,
            (keyfilter, lambda k: k in {"--append", "--replace"}),
            (valfilter, lambda v: v is True),
            dict.keys,
            first,
        )

        n_rows = ingest_command(
            arguments["<url>"],
            arguments["<database>"],
            arguments["<table>"],
            download_dir=arguments["--download_dir"],
            chunksize=int(arguments["--chunksize"]),
            datetime_columns=dt_columns,
            if_exists=if_exists.lstrip("-"),
        )

        print(f"{n_rows} rows successfully ingested to the table")
