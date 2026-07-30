"""Unit tests that do not require live LLM calls."""

from __future__ import annotations

from pathlib import Path

import pytest

from daily_dish.config import PROJECT_ROOT, WorkflowMode, get_settings
from daily_dish.crews.agent_centric import build_agent_centric_crew
from daily_dish.crews.task_centric import build_task_centric_crew
from daily_dish.tools.pdf_search import LocalPdfSearchTool, build_pdf_search_tool


@pytest.fixture(scope="session")
def faq_pdf(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Ensure a FAQ PDF exists for tool tests (generate if missing)."""
    packaged = PROJECT_ROOT / "data" / "faqs" / "daily_dish_faq.pdf"
    if packaged.is_file():
        return packaged

    import importlib.util

    script = PROJECT_ROOT / "scripts" / "generate_faq_pdf.py"
    spec = importlib.util.spec_from_file_location("generate_faq_pdf", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    out = tmp_path_factory.mktemp("faq") / "daily_dish_faq.pdf"
    src = PROJECT_ROOT / "data" / "faqs" / "daily_dish_faq.md"
    return module.generate(src, out)


def test_settings_defaults() -> None:
    settings = get_settings()
    assert settings.default_mode in WorkflowMode
    assert settings.faq_pdf_path.name.endswith(".pdf")


def test_pdf_search_finds_hours(faq_pdf: Path) -> None:
    tool = build_pdf_search_tool(faq_pdf)
    result = tool._run("timings hours operation")
    assert "Relevant Content" in result
    assert "11:00" in result or "Monday" in result


def test_pdf_search_missing_file(tmp_path: Path) -> None:
    missing = tmp_path / "nope.pdf"
    with pytest.raises(FileNotFoundError):
        LocalPdfSearchTool(pdf_path=missing)


def test_agent_centric_crew_wires_tools_on_agent(
    faq_pdf: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DAILY_DISH_FAQ_PDF_PATH", str(faq_pdf))
    get_settings.cache_clear()
    settings = get_settings().model_copy(update={"enable_web_search": False})

    crew = build_agent_centric_crew(settings)
    assert len(crew.agents) == 1
    assert len(crew.tasks) == 1
    # Tools are owned by the agent; CrewAI may also mirror them onto the task.
    assert len(crew.agents[0].tools) >= 1
    assert len(crew.tasks[0].tools) >= 1
    assert crew.agents[0].tools[0].name == crew.tasks[0].tools[0].name


def test_task_centric_crew_wires_tools_on_task(
    faq_pdf: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DAILY_DISH_FAQ_PDF_PATH", str(faq_pdf))
    get_settings.cache_clear()
    settings = get_settings().model_copy(update={"enable_web_search": False})

    crew = build_task_centric_crew(settings)
    assert len(crew.agents) == 1
    assert len(crew.tasks) == 2
    # Agent has no standing toolbox; only the retrieval task is armed.
    assert len(crew.agents[0].tools) == 0
    assert len(crew.tasks[0].tools) >= 1
    assert len(crew.tasks[1].tools) == 0
