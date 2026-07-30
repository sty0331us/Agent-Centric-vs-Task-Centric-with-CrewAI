"""CLI entrypoint for The Daily Dish chatbot."""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from daily_dish.config import PROJECT_ROOT, Settings, WorkflowMode, get_settings
from daily_dish.crews import build_agent_centric_crew, build_task_centric_crew
from daily_dish.logging_setup import get_logger, setup_logging
from daily_dish.runtime import ensure_local_storage

console = Console()
logger = get_logger(__name__)


def _ensure_api_key() -> None:
    if not os.getenv("OPENAI_API_KEY"):
        console.print(
            Panel(
                "[bold red]OPENAI_API_KEY is not set.[/]\n"
                "Copy [cyan].env.example[/] → [cyan].env[/] and add your key.",
                title="Configuration Error",
                border_style="red",
            )
        )
        sys.exit(1)


def _ensure_faq(settings: Settings) -> None:
    if settings.faq_exists:
        return
    console.print(
        Panel(
            f"[bold red]FAQ PDF missing:[/] {settings.faq_pdf_path}\n"
            "Generate it with:\n"
            "  [cyan]python scripts/generate_faq_pdf.py[/]",
            title="Missing Knowledge Base",
            border_style="red",
        )
    )
    sys.exit(1)


def _crew_result_text(result: Any) -> str:
    if result is None:
        return ""
    if hasattr(result, "raw") and result.raw:
        return str(result.raw).strip()
    return str(result).strip()


def run_once(mode: WorkflowMode, customer_query: str, settings: Settings) -> str:
    """Execute a single turn for the selected workflow mode."""
    inputs = {"customer_query": customer_query}

    if mode is WorkflowMode.AGENT_CENTRIC:
        crew = build_agent_centric_crew(settings)
        return _crew_result_text(crew.kickoff(inputs=inputs))

    if mode is WorkflowMode.TASK_CENTRIC:
        crew = build_task_centric_crew(settings)
        return _crew_result_text(crew.kickoff(inputs=inputs))

    # COMPARE: run both and return a side-by-side summary
    agent_out = _crew_result_text(build_agent_centric_crew(settings).kickoff(inputs=inputs))
    task_out = _crew_result_text(build_task_centric_crew(settings).kickoff(inputs=inputs))

    table = Table(title="Agent-Centric vs Task-Centric", show_lines=True)
    table.add_column("Aspect", style="bold cyan", width=18)
    table.add_column("Agent-Centric", overflow="fold")
    table.add_column("Task-Centric", overflow="fold")
    table.add_row("Final reply", agent_out, task_out)
    table.add_row(
        "Tool binding",
        "Tools on Agent; LLM chooses",
        "Tools on Task; fixed mapping",
    )
    table.add_row(
        "Structure",
        "Search + reply blended",
        "Retrieve → then format",
    )
    console.print(table)
    return task_out


def interactive_loop(mode: WorkflowMode, settings: Settings) -> None:
    """REPL chatbot loop matching the lab UX."""
    mode_label = {
        WorkflowMode.AGENT_CENTRIC: "Agent-Centric",
        WorkflowMode.TASK_CENTRIC: "Task-Centric",
        WorkflowMode.COMPARE: "Compare (both)",
    }[mode]

    console.print(
        Panel(
            f"[bold]Welcome to The Daily Dish Chatbot![/]\n"
            f"Mode: [cyan]{mode_label}[/]\n"
            "What would you like to know? (Type [yellow]exit[/] to quit)",
            title="The Daily Dish",
            border_style="green",
        )
    )

    while True:
        try:
            user_input = console.input("\n[bold]Your question:[/] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\nThank you for chatting. Have a great day!")
            break

        if user_input.lower() == "exit":
            console.print("Thank you for chatting. Have a great day!")
            break
        if not user_input:
            console.print("[yellow]Please type a question.[/]")
            continue

        try:
            result = run_once(mode, user_input, settings)
            if mode is not WorkflowMode.COMPARE:
                console.print(
                    Panel(result, title="The Daily Dish Assistant", border_style="blue")
                )
        except Exception as exc:  # noqa: BLE001 — surface runtime errors to the user
            logger.exception("Crew run failed")
            console.print(f"[bold red]An error occurred:[/] {exc}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="daily-dish",
        description=(
            "The Daily Dish customer-service chatbot — "
            "compare agent-centric vs task-centric CrewAI tool assignment."
        ),
    )
    parser.add_argument(
        "--mode",
        choices=[m.value for m in WorkflowMode],
        default=None,
        help="Workflow strategy (default: DAILY_DISH_DEFAULT_MODE / task_centric)",
    )
    parser.add_argument(
        "--query",
        "-q",
        help="Single question (non-interactive). Omit for the REPL chatbot.",
    )
    parser.add_argument(
        "--enable-web-search",
        action="store_true",
        help="Enable optional web-search tool (requires SERPER_API_KEY).",
    )
    parser.add_argument(
        "--log-level",
        default=None,
        help="Override log level (DEBUG, INFO, WARNING, ERROR).",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    load_dotenv(PROJECT_ROOT / ".env")
    ensure_local_storage()
    args = build_parser().parse_args(argv)

    base = get_settings()
    if args.enable_web_search:
        settings = base.model_copy(update={"enable_web_search": True})
    else:
        settings = base

    level = args.log_level or settings.log_level
    setup_logging(level)

    _ensure_api_key()
    _ensure_faq(settings)

    mode = WorkflowMode(args.mode) if args.mode else settings.default_mode
    logger.info("Starting Daily Dish chatbot in mode=%s", mode.value)

    if args.query:
        result = run_once(mode, args.query, settings)
        if mode is not WorkflowMode.COMPARE:
            console.print(Panel(result, title="The Daily Dish Assistant", border_style="blue"))
        return

    interactive_loop(mode, settings)


if __name__ == "__main__":
    main()
