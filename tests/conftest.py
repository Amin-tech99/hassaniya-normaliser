"""Pytest test configuration for local and CI stability."""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from uuid import uuid4

import pytest


class SafeTemporaryDirectory:
    """TemporaryDirectory replacement using plain mkdir for restricted envs."""

    def __init__(
        self,
        suffix: str | None = None,
        prefix: str | None = None,
        dir: str | None = None,
        ignore_cleanup_errors: bool = False,
    ) -> None:
        base_dir = Path(dir) if dir else Path(tempfile.gettempdir())
        base_dir.mkdir(parents=True, exist_ok=True)

        name = f"{prefix or 'tmp'}{uuid4().hex}{suffix or ''}"
        self.name = str(base_dir / name)
        Path(self.name).mkdir(parents=True, exist_ok=False)
        self._ignore_cleanup_errors = ignore_cleanup_errors

    def cleanup(self) -> None:
        shutil.rmtree(self.name, ignore_errors=True)

    def __enter__(self) -> str:
        return self.name

    def __exit__(self, exc_type, exc, tb) -> None:
        self.cleanup()


@pytest.fixture(scope="session", autouse=True)
def configure_temp_dir():
    """Force tests to use a writable temp directory inside the project."""
    base = Path(__file__).resolve().parents[1] / ".test_tmp"
    base.mkdir(parents=True, exist_ok=True)
    temp_path = str(base)

    old_tmp = os.environ.get("TMP")
    old_temp = os.environ.get("TEMP")
    old_tmpdir = os.environ.get("TMPDIR")
    old_tempdir = tempfile.tempdir
    old_temp_cls = tempfile.TemporaryDirectory

    os.environ["TMP"] = temp_path
    os.environ["TEMP"] = temp_path
    os.environ["TMPDIR"] = temp_path
    tempfile.tempdir = temp_path
    tempfile.TemporaryDirectory = SafeTemporaryDirectory

    try:
        yield
    finally:
        tempfile.TemporaryDirectory = old_temp_cls
        tempfile.tempdir = old_tempdir

        if old_tmp is None:
            os.environ.pop("TMP", None)
        else:
            os.environ["TMP"] = old_tmp

        if old_temp is None:
            os.environ.pop("TEMP", None)
        else:
            os.environ["TEMP"] = old_temp

        if old_tmpdir is None:
            os.environ.pop("TMPDIR", None)
        else:
            os.environ["TMPDIR"] = old_tmpdir
