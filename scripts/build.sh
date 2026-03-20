#!/usr/bin/env bash
# exit on error
set -o errexit

cd LeoRent_backend
pip install poetry
poetry install --no-root
# poetry run alembic upgrade head