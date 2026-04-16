FROM python:3.14-alpine

# Workdir
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false

# System dependencies
RUN apk update && apk add --no-cache \
    build-base \
    libpq-dev \
    curl \
    linux-headers \
    musl-dev

# Poetry install
RUN pip install poetry

# Dependencies copy
COPY LeoRent_backend/poetry.lock LeoRent_backend/pyproject.toml ./

# Dependencies install
ARG MODE=debug
RUN if [ "$MODE" = "production" ]; then \
    poetry install --no-root --only main; \
    else \
    poetry install --no-root; \
    fi

# Codebase copy
COPY LeoRent_backend/src/ ./src/

# Runtime environment comes from docker-compose env_file

# Linter check
# RUN if [ "$MODE" = "debug" ]; then \
#     ruff check ./src || true; \
#     fi 

EXPOSE 8000

# Process
CMD ["uvicorn", "src.leorent_backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]