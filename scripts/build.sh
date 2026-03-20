#!/usr/bin/env bash
# exit on error
set -o errexit

<<<<<<< Updated upstream
=======
cd LeoRent_backend
>>>>>>> Stashed changes
pip install poetry
poetry install --no-root
# poetry run alembic upgrade head