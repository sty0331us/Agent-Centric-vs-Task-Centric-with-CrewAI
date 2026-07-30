"""Optional web search tool wrapper for out-of-FAQ questions."""

from __future__ import annotations

import os

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class WebSearchInput(BaseModel):
    """Schema for web search."""

    query: str = Field(..., description="Public web search query")


class StubWebSearchTool(BaseTool):
    """
    Safe default when SERPER_API_KEY is not configured.

    Returns an explicit message so the agent can fall back to FAQ knowledge
    instead of hallucinating live web results.
    """

    name: str = "Search the internet"
    description: str = (
        "Search the public web for restaurant-related information that is not "
        "covered in the local FAQ PDF."
    )
    args_schema: type[BaseModel] = WebSearchInput

    def _run(self, query: str) -> str:
        return (
            "Web search is not configured (missing SERPER_API_KEY). "
            f"Unable to look up '{query}' online. Prefer the restaurant FAQ PDF."
        )


def build_web_search_tool() -> BaseTool:
    """
    Return CrewAI's SerperDevTool when credentials exist; otherwise a stub.

    Keeping the stub avoids hard failures in environments without web search.
    """
    if not os.getenv("SERPER_API_KEY"):
        return StubWebSearchTool()

    try:
        from crewai_tools import SerperDevTool

        return SerperDevTool()
    except Exception:  # pragma: no cover - optional dependency path
        return StubWebSearchTool()
