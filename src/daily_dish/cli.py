"""CLI entrypoint for The Daily Dish chatbot."""

from __future__ import annotations

import argparse
import json
import os
import sys

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from daily_dish.config import PROJECT_ROOT, Settings, WorkflowMode, get_settings
from daily_dish.doctor import doctor_passed, run_doctor
from daily_dish.logging_setup import get_logger, setup_logging
from daily_dish.memory import ConversationMemory
from daily_dish.runtime import ensure_local_storage
from daily_dish.services import ChatService
from daily_dish.services.chat import TurnResult
from daily_dish.validation import sanitize_query

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


def _print_compare(_mode: WorkflowMode, turn: TurnResult) -> None:
    table = Table(title="Agent-Centric vs Task-Centric", show_lines=True)
    table.add_column("Aspect", style="bold cyan", width=18)
    table.add_column("Agent-Centric", overflow="fold")
    table.add_column("Task-Centric", overflow="fold")
    table.add_row("Final reply", turn.agent_centric_reply or "", turn.task_centric_reply or "")
    table.add_row(
        "Latency",
        f"{(turn.agent_centric_latency_ms or 0):.0f} ms",
        f"{(turn.task_centric_latency_ms or 0):.0f} ms",
    )
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


def run_doctor_command(settings: Settings) -> int:
    """Print preflight diagnostics and return a process exit code."""
    checks = run_doctor(settings)
    table = Table(title="Daily Dish Doctor", show_lines=True)
    table.add_column("Check", style="bold")
    table.add_column("Status")
    table.add_column("Detail", overflow="fold")
    for check in checks:
        status = "[green]OK[/]" if check.ok else "[red]FAIL[/]"
        table.add_row(check.name, status, check.detail)
    console.print(table)
    return 0 if doctor_passed(checks) else 1


def run_once(
    mode: WorkflowMode,
    customer_query: str,
    settings: Settings,
    *,
    render_compare: bool = True,
) -> TurnResult:
    """Execute a single turn for the selected workflow mode."""
    turn = ChatService(settings).ask(mode, customer_query)
    if mode is WorkflowMode.COMPARE and render_compare:
        _print_compare(mode, turn)
    return turn


def interactive_loop(mode: WorkflowMode, settings: Settings) -> None:
    """REPL chatbot loop matching the lab UX."""
    mode_label = {
        WorkflowMode.AGENT_CENTRIC: "Agent-Centric",
        WorkflowMode.TASK_CENTRIC: "Task-Centric",
        WorkflowMode.COMPARE: "Compare (both)",
    }[mode]
    service = ChatService(settings)
    memory = ConversationMemory(max_turns=settings.memory_turns)

    console.print(
        Panel(
            f"[bold]Welcome to The Daily Dish Chatbot![/]\n"
            f"Mode: [cyan]{mode_label}[/]\n"
            "What would you like to know? (Type [yellow]exit[/] to quit, "
            "[yellow]reset[/] to clear memory)",
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

        lowered = user_input.lower()
        if lowered == "exit":
            console.print("Thank you for chatting. Have a great day!")
            break
        if lowered == "reset":
            memory.clear()
            console.print("[cyan]Conversation memory cleared.[/]")
            continue

        validated = sanitize_query(user_input, max_chars=settings.max_query_chars)
        if not validated.ok:
            console.print(f"[yellow]{validated.error}[/]")
            continue

        try:
            enriched = memory.enrich_query(validated.query)
            turn = service.ask(mode, enriched)
            if mode is WorkflowMode.COMPARE:
                _print_compare(mode, turn)
            else:
                console.print(
                    Panel(
                        f"{turn.reply}\n\n[dim]{turn.latency_ms:.0f} ms[/]",
                        title="The Daily Dish Assistant",
                        border_style="blue",
                    )
                )
            memory.add(validated.query, turn.reply)
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
        "--doctor",
        action="store_true",
        help="Run preflight diagnostics (API key, FAQ, packages, storage) and exit.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON for single-query runs (implies -q).",
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

    if args.doctor:
        code = run_doctor_command(settings)
        raise SystemExit(code)

    _ensure_api_key()
    _ensure_faq(settings)

    mode = WorkflowMode(args.mode) if args.mode else settings.default_mode
    logger.info("Starting Daily Dish chatbot in mode=%s", mode.value)

    if args.json and not args.query:
        console.print("[bold red]--json requires --query / -q[/]")
        raise SystemExit(2)

    if args.query:
        validated = sanitize_query(args.query, max_chars=settings.max_query_chars)
        if not validated.ok:
            if args.json:
                print(json.dumps({"ok": False, "error": validated.error}))
            else:
                console.print(f"[bold red]{validated.error}[/]")
            raise SystemExit(2)
        turn = run_once(mode, validated.query, settings, render_compare=not args.json)
        if args.json:
            # Avoid double-printing the Rich compare table noise for JSON consumers
            print(json.dumps({"ok": True, **turn.to_dict()}, ensure_ascii=False, indent=2))
            return
        if mode is not WorkflowMode.COMPARE:
            console.print(
                Panel(
                    f"{turn.reply}\n\n[dim]{turn.latency_ms:.0f} ms[/]",
                    title="The Daily Dish Assistant",
                    border_style="blue",
                )
            )
        return

    interactive_loop(mode, settings)


if __name__ == "__main__":
    main()
