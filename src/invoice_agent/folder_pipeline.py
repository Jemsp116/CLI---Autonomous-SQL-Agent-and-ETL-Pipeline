from __future__ import annotations

from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TextColumn, TimeElapsedColumn
from rich.table import Table

from invoice_agent.ask import run_interactive
from invoice_agent.db.loader import run as load_run
from invoice_agent.extract.headers import run as headers_run
from invoice_agent.extract.tables import run as tables_run
from invoice_agent.preflight import ensure_openrouter_api_key


@dataclass(frozen=True)
class FolderRunResult:
    total_files: int
    succeeded: int
    failed: list[dict[str, str]]
    output_dir: Path
    db_path: Path


def run(
    pdf_folder: str | Path,
    *,
    db_path: str | Path | None = None,
    out_dir: str | Path | None = None,
    console: Console | None = None,
) -> FolderRunResult:
    resolved_console = console or Console()
    resolved_pdf_folder = Path(pdf_folder).expanduser().resolve()

    _print_banner(resolved_console, resolved_pdf_folder)
    pdf_files = _validate_pdf_folder(resolved_pdf_folder)
    _run_preflight(resolved_console, len(pdf_files))

    resolved_out_dir = Path(out_dir).expanduser().resolve() if out_dir else resolved_pdf_folder / "invoice_agent_output"
    resolved_db_path = (
        Path(db_path).expanduser().resolve()
        if db_path
        else (resolved_out_dir / "invoice_data.db" if out_dir else resolved_pdf_folder / "invoice_data.db")
    )

    resolved_out_dir.mkdir(parents=True, exist_ok=True)
    resolved_db_path.parent.mkdir(parents=True, exist_ok=True)

    headers_csv = resolved_out_dir / "invoice_headers.csv"
    line_items_csv = resolved_out_dir / "invoice_line_items.csv"
    summaries_csv = resolved_out_dir / "invoice_summaries.csv"

    progress_state = {"headers_failed": 0, "tables_failed": 0}
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        TimeElapsedColumn(),
        console=resolved_console,
    ) as progress:
        headers_task = progress.add_task(_progress_text("Extracting headers", 0), total=len(pdf_files))

        def on_header(file_path: Path, ok: bool, reason: str | None) -> None:
            if not ok:
                progress_state["headers_failed"] += 1
            progress.update(
                headers_task,
                advance=1,
                description=_progress_text("Extracting headers", progress_state["headers_failed"]),
            )

        header_report = headers_run(
            pdf_dir=resolved_pdf_folder,
            output_csv=headers_csv,
            report_json=resolved_out_dir / "invoice_headers_report.json",
            verbose=False,
            progress_callback=on_header,
        )

        tables_task = progress.add_task(_progress_text("Extracting tables", 0), total=len(pdf_files))

        def on_table(file_path: Path, ok: bool, reason: str | None) -> None:
            if not ok:
                progress_state["tables_failed"] += 1
            progress.update(
                tables_task,
                advance=1,
                description=_progress_text("Extracting tables", progress_state["tables_failed"]),
            )

        table_report = tables_run(
            pdf_dir=resolved_pdf_folder,
            line_items_csv=line_items_csv,
            summaries_csv=summaries_csv,
            report_json=resolved_out_dir / "invoice_tables_report.json",
            verbose=False,
            progress_callback=on_table,
        )

        load_task = progress.add_task("Loading database", total=1)
        load_run(csv_dir=resolved_out_dir, db_path=resolved_db_path, verbose=False)
        progress.update(load_task, advance=1, description="[green]Loading database")

    failed = _merge_failures(header_report, table_report)
    result = FolderRunResult(
        total_files=len(pdf_files),
        succeeded=len(pdf_files) - len({item["file"] for item in failed}),
        failed=failed,
        output_dir=resolved_out_dir,
        db_path=resolved_db_path,
    )
    _print_summary(resolved_console, result)

    if result.succeeded > 0:
        run_interactive(db_path=resolved_db_path, console=resolved_console)
    else:
        resolved_console.print("[yellow]No processable invoices found. Skipping Q&A session.[/yellow]")

    resolved_console.print("[dim]Want to run steps individually? See: invoice-agent --help[/dim]")
    return result


def _validate_pdf_folder(pdf_folder: Path) -> list[Path]:
    if not pdf_folder.exists():
        raise ValueError(f"Input folder not found: {pdf_folder}")
    if not pdf_folder.is_dir():
        raise ValueError(f"Input path is not a folder: {pdf_folder}")

    pdf_files = sorted(path for path in pdf_folder.iterdir() if path.is_file() and path.suffix.lower() == ".pdf")
    if not pdf_files:
        raise ValueError(f"No PDF files found in: {pdf_folder}")
    return pdf_files


def _run_preflight(console: Console, pdf_count: int) -> None:
    console.print("[bold]Preflight checks[/bold]")
    console.print("[green]OK[/green] Input folder found")
    console.print(f"[green]OK[/green] PDF files found: {pdf_count}")

    api_result = ensure_openrouter_api_key(lambda prompt: console.input(prompt))
    console.print("[green]OK[/green] OpenRouter API key found")
    if api_result.warning:
        console.print(f"[yellow]WARN[/yellow] {api_result.warning}")
    console.print()


def _merge_failures(header_report: dict, table_report: dict) -> list[dict[str, str]]:
    failures: dict[str, list[str]] = {}
    for stage, report in (("headers", header_report), ("tables", table_report)):
        for item in report.get("failed", []):
            file_name = str(item.get("file", "unknown"))
            reason = str(item.get("reason", "Unknown error"))
            failures.setdefault(file_name, []).append(f"{stage}: {reason}")
    return [
        {"file": file_name, "reason": "; ".join(reasons)}
        for file_name, reasons in sorted(failures.items())
    ]


def _print_banner(console: Console, target: Path) -> None:
    try:
        package_version = version("invoice-agent")
    except PackageNotFoundError:
        package_version = "0.1.0"

    console.print(
        Panel.fit(
            f"[bold]Invoice Agent v{package_version}[/bold]\n"
            "Extract invoice PDFs into a searchable local database\n\n"
            f"[dim]Target:[/dim] {target}",
            border_style="cyan",
        )
    )


def _progress_text(label: str, failed: int) -> str:
    style = "yellow" if failed else "green"
    return f"[{style}]{label} - {failed} failed"


def _print_summary(console: Console, result: FolderRunResult) -> None:
    table = Table(title="Run Summary")
    table.add_column("Metric", style="bold")
    table.add_column("Value")
    table.add_row("Total PDF files", str(result.total_files))
    table.add_row("Successfully processed", f"[green]{result.succeeded}[/green]")
    table.add_row("Failed", f"[red]{len(result.failed)}[/red]" if result.failed else "[green]0[/green]")
    table.add_row("Output CSV folder", str(result.output_dir))
    table.add_row("Database", str(result.db_path))
    console.print(table)

    if not result.failed:
        console.print("[green]No failed files.[/green]")
        return

    failed_table = Table(title="Failed Files")
    failed_table.add_column("File", style="red")
    failed_table.add_column("Reason")
    for item in result.failed:
        failed_table.add_row(item["file"], item["reason"])
    console.print(failed_table)
