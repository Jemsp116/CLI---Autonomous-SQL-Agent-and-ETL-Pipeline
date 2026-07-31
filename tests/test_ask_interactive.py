from __future__ import annotations

from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from rich.console import Console

from invoice_agent.ask import run_interactive
from invoice_agent.folder_pipeline import run as folder_pipeline_run
from invoice_agent.preflight import ApiKeyResult

FIXTURES = Path(__file__).parent / "fixtures"


def test_run_interactive_exit():
    console = Console(file=StringIO(), force_terminal=False)
    console.input = MagicMock(side_effect=["exit"])

    run_interactive(db_path=FIXTURES, console=console)

    output = console.file.getvalue()
    assert "Goodbye!" in output


def test_run_interactive_quit():
    console = Console(file=StringIO(), force_terminal=False)
    console.input = MagicMock(side_effect=["quit"])

    run_interactive(db_path=FIXTURES, console=console)

    output = console.file.getvalue()
    assert "Goodbye!" in output


def test_run_interactive_keyboard_interrupt():
    console = Console(file=StringIO(), force_terminal=False)
    console.input = MagicMock(side_effect=KeyboardInterrupt)

    run_interactive(db_path=FIXTURES, console=console)

    output = console.file.getvalue()
    assert "Goodbye!" in output
    assert "Traceback" not in output


def test_run_interactive_ask_question():
    console = Console(file=StringIO(), force_terminal=False)
    console.input = MagicMock(side_effect=["hello", "exit"])

    with patch("invoice_agent.ask.run", return_value="mocked answer") as mock_run:
        run_interactive(db_path=FIXTURES, console=console)
        mock_run.assert_called_once_with(question="hello", db_path=FIXTURES)

    output = console.file.getvalue()
    assert "mocked answer" in output
    assert "Goodbye!" in output


def test_folder_pipeline_calls_qa_when_succeeded(tmp_path):
    with patch("invoice_agent.folder_pipeline.find_ghostscript", return_value="gs"), \
         patch("invoice_agent.folder_pipeline.ensure_openrouter_api_key", return_value=ApiKeyResult(key_found=True, persisted=True)), \
         patch("invoice_agent.folder_pipeline.run_interactive") as mock_qa:
        out_dir = tmp_path / "output"
        result = folder_pipeline_run(
            pdf_folder=FIXTURES,
            out_dir=out_dir,
        )
        assert result.succeeded == 3
        mock_qa.assert_called_once()


def test_folder_pipeline_hint_printed(tmp_path):
    with patch("invoice_agent.folder_pipeline.find_ghostscript", return_value="gs"), \
         patch("invoice_agent.folder_pipeline.ensure_openrouter_api_key", return_value=ApiKeyResult(key_found=True, persisted=True)), \
         patch("invoice_agent.folder_pipeline.run_interactive"):
        out_dir = tmp_path / "output"
        console = Console(file=StringIO(), force_terminal=False)
        result = folder_pipeline_run(
            pdf_folder=FIXTURES,
            out_dir=out_dir,
            console=console,
        )
        output = console.file.getvalue()
        assert "Want to run steps individually? See: invoice-agent --help" in output
        assert result.succeeded == 3
