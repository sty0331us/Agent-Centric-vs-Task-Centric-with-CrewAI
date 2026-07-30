"""Structured logging setup for CLI and crew runs."""

from __future__ import annotations

import logging

from rich.logging import RichHandler

from daily_dish.config import PROJECT_ROOT


def setup_logging(level: str = "INFO") -> None:
    """Configure root logging with Rich console output and a rotating file sink."""
    log_dir = PROJECT_ROOT / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "daily_dish.log"

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level.upper())

    console = RichHandler(
        rich_tracebacks=True,
        markup=True,
        show_path=False,
        omit_repeated_times=False,
    )
    console.setLevel(level.upper())
    console.setFormatter(logging.Formatter("%(message)s"))

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

    root.addHandler(console)
    root.addHandler(file_handler)

    # Quiet noisy third-party loggers in production-ish runs
    for noisy in ("httpx", "httpcore", "openai", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger."""
    return logging.getLogger(name)
