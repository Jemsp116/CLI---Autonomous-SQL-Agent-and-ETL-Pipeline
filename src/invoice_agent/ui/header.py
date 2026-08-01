from __future__ import annotations

from rich import box
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


def render_header(status: str, db_name: str, pdf_count: int) -> Panel:
    status_style = "green" if status.lower() == "ready" else "yellow"

    grid = Table.grid(expand=True, padding=(0, 1))
    grid.add_column(ratio=1)
    grid.add_column(justify="right")
    grid.add_row(Text("Invoice Agent", style="bold"), Text(f"{status} ●", style=status_style))
    grid.add_row(Text(f"Database : {db_name}", style="dim"), Text(f"PDFs     : {pdf_count}", style="dim"))

    return Panel(grid, box=box.ROUNDED, padding=(0, 1), expand=True)