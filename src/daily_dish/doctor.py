"""Preflight diagnostics for production readiness checks."""

from __future__ import annotations

import importlib.metadata
import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from daily_dish.config import PROJECT_ROOT, Settings


@dataclass(slots=True)
class CheckResult:
    """One diagnostic check outcome."""

    name: str
    ok: bool
    detail: str


def run_doctor(settings: Settings) -> list[CheckResult]:
    """Collect environment, dependency, and knowledge-base health checks."""
    checks: list[CheckResult] = []

    api_key = os.getenv("OPENAI_API_KEY", "")
    checks.append(
        CheckResult(
            name="OPENAI_API_KEY",
            ok=bool(api_key.strip()),
            detail="set" if api_key.strip() else "missing — copy .env.example to .env",
        )
    )

    checks.append(
        CheckResult(
            name="FAQ PDF",
            ok=settings.faq_exists,
            detail=str(settings.faq_pdf_path)
            if settings.faq_exists
            else f"missing at {settings.faq_pdf_path}",
        )
    )

    faq_md = PROJECT_ROOT / "data" / "faqs" / "daily_dish_faq.md"
    checks.append(
        CheckResult(
            name="FAQ Markdown",
            ok=faq_md.is_file(),
            detail=str(faq_md) if faq_md.is_file() else f"missing at {faq_md}",
        )
    )

    for package in ("crewai", "pydantic", "pypdf", "rich"):
        try:
            version = importlib.metadata.version(package)
            checks.append(CheckResult(name=f"package:{package}", ok=True, detail=version))
        except importlib.metadata.PackageNotFoundError:
            checks.append(CheckResult(name=f"package:{package}", ok=False, detail="not installed"))

    storage = PROJECT_ROOT / "storage"
    try:
        storage.mkdir(parents=True, exist_ok=True)
        probe = storage / ".doctor_write_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        writable = True
        detail = str(storage)
    except OSError as exc:
        writable = False
        detail = str(exc)
    checks.append(CheckResult(name="storage writable", ok=writable, detail=detail))

    python = shutil.which("python3") or shutil.which("python") or "unknown"
    checks.append(
        CheckResult(
            name="python",
            ok=True,
            detail=python,
        )
    )

    model = settings.openai_model_name
    checks.append(CheckResult(name="model", ok=bool(model), detail=model or "unset"))

    env_file = PROJECT_ROOT / ".env"
    checks.append(
        CheckResult(
            name=".env file",
            ok=env_file.is_file(),
            detail=str(env_file) if env_file.is_file() else "optional but recommended",
        )
    )

    # Path existence helper for operators
    _ = Path
    return checks


def doctor_passed(checks: list[CheckResult]) -> bool:
    """Return True when all required checks pass (.env presence is optional)."""
    optional = {".env file"}
    return all(check.ok for check in checks if check.name not in optional)
