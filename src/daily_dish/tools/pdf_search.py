"""Local FAQ PDF retrieval tool."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from crewai.tools import BaseTool
from pydantic import BaseModel, Field, PrivateAttr
from pypdf import PdfReader


class PdfSearchInput(BaseModel):
    """Schema for FAQ PDF keyword search."""

    query: str = Field(..., description="Search terms related to the customer question")


class LocalPdfSearchTool(BaseTool):
    """
    Lightweight, dependency-stable PDF search for production demos.

    Extracts text from a local FAQ PDF and returns the most relevant chunks
    by simple term overlap. Avoids remote embedding services so the lab
    remains reproducible offline once the PDF exists.
    """

    name: str = "Search a PDF's content"
    description: str = (
        "Search the restaurant FAQ PDF for answers related to hours, location, "
        "reservations, menu, dietary needs, payments, and policies."
    )
    args_schema: type[BaseModel] = PdfSearchInput

    _pdf_path: Path = PrivateAttr()
    _pages: list[str] = PrivateAttr(default_factory=list)

    def __init__(self, pdf_path: Path | str, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._pdf_path = Path(pdf_path)
        if not self._pdf_path.is_file():
            raise FileNotFoundError(
                f"FAQ PDF not found at {self._pdf_path}. "
                "Run: python scripts/generate_faq_pdf.py"
            )
        self._pages = self._load_pages()

    def _load_pages(self) -> list[str]:
        reader = PdfReader(str(self._pdf_path))
        pages: list[str] = []
        for page in reader.pages:
            text = page.extract_text() or ""
            cleaned = " ".join(text.split())
            if cleaned:
                pages.append(cleaned)
        if not pages:
            raise ValueError(f"No extractable text found in {self._pdf_path}")
        return pages

    def _run(self, query: str) -> str:
        terms = [t.lower() for t in query.split() if len(t) > 2]
        if not terms:
            return "No usable search terms provided."

        scored: list[tuple[int, str]] = []
        for page in self._pages:
            lower = page.lower()
            score = sum(lower.count(term) for term in terms)
            if score > 0:
                scored.append((score, page))

        if not scored:
            # Fallback: return a truncated corpus so the LLM still has context
            joined = " ".join(self._pages)
            return f"Relevant Content:\n{joined[:1800]}"

        scored.sort(key=lambda item: item[0], reverse=True)
        top = scored[0][1]
        return f"Relevant Content:\n{top[:2500]}"


def build_pdf_search_tool(pdf_path: Path | str) -> LocalPdfSearchTool:
    """Construct the FAQ PDF search tool for a given path."""
    return LocalPdfSearchTool(pdf_path=pdf_path)
