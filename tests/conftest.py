"""Shared test helpers."""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def run_cli(*args: str) -> tuple[int, bytes, bytes]:
    """Run ``python -m csv_summary`` in a subprocess; return (rc, stdout, stderr)."""
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.run(
        [sys.executable, "-m", "csv_summary", *args],
        capture_output=True, env=env, cwd=str(ROOT), check=False,
    )
    return proc.returncode, proc.stdout, proc.stderr


@pytest.fixture
def write_csv(tmp_path: Path) -> Callable[..., Path]:
    """Write text (or bytes) to a file under tmp_path and return its path."""

    def _write(content: str | bytes, name: str = "data.csv") -> Path:
        path = tmp_path / name
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_bytes(content.encode("utf-8"))
        return path

    return _write


@pytest.fixture
def fixture_path() -> Callable[[str], Path]:
    return lambda name: FIXTURES / name
