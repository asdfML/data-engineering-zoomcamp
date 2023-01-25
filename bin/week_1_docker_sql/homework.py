#!/usr/bin/env python

"""Zoomcamp docker'n'sql preparation

Usage:
  homework.py ingest [options] (--append | --replace) <url> <database> <table>
  homework.py answers <database> <table_data> <table_zones>
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


def answers_command(database: str, table_data: str, table_zones: str) -> None:
    engine = create_engine(
        os.getenv("POSTGRES_HOST", "localhost"),
        int(os.getenv("POSTGRES_PORT", "5432")),
        os.getenv("POSTGRES_USER"),
        os.getenv("POSTGRES_PASSWORD"),
        database,
    )

    print("Question 1: Knowing docker tags")
    print("Answer 1:", "--iidfile string", "\n")

    print("Question 2: Understanding docker first run")
    print("Answer 2:", 3, "\n")

    connection: sa.future.Connection = engine.connect()

    print("Question 3: Count records")

    query = f"""
        SELECT count(*)
        FROM {table_data}
        WHERE lpep_pickup_datetime::DATE = '2019-01-15' AND
              lpep_dropoff_datetime::DATE = '2019-01-15'
    """

    result = connection.execute(sa.text(query))
    answer = result.scalar()

    print("Answer 3:", answer, "\n")

    print("Question 4: Largest trip for each day")

    query = f"""
        SELECT lpep_pickup_datetime::DATE as date, max(trip_distance) as max
        FROM {table_data}
        GROUP BY lpep_pickup_datetime::DATE
        ORDER BY max DESC LIMIT 1;
    """

    result = connection.execute(sa.text(query))
    answer = result.one()[0]

    print("Answer 4:", answer, "\n")

    print("Question 5: The number of passengers")

    query = f"""
        SELECT passenger_count as passengers, count(*) as count
        FROM {table_data}
        WHERE lpep_pickup_datetime::DATE = '2019-01-01'
        AND passenger_count BETWEEN 2 AND 3
        GROUP BY passenger_count;
    """

    result = connection.execute(sa.text(query))
    answer = result.mappings().all()

    print("Answer 5:", answer, "\n")

    print("Question 6: Largest tip")

    query = f"""
        SELECT dropoff_zones."Zone", max(tip_amount) as max_tip
        FROM {table_data}
            INNER JOIN {table_zones} as pickup_zones
                ON green_taxi_data."PULocationID" = pickup_zones."LocationID"
            INNER JOIN {table_zones} as dropoff_zones
                ON green_taxi_data."DOLocationID" = dropoff_zones."LocationID"
        WHERE pickup_zones."Zone" = 'Astoria'
        GROUP BY dropoff_zones."Zone"
        ORDER BY max_tip DESC LIMIT 1;
    """

    result = connection.execute(sa.text(query))
    answer = result.one()[0]

    print("Answer 6:", answer, "\n")

    connection.close()


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
    elif arguments["answers"]:
        answers_command(
            arguments["<database>"],
            arguments["<table_data>"],
            arguments["<table_zones>"],
        )
