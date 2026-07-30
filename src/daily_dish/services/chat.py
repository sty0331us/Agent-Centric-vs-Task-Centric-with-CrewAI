"""Application service that orchestrates crew runs outside the CLI layer."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from daily_dish.config import Settings, WorkflowMode
from daily_dish.crews import build_agent_centric_crew, build_task_centric_crew
from daily_dish.logging_setup import get_logger

logger = get_logger(__name__)


@dataclass(slots=True)
class TurnResult:
    """Normalized result for a single chatbot turn."""

    reply: str
    mode: WorkflowMode
    latency_ms: float
    agent_centric_reply: str | None = None
    task_centric_reply: str | None = None
    agent_centric_latency_ms: float | None = None
    task_centric_latency_ms: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "reply": self.reply,
            "mode": self.mode.value,
            "latency_ms": round(self.latency_ms, 2),
        }
        if self.agent_centric_reply is not None:
            payload["agent_centric_reply"] = self.agent_centric_reply
        if self.task_centric_reply is not None:
            payload["task_centric_reply"] = self.task_centric_reply
        if self.agent_centric_latency_ms is not None:
            payload["agent_centric_latency_ms"] = round(self.agent_centric_latency_ms, 2)
        if self.task_centric_latency_ms is not None:
            payload["task_centric_latency_ms"] = round(self.task_centric_latency_ms, 2)
        if self.metadata:
            payload["metadata"] = self.metadata
        return payload


def crew_result_text(result: Any) -> str:
    """Extract plain text from a CrewAI kickoff result."""
    if result is None:
        return ""
    if hasattr(result, "raw") and result.raw:
        return str(result.raw).strip()
    return str(result).strip()


class ChatService:
    """Run agent-centric / task-centric / compare workflows for one query."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def ask(self, mode: WorkflowMode, customer_query: str) -> TurnResult:
        """Execute one turn and return a structured result with timing."""
        started = time.perf_counter()
        inputs = {"customer_query": customer_query}

        if mode is WorkflowMode.AGENT_CENTRIC:
            reply = crew_result_text(build_agent_centric_crew(self.settings).kickoff(inputs=inputs))
            latency_ms = (time.perf_counter() - started) * 1000
            logger.info("agent_centric turn completed in %.0fms", latency_ms)
            return TurnResult(reply=reply, mode=mode, latency_ms=latency_ms)

        if mode is WorkflowMode.TASK_CENTRIC:
            reply = crew_result_text(build_task_centric_crew(self.settings).kickoff(inputs=inputs))
            latency_ms = (time.perf_counter() - started) * 1000
            logger.info("task_centric turn completed in %.0fms", latency_ms)
            return TurnResult(reply=reply, mode=mode, latency_ms=latency_ms)

        agent_started = time.perf_counter()
        agent_out = crew_result_text(
            build_agent_centric_crew(self.settings).kickoff(inputs=inputs)
        )
        agent_ms = (time.perf_counter() - agent_started) * 1000

        task_started = time.perf_counter()
        task_out = crew_result_text(build_task_centric_crew(self.settings).kickoff(inputs=inputs))
        task_ms = (time.perf_counter() - task_started) * 1000

        total_ms = (time.perf_counter() - started) * 1000
        logger.info(
            "compare turn completed total=%.0fms agent=%.0fms task=%.0fms",
            total_ms,
            agent_ms,
            task_ms,
        )
        return TurnResult(
            reply=task_out,
            mode=mode,
            latency_ms=total_ms,
            agent_centric_reply=agent_out,
            task_centric_reply=task_out,
            agent_centric_latency_ms=agent_ms,
            task_centric_latency_ms=task_ms,
        )
