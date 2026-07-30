#!/usr/bin/env python3
"""Generate the Daily Dish FAQ PDF from the Markdown source of truth."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SRC = ROOT / "data" / "faqs" / "daily_dish_faq.md"
DEFAULT_OUT = ROOT / "data" / "faqs" / "daily_dish_faq.pdf"


def _plain_lines(markdown: str) -> list[str]:
    """Strip light Markdown formatting for PDF rendering."""
    lines: list[str] = []
    for raw in markdown.splitlines():
        line = raw.rstrip()
        line = re.sub(r"^#+\s*", "", line)
        line = re.sub(r"\*\*(.+?)\*\*", r"\1", line)
        lines.append(line)
    return lines


def generate(src: Path, out: Path) -> Path:
    try:
        from reportlab.lib.pagesizes import LETTER
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
    except ImportError as exc:  # pragma: no cover
        raise SystemExit(
            "reportlab is required. Install with: pip install 'daily-dish-crewai[pdf]'"
        ) from exc

    if not src.is_file():
        raise FileNotFoundError(f"FAQ markdown not found: {src}")

    out.parent.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(
        str(out),
        pagesize=LETTER,
        title="The Daily Dish — FAQ",
        author="The Daily Dish",
    )
    story: list = []
    for line in _plain_lines(src.read_text(encoding="utf-8")):
        if not line.strip():
            story.append(Spacer(1, 8))
            continue
        style = styles["Heading2"] if line.startswith("The Daily Dish") or line.endswith(
            ("Location", "Seating", "Needs", "Specials")
        ) else styles["BodyText"]
        # Escape XML-sensitive characters for reportlab Paragraph
        safe = (
            line.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        story.append(Paragraph(safe, style))
        story.append(Spacer(1, 4))

    doc.build(story)
    return out


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--src", type=Path, default=DEFAULT_SRC)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)
    path = generate(args.src, args.out)
    print(f"Wrote FAQ PDF → {path}")


if __name__ == "__main__":
    main(sys.argv[1:])
