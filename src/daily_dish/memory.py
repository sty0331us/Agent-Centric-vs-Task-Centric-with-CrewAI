"""Short-term conversation memory for the interactive REPL."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass


@dataclass(slots=True)
class MemoryTurn:
    """One customer/assistant exchange."""

    question: str
    answer: str


class ConversationMemory:
    """
    Keep the last N turns so follow-ups like "what about weekends?" have context.

    Memory is process-local and intentionally small for customer-service demos.
    """

    def __init__(self, max_turns: int = 3) -> None:
        self._turns: deque[MemoryTurn] = deque(maxlen=max(0, max_turns))

    def add(self, question: str, answer: str) -> None:
        if self._turns.maxlen == 0:
            return
        self._turns.append(MemoryTurn(question=question, answer=answer))

    def clear(self) -> None:
        self._turns.clear()

    def as_context(self) -> str:
        if not self._turns:
            return ""
        lines = ["Recent conversation:"]
        for idx, turn in enumerate(self._turns, start=1):
            lines.append(f"{idx}. Customer: {turn.question}")
            lines.append(f"   Assistant: {turn.answer}")
        return "\n".join(lines)

    def enrich_query(self, question: str) -> str:
        """Attach recent turns to the current question for the crew input."""
        context = self.as_context()
        if not context:
            return question
        return (
            f"{context}\n\n"
            f"Current customer question: {question}\n"
            "Answer the current question. Use recent conversation only when it clarifies pronouns or follow-ups."
        )

    def __len__(self) -> int:
        return len(self._turns)
