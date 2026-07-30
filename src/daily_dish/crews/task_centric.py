"""
Task-centric crew: tools are bound to the tasks that need them.

This is the preferred production pattern — deterministic, auditable, and
easier to secure because powerful tools are scoped to a single step.
"""

from __future__ import annotations

from crewai import Crew, Process, Task

from daily_dish.agents import build_customer_service_agent
from daily_dish.config import Settings, get_settings
from daily_dish.runtime import ensure_local_storage
from daily_dish.tools import build_retrieval_tools


def build_task_centric_crew(settings: Settings | None = None) -> Crew:
    """
    Two-task sequential crew with tools assigned at the task layer.

    Flow:
      customer_query
        → Task 1: FAQ (and optional web) retrieval  [tools attached here]
        → Task 2: response drafting                 [no tools — format only]
        → structured, friendly customer reply
    """
    ensure_local_storage()
    cfg = settings or get_settings()
    retrieval_tools = build_retrieval_tools(cfg)

    # Agent has NO tools — capability is granted per task instead.
    agent = build_customer_service_agent(tools=[], settings=cfg)

    search_task = Task(
        description=(
            "Search the restaurant's FAQ PDF for information related to the "
            "customer's query: '{customer_query}'.\n"
            "Extract only the facts needed to answer. Prefer precise quotes or "
            "paraphrases from the FAQ. If the FAQ lacks coverage, state that clearly."
        ),
        expected_output=(
            "A concise research brief listing relevant FAQ facts for the query. "
            "Do not write the final customer message yet."
        ),
        agent=agent,
        tools=retrieval_tools,  # task-level tool assignment (overrides agent tools)
    )

    respond_task = Task(
        description=(
            "Using the information gathered from the FAQ search, draft a friendly "
            "and comprehensive response to the customer's query: '{customer_query}'.\n"
            "Stay faithful to the research brief. Do not invent details. "
            "Keep a warm, professional restaurant voice."
        ),
        expected_output=(
            "A polished customer-facing reply ready to display in the chatbot. "
            "No tool call traces, no internal notes — only the message itself."
        ),
        agent=agent,
        context=[search_task],
        tools=[],  # formatting-only step — no tool access
    )

    return Crew(
        agents=[agent],
        tasks=[search_task, respond_task],
        process=Process.sequential,
        verbose=cfg.verbose,
    )
