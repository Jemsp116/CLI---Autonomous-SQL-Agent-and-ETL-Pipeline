from __future__ import annotations

from rich import box
from rich.console import Group
from rich.panel import Panel
from rich.padding import Padding
from rich.text import Text

EXAMPLE_PROMPTS = (
    "Show unpaid invoices",
    "Total GST this month",
    "Highest value invoice",
    "Vendor summary",
)


def render_input_box(
    buffer: str,
    *,
    focused: bool,
    locked: bool,
    placeholder: str = "Ask anything about your invoices...",
) -> Panel:
    if not buffer and not locked:
        examples = Text()
        examples.append("\n")
        for example in EXAMPLE_PROMPTS:
            examples.append(f"• {example}\n", style="dim")

        body = Group(
            Text(placeholder, style="dim"),
            Padding(examples, (0, 0, 0, 0)),
        )
    else:
        line = Text()
        if focused and not locked:
            line.append("> ", style="cyan")
            line.append(buffer, style="white")
            line.append("█", style="bold cyan")
        else:
            line.append(buffer or "Thinking...", style="dim")
        body = line

    return Panel(body, box=box.ROUNDED, padding=(0, 1), expand=True)