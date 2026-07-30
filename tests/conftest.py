"""Pytest fixtures for local CrewAI storage under the project tree."""

from __future__ import annotations

from pathlib import Path

import pytest

from daily_dish.config import PROJECT_ROOT
from daily_dish.runtime import ensure_local_storage


@pytest.fixture(autouse=True)
def _crewai_local_storage(tmp_path: Path) -> None:
    """Keep CrewAI SQLite artifacts inside a temp project-local folder."""
    ensure_local_storage(tmp_path)
    (PROJECT_ROOT / "logs").mkdir(parents=True, exist_ok=True)
