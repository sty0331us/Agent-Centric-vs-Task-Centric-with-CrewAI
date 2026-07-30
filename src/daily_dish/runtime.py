"""Runtime bootstrap — local storage, env loading, fail-fast checks."""

from __future__ import annotations

from pathlib import Path

from daily_dish.config import PROJECT_ROOT


def ensure_local_storage(root: Path | None = None) -> Path:
    """
    Force CrewAI SQLite / app data into the project tree.

    CrewAI normally writes under the user data directory via appdirs.
    For reproducible demos and CI, we keep artifacts under ./storage
    (or under ``root / storage`` when a custom root is provided).
    """
    base = (root or PROJECT_ROOT) / "storage"
    base.mkdir(parents=True, exist_ok=True)

    def _path() -> str:
        return str(base)

    # Patch both the source module and common early-bound importers.
    targets = (
        "crewai_core.paths",
        "crewai.memory.storage.kickoff_task_outputs_storage",
    )
    for module_name in targets:
        try:
            module = __import__(module_name, fromlist=["db_storage_path"])
            if hasattr(module, "db_storage_path"):
                module.db_storage_path = _path
        except Exception:  # pragma: no cover - optional if import graph changes
            continue

    return base
