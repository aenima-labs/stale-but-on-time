"""Shared helpers for the task modules."""

import sys
from pathlib import Path

from invoke import Context

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
SRC_ENV = {"PYTHONPATH": str(ROOT / "src")}


def run_src(c: Context, script: str, args: str = "") -> None:
    """Run a script from src/ with the project's interpreter and src/ on PYTHONPATH."""
    c.run(f"{PY} src/{script} {args}".strip(), env=SRC_ENV, pty=False)
