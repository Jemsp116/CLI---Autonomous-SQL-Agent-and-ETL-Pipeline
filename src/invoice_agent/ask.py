from __future__ import annotations

from pathlib import Path

from rich.console import Console

from invoice_agent.agent.react_agent import ask


def run(question: str, db_path: str | Path | None = None) -> str:
    try:
        return ask(question=question, db_path=db_path)
    except ValueError as exc:
        if str(exc) == "OPENROUTER_API_KEY environment variable is not set.":
            raise SystemExit(str(exc)) from exc
        raise


def run_interactive(
    db_path: str | Path | None = None,
    *,
    console: Console | None = None,
) -> None:
    resolved_console = console or Console()
    resolved_db_path = Path(db_path) if db_path else None

    resolved_console.print("\n[bold]Ask a question about your invoices (or type 'exit' to quit):[/bold]")

    while True:
        try:
            question = resolved_console.input("[cyan]question> [/cyan]")
        except KeyboardInterrupt:
            resolved_console.print("\n[green]Goodbye![/green]")
            return

        question = question.strip()
        if not question:
            continue
        if question.lower() in ("exit", "quit"):
            resolved_console.print("[green]Goodbye![/green]")
            return

        try:
            answer = run(question=question, db_path=resolved_db_path)
            resolved_console.print(answer)
        except SystemExit as exc:
            resolved_console.print(f"[red]Error:[/red] {exc}")
            return
        except Exception as exc:
            resolved_console.print(f"[red]Error:[/red] {exc}")


def main() -> None:
    raise SystemExit("Use invoice-agent ask <question> from the CLI.")


if __name__ == "__main__":
    main()
