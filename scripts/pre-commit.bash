#!/usr/bin/env bash

# pre-commit hook — Minimal pipeline to avoid crushed CI/CD.

set -euo pipefail # Exit when error

# Colors
if [[ -t 1 ]]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    NC='\033[0m' # No Color
else
    RED='' GREEN='' YELLOW='' BLUE='' NC=''
fi

# Pretty display
info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
success() { echo -e "${GREEN}✓  $1${NC}"; }
warning() { echo -e "${YELLOW}⚠  $1${NC}"; }
error() { echo -e "${RED}✗  $1${NC}" >&2; }

echo -e "${BLUE}Starting pre-commit checks...${NC}"

# Directory (pyproject.toml)
if ! cd LeoRent_backend 2>/dev/null; then
    error "Issue with directory"
    exit 1
fi

# ────────────────────────────────────────────────────────────────
# 1. Flake8 — linter
# ────────────────────────────────────────────────────────────────
info "Linter(flake8)..."

if ! poetry run flake8 .; then
    error "Flake8 has encountered linter issues. Aborted..."
    error "Please Solve it"
    exit 1
fi

success "flake8 — success"

# ────────────────────────────────────────────────────────────────
# 2. Tests (pytest)
# ────────────────────────────────────────────────────────────────
info "Running tests (pytest)..."

if ! poetry run pytest -q --no-header; then
    error "Tests error"
    error "Aborted"
    exit 1
fi

success "Test success"

# ────────────────────────────────────────────────────────────────
echo -e "${GREEN}┌─────────────────────────────────────────────┐${NC}"
echo -e "${GREEN}│             Ready to commit                 │${NC}"
echo -e "${GREEN}└─────────────────────────────────────────────┘${NC}"

exit 0
