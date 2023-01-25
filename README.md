# Data Engineering Zoomcamp 2023

Organiser: @DataTalksClub

Links

- https://github.com/DataTalksClub/data-engineering-zoomcamp
- https://www.youtube.com/watch?v=-zpVha7bw5A&list=PL3MmuxUbc_hJed7dXYoJw8DoCuVHhGEQb
- https://github.com/DataTalksClub/data-engineering-zoomcamp/tree/main/cohorts/2023

## Prepare environment

`!WARNING` _You need to have a new Docker installed to handle 1.4 syntax of the
Dockerfile. Docker version 20.10.7 and above is known to work._

`!WARNING` _Properly tested only with BuiltKit enabled. Follow the links for further
details: [documentation](https://docs.docker.com/build/buildkit/),
[stackoverflow](https://stackoverflow.com/questions/58592259/how-do-you-enable-buildkit-with-docker-compose)._

Create cross-project runtime shared cache volumes for pip and poetry. Saves time if
you're working on multiple projects and don't want to download the same packages over
and over again.

```bash
docker volume create -d local poetry-cache
docker volume create -d local pip-cache
```

Fill in the values of the environment variables in the .env file before starting any
services.

```bash
cp .env.dist .env

docker compose up -d
```

## Homework #1

#### Docker and SQL

```bash
docker compose build homework_docker_sql
docker compose run --rm homework_docker_sql ingest --replace --dt-columns=lpep_pickup_datetime,lpep_dropoff_datetime https://github.com/DataTalksClub/nyc-tlc-data/releases/download/green/green_tripdata_2019-01.csv.gz ny_taxi green_taxi_data
docker compose run --rm homework_docker_sql ingest --replace https://s3.amazonaws.com/nyc-tlc/misc/taxi+_zone_lookup.csv ny_taxi zones
docker compose run --rm homework_docker_sql answers ny_taxi green_taxi_data zones
```
