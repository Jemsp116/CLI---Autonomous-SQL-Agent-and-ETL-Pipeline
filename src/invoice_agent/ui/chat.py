from __future__ import annotations

from pathlib import Path

from rich.console import Console

from invoice_agent.config import get_settings


def run(
    initial_question: str | None = None,
    db_path: str | Path | None = None,
    *,
    console: Console | None = None,
) -> None:
    resolved_console = console or Console()
    settings = get_settings()
    resolved_db_path = Path(db_path or settings.demo_db_path)

    if not resolved_db_path.exists():
        raise SystemExit(f"Database not found: {resolved_db_path}")

    resolved_console.print("[bold]Invoice Agent[/bold]")
    resolved_console.print(f"[dim]Database:[/dim] {resolved_db_path.name}")
    resolved_console.print("[dim]Type 'exit' or press Ctrl+C to quit.[/dim]\n")

    def submit_question(question: str) -> None:
        question = question.strip()
        if not question:
            return

        try:
            from invoice_agent.ask import run as ask_question

            answer = ask_question(question=question, db_path=resolved_db_path)
        except Exception as exc:  # noqa: BLE001
            resolved_console.print(f"[red]Error:[/red] {exc}")
            return

        if answer:
            resolved_console.print(f"[bold green]Assistant:[/bold green] {answer}")

    try:
        if initial_question:
            resolved_console.print(f"[bold cyan]You:[/bold cyan] {initial_question}")
            submit_question(initial_question)

        while True:
            try:
                question = resolved_console.input("[bold cyan]You[/bold cyan]: ").strip()
            except (EOFError, KeyboardInterrupt):
                raise KeyboardInterrupt

            if not question:
                continue
            if question.lower() in {"exit", "quit", "q"}:
                break

            resolved_console.print(f"[bold cyan]You:[/bold cyan] {question}")
            submit_question(question)
    except KeyboardInterrupt:
        resolved_console.print("\n[dim]Goodbye.[/dim]")