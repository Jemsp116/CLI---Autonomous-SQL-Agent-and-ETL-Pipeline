from __future__ import annotations

from dataclasses import dataclass, field

from rich.console import Console
from rich.layout import Layout

from .conversation import render_conversation
from .header import render_header
from .input_box import render_input_box


@dataclass
class ChatState:
    status: str = "Ready"
    db_name: str = "invoice_data.db"
    pdf_count: int = 0
    messages: list[tuple[str, str]] = field(default_factory=list)
    draft_assistant: str = ""
    input_buffer: str = ""
    locked: bool = False
    thinking: bool = False


def build_layout(state: ChatState, *, console: Console) -> Layout:
    layout = Layout(name="root")
    layout.split_column(
        Layout(name="header", size=4),
        Layout(name="conversation", ratio=1),
        Layout(name="input", size=6),
    )

    layout["header"].update(render_header(state.status, state.db_name, state.pdf_count))

    available_height = max(5, console.size.height - 10)
    layout["conversation"].update(
        render_conversation(
            state.messages,
            console.size.width,
            available_height,
            thinking=state.thinking,
            draft_assistant=state.draft_assistant,
        )
    )
    layout["input"].update(
        render_input_box(
            state.input_buffer,
            focused=not state.locked,
            locked=state.locked,
        )
    )

    return layout