"""Shared tool assembly used by both crew strategies."""

from __future__ import annotations

from crewai.tools import BaseTool

from daily_dish.config import Settings
from daily_dish.tools import build_pdf_search_tool, build_web_search_tool


def build_retrieval_tools(settings: Settings) -> list[BaseTool]:
    """
    Assemble retrieval tools from settings.

    PDF search is always included. Web search is appended only when enabled
    so both agent-centric and task-centric crews stay in sync.
    """
    tools: list[BaseTool] = [build_pdf_search_tool(settings.faq_pdf_path)]
    if settings.enable_web_search:
        tools.append(build_web_search_tool())
    return tools
