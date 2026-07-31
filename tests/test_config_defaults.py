from __future__ import annotations

from invoice_agent.config import Settings


def test_default_agent_model_uses_supported_openrouter_slug():
    assert Settings().agent_model == "openai/gpt-oss-120b"