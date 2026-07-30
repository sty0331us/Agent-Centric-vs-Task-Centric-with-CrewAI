"""Customer service agent definitions."""

from __future__ import annotations

from collections.abc import Sequence

from crewai import Agent
from crewai.tools import BaseTool

from daily_dish.config import Settings, get_settings


def build_customer_service_agent(
    tools: Sequence[BaseTool] | None = None,
    *,
    settings: Settings | None = None,
) -> Agent:
    """
    Create the shared Customer Service Specialist agent.

    Tools may be attached here (agent-centric) or left empty and assigned
    per-task (task-centric). Task-level tools override agent-level tools
    when both are present.
    """
    cfg = settings or get_settings()
    return Agent(
        role="Customer Service Specialist",
        goal=(
            "Provide accurate, friendly answers about The Daily Dish restaurant "
            "using only trusted tools and verified FAQ content."
        ),
        backstory=(
            "You are the front-line specialist for The Daily Dish, a contemporary "
            "American restaurant. You know the house policies, hours, seating, "
            "and menu guidance. You never invent facts: you retrieve them with "
            "tools, then craft a warm, concise reply."
        ),
        tools=list(tools or []),
        verbose=cfg.verbose,
        allow_delegation=False,
        llm=cfg.openai_model_name,
    )
