from __future__ import annotations

from rich.console import Console

from invoice_agent.ui.renderer import ChatState, build_layout


def test_chat_layout_renders_core_sections():
    state = ChatState(
        status="Ready",
        db_name="data.db",
        pdf_count=12,
        messages=[
            ("assistant", "I'm ready."),
            ("user", "Show unpaid invoices."),
            ("assistant", "I found 3 invoices."),
        ],
        input_buffer="Ask anything about your invoices...",
    )

    console = Console(width=100, height=30, record=True, force_terminal=True)
    layout = build_layout(state, console=console)
    console.print(layout)

    output = console.export_text()

    assert "Invoice Agent" in output
    assert "Database : data.db" in output
    assert "Show unpaid invoices." in output
    assert "Ask anything about your invoices..." in output