"""
Agent-centric crew: tools live on the Agent; the LLM chooses what to call.

This pattern is flexible and quick to prototype, but tool selection is
non-deterministic and harder to audit in production.
"""

from __future__ import annotations

from crewai import Crew, Process, Task

from daily_dish.agents import build_customer_service_agent
from daily_dish.config import Settings, get_settings
from daily_dish.runtime import ensure_local_storage
from daily_dish.tools import build_retrieval_tools


def build_agent_centric_crew(settings: Settings | None = None) -> Crew:
    """
    Single-task crew where the agent holds the full toolbelt.

    Flow:
      customer_query
        → Agent (with PDF + optional web tools) reasons & picks tools
        → free-form customer reply
    """
    ensure_local_storage()
    cfg = settings or get_settings()
    tools = build_retrieval_tools(cfg)

    agent = build_customer_service_agent(tools=tools, settings=cfg)

    answer_task = Task(
        description=(
            "Handle the customer's query: '{customer_query}'.\n"
            "Use your available tools to find accurate information from The Daily "
            "Dish FAQ (and the web if configured), then write a friendly, complete "
            "reply. Do not invent hours, policies, or menu facts."
        ),
        expected_output=(
            "A single polished customer-facing message answering the query. "
            "If information is missing, say so politely and suggest calling the restaurant."
        ),
        agent=agent,
    )

    return Crew(
        agents=[agent],
        tasks=[answer_task],
        process=Process.sequential,
        verbose=cfg.verbose,
    )
