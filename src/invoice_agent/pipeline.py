from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from invoice_agent import generate
from invoice_agent.ask import run as ask_run
from invoice_agent.config import get_settings
from invoice_agent.extract import headers, tables
from invoice_agent.load import run as load_run
from invoice_agent.status import run as status_run

console = Console()


def run(
    count: int | None = None,
    out_dir: str | Path | None = None,
    zip_path: str | Path | None = None,
    csv_dir: str | Path | None = None,
    db_path: str | Path | None = None,
    question: str | None = None,
    enable_llm_fallback: bool = True,
) -> None:
    settings = get_settings()
    resolved_out_dir = Path(out_dir or settings.invoice_output_dir)
    resolved_zip_path = Path(zip_path or settings.invoice_zip_path)
    resolved_csv_dir = Path(csv_dir or settings.headers_output_csv.parent)
    resolved_db_path = Path(db_path or settings.demo_db_path)
    resolved_count = count or (settings.invoice_end_no - settings.invoice_start_no)
    resolved_spot_checks = tuple()

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), TimeElapsedColumn(), console=console) as progress:
        task = progress.add_task("Generating invoices", total=None)
        generate.run(
            out_dir=resolved_out_dir,
            zip_path=resolved_zip_path,
            start_invoice_no=settings.invoice_start_no,
            end_invoice_no=settings.invoice_start_no + resolved_count,
            spot_check_invoice_nos=resolved_spot_checks,
        )
        progress.update(task, completed=1)

        task = progress.add_task("Extracting headers", total=None)
        headers.run(
            pdf_dir=resolved_out_dir,
            output_csv=resolved_csv_dir / "invoice_headers.csv",
            report_json=resolved_csv_dir / "invoice_headers_report.json",
            enable_llm_fallback=enable_llm_fallback,
        )
        progress.update(task, completed=1)

        task = progress.add_task("Extracting tables", total=None)
        tables.run(
            pdf_dir=resolved_out_dir,
            line_items_csv=resolved_csv_dir / "invoice_line_items.csv",
            summaries_csv=resolved_csv_dir / "invoice_summaries.csv",
            report_json=resolved_csv_dir / "invoice_tables_report.json",
            enable_llm_fallback=enable_llm_fallback,
        )
        progress.update(task, completed=1)

        task = progress.add_task("Loading database", total=None)
        load_run(csv_dir=resolved_csv_dir, db_path=resolved_db_path)
        progress.update(task, completed=1)

    if question:
        ask_run(question=question, db_path=resolved_db_path)

    status_run(csv_dir=resolved_csv_dir, db_path=resolved_db_path, invoices_dir=resolved_out_dir)


def main() -> None:
    run()


if __name__ == "__main__":
    main()
