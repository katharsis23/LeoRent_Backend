# tasks.py

"""

Invoke tasks list:

    inv --list  Displays all the tasks
    inv test    Runs pytest
    inv lint    Runs flake8
    inv dev     Runs server in dev mode(For now runs server default)
    inv check   Runs lint → test
    inv build   Builds package (poetry build) !!!{deprecated}
    inv all     Runs lint → test → build
    inv clean   Cleans up temporary files, cache etc
"""

# TODO:
# Add format, type, tasks

import sys
from pathlib import Path
from invoke import task, UnexpectedExit, Failure, Context, Collection


# ---------------- Configuration ----------------

PROJECT_DIR = Path(__file__).parent.resolve()
SRC_DIR = PROJECT_DIR / "src" / "leorent_backend"
TESTS_DIR = PROJECT_DIR / "tests"

# Colors
C = {
    "red": "\033[0;31m",
    "green": "\033[0;32m",
    "yellow": "\033[1;33m",
    "blue": "\033[0;34m",
    "nc": "\033[0m",
}


def echo(msg: str, color: str = "nc") -> None:
    print(f"{C[color]}{msg}{C['nc']}")


def success(msg: str = "OK") -> None:
    echo(f"✓ {msg}", "green")


def error(msg: str) -> None:
    echo(f"✗ {msg}", "red")


def info(msg: str) -> None:
    echo(f"→ {msg}", "blue")


# ---------------- Helpers ----------------

def poetry_run(c: Context, cmd: str, **kwargs):
    """Starts poetry command with pretty output"""
    full_cmd = f"poetry run {cmd}"
    info(f"Executing... {full_cmd}")
    try:
        c.run(full_cmd, pty=True, **kwargs)
        success()
    except UnexpectedExit as e:
        error(f"Command failed with exit code {e.result.exited}")
        sys.exit(1)
    except Failure:
        error("Command failed")
        sys.exit(1)


# ---------------- Tasks ----------------

@task
def lint(c: Context):
    """Runs flake8"""
    info("Linting code...")
    poetry_run(c, "flake8 src tests")


@task
def test(c: Context, cov=False, lastfailed=False):
    """Runs pytest"""
    info("Running tests...")
    cmd = "pytest"
    if cov:
        cmd += " --cov=src/leorent_backend --cov-report=term-missing"
    if lastfailed:
        cmd += " --lf"
    poetry_run(c, cmd)


@task
def dev(c: Context, reload=True):
    """Runs FastAPI server in dev mode (uvicorn)"""
    info("Running dev server...")
    reload_flag = "--reload" if reload else ""
    poetry_run(
        c,
        f"uvicorn src.leorent_backend.main:app --host 0.0.0.0 --port 8000 {reload_flag}",
    )


@task(pre=[lint, test])
def check(c: Context):
    """Runs lint → test"""
    success("All checks passed!")


# @task
# def build(c: Context):
#     """Builds package (poetry build)"""
#     info("Building package...")
#     poetry_run(c, "poetry build")


@task(post=[check])
def all(c: Context):
    """All at once: check + build"""
    success("All done successfully!")


@task
def clean(c: Context):
    """Cleans up temporary files, cache etc"""
    info("Cleaning project...")
    patterns = [
        "**/__pycache__",
        "**/*.pyc",
        ".pytest_cache",
        ".coverage",
        "htmlcov",
        "dist",
        "*.egg-info",
    ]
    for pat in patterns:
        c.run(f"find . -name '{pat}' -exec rm -rf {{}} +", warn=True)
    success("Cleared")


ns = Collection(
    lint,
    test,
    dev,
    check,
    # build,
    all,
    clean,
)
