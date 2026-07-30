"""Pytest fixtures for local CrewAI storage under the project tree."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from daily_dish.config import PROJECT_ROOT
from daily_dish.runtime import ensure_local_storage


@pytest.fixture(autouse=True)
def _crewai_local_storage(tmp_path: Path) -> None:
    """Keep CrewAI SQLite artifacts inside a temp project-local folder."""
    ensure_local_storage(tmp_path)
    (PROJECT_ROOT / "logs").mkdir(parents=True, exist_ok=True)


@pytest.fixture(scope="session")
def faq_pdf(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Ensure a FAQ PDF exists for tool tests (generate if missing)."""
    packaged = PROJECT_ROOT / "data" / "faqs" / "daily_dish_faq.pdf"
    if packaged.is_file():
        return packaged

    script = PROJECT_ROOT / "scripts" / "generate_faq_pdf.py"
    spec = importlib.util.spec_from_file_location("generate_faq_pdf", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    out = tmp_path_factory.mktemp("faq") / "daily_dish_faq.pdf"
    src = PROJECT_ROOT / "data" / "faqs" / "daily_dish_faq.md"
    return module.generate(src, out)
