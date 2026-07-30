"""Local FAQ PDF retrieval tool."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from crewai.tools import BaseTool
from pydantic import BaseModel, Field, PrivateAttr
from pypdf import PdfReader

# Expand casual customer phrasing into FAQ vocabulary before scoring.
QUERY_SYNONYMS: dict[str, tuple[str, ...]] = {
    "timings": ("hours", "operation", "open"),
    "timing": ("hours", "operation", "open"),
    "time": ("hours", "operation"),
    "when": ("hours", "open"),
    "where": ("located", "location", "address"),
    "address": ("located", "location"),
    "phone": ("number", "call", "reach"),
    "reserve": ("reservation", "book", "table"),
    "booking": ("reservation", "book", "table"),
    "park": ("parking", "valet"),
    "vegan": ("vegetarian", "dietary"),
    "allergy": ("allergies", "allergen"),
    "kids": ("children", "kids'"),
    "pay": ("payment", "cards", "cash"),
    "happy": ("happy hour", "drinks"),
    "dress": ("dress code", "casual"),
}


class PdfSearchInput(BaseModel):
    """Schema for FAQ PDF keyword search."""

    query: str = Field(..., description="Search terms related to the customer question")


def expand_query_terms(query: str) -> list[str]:
    """Tokenize a query and expand known synonyms for better FAQ recall."""
    raw = [t.lower() for t in re.findall(r"[a-zA-Z0-9']+", query) if len(t) > 2]
    terms: list[str] = []
    seen: set[str] = set()
    for token in raw:
        candidates = (token, *QUERY_SYNONYMS.get(token, ()))
        for candidate in candidates:
            key = candidate.lower()
            if key not in seen:
                seen.add(key)
                terms.append(key)
    return terms


def split_faq_chunks(text: str) -> list[str]:
    """
    Split FAQ corpus into Q&A-sized chunks.

    Prefers numbered FAQ entries; falls back to paragraph splits.
    """
    numbered = re.split(r"(?=\b\d+\.\s)", text)
    chunks = [c.strip() for c in numbered if len(c.strip()) > 40]
    if len(chunks) >= 2:
        return chunks

    paragraphs = [p.strip() for p in re.split(r"\n{2,}|\s{2,}", text) if len(p.strip()) > 40]
    return paragraphs or [text]


class LocalPdfSearchTool(BaseTool):
    """
    Lightweight, dependency-stable PDF search for production demos.

    Extracts text from a local FAQ PDF, chunks it into FAQ entries, expands
    query synonyms, and returns the top overlapping chunks. Avoids remote
    embedding services so the lab remains reproducible offline.
    """

    name: str = "Search a PDF's content"
    description: str = (
        "Search the restaurant FAQ PDF for answers related to hours, location, "
        "reservations, menu, dietary needs, payments, and policies."
    )
    args_schema: type[BaseModel] = PdfSearchInput

    _pdf_path: Path = PrivateAttr()
    _chunks: list[str] = PrivateAttr(default_factory=list)

    def __init__(self, pdf_path: Path | str, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._pdf_path = Path(pdf_path)
        if not self._pdf_path.is_file():
            raise FileNotFoundError(
                f"FAQ PDF not found at {self._pdf_path}. "
                "Run: python scripts/generate_faq_pdf.py"
            )
        self._chunks = self._load_chunks()

    def _load_chunks(self) -> list[str]:
        reader = PdfReader(str(self._pdf_path))
        pages: list[str] = []
        for page in reader.pages:
            text = page.extract_text() or ""
            cleaned = " ".join(text.split())
            if cleaned:
                pages.append(cleaned)
        if not pages:
            raise ValueError(f"No extractable text found in {self._pdf_path}")
        return split_faq_chunks(" ".join(pages))

    def _run(self, query: str) -> str:
        terms = expand_query_terms(query)
        if not terms:
            return "No usable search terms provided."

        scored: list[tuple[int, str]] = []
        for chunk in self._chunks:
            lower = chunk.lower()
            score = sum(lower.count(term) for term in terms)
            if score > 0:
                scored.append((score, chunk))

        if not scored:
            joined = " ".join(self._chunks)
            return f"Relevant Content:\n{joined[:1800]}"

        scored.sort(key=lambda item: item[0], reverse=True)
        top_chunks = [chunk for _, chunk in scored[:3]]
        return "Relevant Content:\n" + "\n\n".join(top_chunks)[:3000]


def build_pdf_search_tool(pdf_path: Path | str) -> LocalPdfSearchTool:
    """Construct the FAQ PDF search tool for a given path."""
    return LocalPdfSearchTool(pdf_path=pdf_path)
