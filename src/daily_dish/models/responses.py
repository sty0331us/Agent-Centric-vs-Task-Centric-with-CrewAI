"""Structured response models for crew outputs."""

from __future__ import annotations

from pydantic import BaseModel, Field


class FaqSearchResult(BaseModel):
    """Intermediate result from an FAQ retrieval task."""

    query: str = Field(description="Original customer query")
    findings: str = Field(description="Relevant FAQ excerpts or synthesized facts")
    source: str = Field(default="faq_pdf", description="Retrieval source identifier")


class CustomerReply(BaseModel):
    """Final customer-facing reply."""

    reply: str = Field(description="Friendly, comprehensive answer for the customer")
    confidence: str = Field(
        default="high",
        description="Agent confidence: high | medium | low | unknown",
    )
