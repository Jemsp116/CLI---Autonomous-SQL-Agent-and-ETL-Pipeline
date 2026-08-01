from __future__ import annotations

from pathlib import Path

from rich.console import Console

from invoice_agent.agent.react_agent import ask
from invoice_agent.ui.chat import run as run_chat


def run(question: str, db_path: str | Path | None = None) -> str:
    try:
        return ask(question=question, db_path=db_path)
    except ValueError as exc:
        if str(exc) == "OPENROUTER_API_KEY environment variable is not set.":
            raise SystemExit(str(exc)) from exc
        raise


def run_interactive(
    initial_question: str | None = None,
    db_path: str | Path | None = None,
    *,
    console: Console | None = None,
) -> None:
    run_chat(initial_question=initial_question, db_path=db_path, console=console)


def main() -> None:
    raise SystemExit("Use invoice-agent ask <question> from the CLI.")


if __name__ == "__main__":
    main()
