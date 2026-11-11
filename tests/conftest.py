"""Shared fixtures."""

from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "works"
STATIC = ROOT / "static"


@pytest.fixture
def app():
    from app import create_app

    application = create_app()
    application.config.update(TESTING=True)
    return application


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def sample_work() -> dict:
    """A deep copy of the handscroll file, to break in tests."""
    return copy.deepcopy(json.loads((DATA / "01-wang-xizhi-watching-geese.json").read_text(encoding="utf-8")))


@pytest.fixture
def corpus_dir(tmp_path):
    """An empty data folder plus a static folder holding the real images."""
    data = tmp_path / "works"
    data.mkdir()
    static = tmp_path / "static"
    shutil.copytree(STATIC / "img", static / "img")

    def write(name: str, work: dict) -> Path:
        path = data / f"{name}.json"
        path.write_text(json.dumps(work, ensure_ascii=False), encoding="utf-8")
        return path

    return data, static, write
