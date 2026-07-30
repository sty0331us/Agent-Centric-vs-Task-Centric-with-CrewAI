"""Unit tests for FAQ search helpers, validation, and memory."""

from __future__ import annotations

from pathlib import Path

from daily_dish.config import PROJECT_ROOT, get_settings
from daily_dish.memory import ConversationMemory
from daily_dish.tools.assembly import build_retrieval_tools
from daily_dish.tools.pdf_search import expand_query_terms, split_faq_chunks
from daily_dish.validation import sanitize_query


def test_expand_query_terms_adds_hours_for_timings() -> None:
    terms = expand_query_terms("What are the timings?")
    assert "timings" in terms
    assert "hours" in terms


def test_split_faq_chunks_prefers_numbered_entries() -> None:
    text = (
        "1. Q: Hours? A: Open daily. "
        "2. Q: Location? A: Culinary Avenue. "
        "3. Q: Parking? A: Valet available."
    )
    chunks = split_faq_chunks(text)
    assert len(chunks) >= 2


def test_sanitize_query_rejects_empty_and_oversized() -> None:
    assert sanitize_query("   ").ok is False
    assert sanitize_query("x" * 501, max_chars=500).ok is False
    ok = sanitize_query("  What time do you open?  ")
    assert ok.ok is True
    assert ok.query == "What time do you open?"


def test_sanitize_query_strips_control_chars() -> None:
    result = sanitize_query("Hello\x00 world")
    assert result.ok is True
    assert "\x00" not in result.query


def test_conversation_memory_enriches_follow_up() -> None:
    memory = ConversationMemory(max_turns=2)
    memory.add("What are your hours?", "We open at 11.")
    enriched = memory.enrich_query("What about weekends?")
    assert "Recent conversation" in enriched
    assert "Current customer question: What about weekends?" in enriched
    memory.clear()
    assert len(memory) == 0


def test_build_retrieval_tools_respects_web_flag(faq_pdf: Path) -> None:
    settings = get_settings().model_copy(
        update={"faq_pdf_path": faq_pdf, "enable_web_search": False}
    )
    tools = build_retrieval_tools(settings)
    assert len(tools) == 1
    assert tools[0].name == "Search a PDF's content"


def test_project_root_points_at_repo() -> None:
    assert (PROJECT_ROOT / "pyproject.toml").is_file()
