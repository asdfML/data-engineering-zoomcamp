# syntax = docker/dockerfile:1.4
FROM python:3.11-bullseye as build

ENV VIRTUAL_ENV /opt/venv
RUN python -m venv --copies $VIRTUAL_ENV
ENV PATH $VIRTUAL_ENV/bin:$PATH

ARG POETRY_VERSION=1.3.2
ENV POETRY_HOME /opt/poetry
ENV POETRY_CONFIG_DIR /etc/pypoetry
ENV POETRY_CACHE_DIR /var/cache/pypoetry
ENV PIP_CACHE_DIR /var/cache/pip
ENV PATH $POETRY_HOME/bin:$PATH

RUN --mount=type=cache,target=/var/cache/pypoetry \
    --mount=type=cache,target=/var/cache/pip \
    curl -sSL https://install.python-poetry.org | python -

COPY pyproject.toml poetry.toml poetry.lock /pyproject/

ARG POETRY_OPTIONS="--no-root"
RUN --mount=type=cache,target=/var/cache/pypoetry \
    --mount=type=cache,target=/var/cache/pip \
    poetry install $POETRY_OPTIONS --no-interaction -C /pyproject

WORKDIR /pyproject

FROM python:3.11-slim-bullseye as runtime

RUN rm -f /etc/apt/apt.conf.d/docker-clean && \
    echo 'Binary::apt::APT::Keep-Downloaded-Packages "true";' > /etc/apt/apt.conf.d/keep-cache

RUN --mount=type=cache,target=/var/cache/apt \
    --mount=type=cache,target=/var/lib/apt \
    apt update && apt-get --no-install-recommends install -y \
        libpq5 wget

COPY --from=build /opt/venv /opt/venv/
ENV VIRTUAL_ENV /opt/venv
ENV PATH $VIRTUAL_ENV/bin:$PATH

RUN set -eux; \
	groupadd zoomcamp --gid=10000 && \
	useradd -g zoomcamp --uid=10000 -d /home/zoomcamp -ms /bin/bash zoomcamp

USER zoomcamp

ENV PYTHONPATH /home/zoomcamp/de_zoomcamp/src
ENV PROJECT_ROOT /home/zoomcamp/de_zoomcamp
WORKDIR /home/zoomcamp/de_zoomcamp

FROM runtime as prod

COPY --chown=zoomcamp:zoomcamp src/ /home/zoomcamp/de_zoomcamp/src/
COPY --chown=zoomcamp:zoomcamp bin/ /home/zoomcamp/de_zoomcamp/bin/
