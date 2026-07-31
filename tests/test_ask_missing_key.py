from __future__ import annotations

import sqlite3

import pytest

from invoice_agent.ask import run as ask_run
from invoice_agent.agent import react_agent
from invoice_agent.config import Settings


def test_ask_exits_cleanly_when_openrouter_key_missing(tmp_path, monkeypatch):
    db_path = tmp_path / "invoices.db"
    with sqlite3.connect(db_path):
        pass

    monkeypatch.setattr(
        react_agent,
        "get_settings",
        lambda: Settings(openrouter_api_key=None, agent_model="openai/gpt-oss-120b"),
    )

    with pytest.raises(SystemExit, match="OPENROUTER_API_KEY environment variable is not set."):
        ask_run(question="which client has the highest total spend?", db_path=db_path)