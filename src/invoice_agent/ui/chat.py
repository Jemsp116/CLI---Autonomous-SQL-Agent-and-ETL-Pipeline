from __future__ import annotations

import os
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING

from rich.console import Console
from rich.live import Live

from invoice_agent.agent.react_agent import ask as ask_question
from invoice_agent.config import get_settings

from .renderer import ChatState, build_layout

if TYPE_CHECKING:
    from collections.abc import Callable


WELCOME_MESSAGE = "I'm ready.\n\nAsk me anything about your invoices."


def _count_pdfs(folder: Path) -> int:
    if not folder.exists():
        return 0
    return sum(1 for entry in folder.iterdir() if entry.is_file() and entry.suffix.lower() == ".pdf")


def _get_key() -> str:
    if os.name != "nt":
        return os.read(0, 1).decode("utf-8", errors="ignore")

    import msvcrt

    key = msvcrt.getwch()
    if key in {"\x00", "\xe0"}:
        special = msvcrt.getwch()
        return {
            "H": "UP",
            "P": "DOWN",
            "K": "LEFT",
            "M": "RIGHT",
            "S": "DELETE",
        }.get(special, special)
    return key


def _question_history_handler(key: str, buffer: str, history: list[str], history_index: int) -> tuple[str, int]:
    if key == "UP" and history:
        history_index = max(0, history_index - 1)
        return history[history_index], history_index
    if key == "DOWN" and history:
        if history_index < len(history) - 1:
            history_index += 1
            return history[history_index], history_index
        return "", len(history)
    return buffer, history_index


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

    state = ChatState(
        db_name=resolved_db_path.name,
        pdf_count=_count_pdfs(Path(settings.invoice_output_dir)),
        messages=[("assistant", WELCOME_MESSAGE)],
    )
    history: list[str] = []
    history_index = 0
    lock = threading.Lock()

    def refresh(live: Live) -> None:
        live.update(build_layout(state, console=resolved_console), refresh=True)

    def submit_question(question: str, live: Live) -> None:
        nonlocal history_index

        question = question.strip()
        if not question:
            return

        state.messages.append(("user", question))
        state.input_buffer = question
        state.locked = True
        state.thinking = True
        state.draft_assistant = ""
        state.status = "Thinking"
        refresh(live)

        answer_holder: dict[str, str] = {"answer": ""}
        error_holder: dict[str, BaseException | None] = {"error": None}
        finished = threading.Event()

        def on_thinking() -> None:
            with lock:
                state.thinking = True
                state.status = "Thinking"

        def on_token(token: str) -> None:
            with lock:
                state.thinking = False
                state.status = "Streaming"
                state.draft_assistant += token

        def worker() -> None:
            try:
                answer_holder["answer"] = ask_question(
                    question=question,
                    db_path=resolved_db_path,
                    on_thinking=on_thinking,
                    on_token=on_token,
                )
            except BaseException as exc:  # noqa: BLE001
                error_holder["error"] = exc
            finally:
                finished.set()

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

        while not finished.is_set():
            with lock:
                refresh(live)
            time.sleep(0.08)

        thread.join()

        error = error_holder["error"]
        if error is not None:
            message = str(error) or error.__class__.__name__
            with lock:
                state.messages.append(("assistant", f"Error: {message}"))
                state.thinking = False
                state.draft_assistant = ""
                state.locked = False
                state.status = "Ready"
                state.input_buffer = ""
                refresh(live)
            if isinstance(error, SystemExit):
                raise error
            return

        with lock:
            state.messages.append(("assistant", answer_holder["answer"]))
            history.append(question)
            history_index = len(history)
            state.thinking = False
            state.draft_assistant = ""
            state.locked = False
            state.status = "Ready"
            state.input_buffer = ""
            refresh(live)

    try:
        with Live(build_layout(state, console=resolved_console), console=resolved_console, screen=True, refresh_per_second=12) as live:
            refresh(live)

            if initial_question:
                submit_question(initial_question, live)

            buffer = ""
            while True:
                with lock:
                    state.input_buffer = buffer
                    state.locked = False
                    state.thinking = False
                    state.status = "Ready"
                    refresh(live)

                key = _get_key()
                if key == "\x03":
                    raise KeyboardInterrupt
                if key in {"\r", "\n"}:
                    question = buffer.strip()
                    if not question:
                        buffer = ""
                        continue
                    submit_question(question, live)
                    buffer = ""
                    continue
                if key == "\x08":
                    buffer = buffer[:-1]
                elif key in {"UP", "DOWN"}:
                    buffer, history_index = _question_history_handler(key, buffer, history, history_index)
                elif len(key) == 1 and key.isprintable():
                    buffer += key

                with lock:
                    state.input_buffer = buffer
                    refresh(live)
    except KeyboardInterrupt:
        resolved_console.print("\n[dim]Goodbye.[/dim]")