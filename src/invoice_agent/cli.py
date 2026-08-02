from __future__ import annotations

import sys
from pathlib import Path

import typer
from rich.console import Console

from invoice_agent.ask import run_interactive as ask_run
from invoice_agent.extract.headers import run as extract_headers_run
from invoice_agent.extract.tables import run as extract_tables_run
from invoice_agent.folder_pipeline import run as folder_pipeline_run
from invoice_agent.generate import run as generate_run
from invoice_agent.load import run as load_run
from invoice_agent.pipeline import run as pipeline_run
from invoice_agent.status import run as status_run


class InvoiceAgentCLI(typer.Typer):
    def __call__(self, *args, **kwargs):
        if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
            first_arg = Path(sys.argv[1])
            if first_arg.exists() and first_arg.is_dir():
                sys.argv.insert(1, "process")
        try:
            super().__call__(*args, **kwargs)
        except SystemExit as exc:
            if exc.code == 0 or (exc.code == 2 and len(sys.argv) <= 1):
                console.print("[dim]Want to run steps individually? See: invoice-agent --help[/dim]")
            raise


app = InvoiceAgentCLI(add_completion=False, help="Invoice agent command line interface.", no_args_is_help=True)
extract_app = typer.Typer(add_completion=False, help="Extraction commands.")
console = Console()


@app.command()
def process(
    pdf_folder: Path = typer.Argument(..., help="Folder containing invoice PDFs."),
    db: Path | None = typer.Option(None, "--db", help="Output SQLite database path."),
    out: Path | None = typer.Option(None, "--out", help="Output folder for CSV and report files."),
) -> None:
    try:
        folder_pipeline_run(pdf_folder=pdf_folder, db_path=db, out_dir=out, console=console)
    except (RuntimeError, ValueError) as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1) from exc


@app.command()
def generate(
    count: int = typer.Option(50, help="Number of invoices to generate."),
    out: Path = typer.Option(Path("data/invoices"), help="Output directory for PDFs."),
    zip_path: Path = typer.Option(Path("data/invoices.zip"), help="ZIP output path."),
) -> None:
    console.print(f"[bold]generate[/bold] count={count} out={out} zip={zip_path}")
    generate_run(out_dir=out, zip_path=zip_path, start_invoice_no=51109301, end_invoice_no=51109301 + count)


@extract_app.command("headers")
def extract_headers(
    in_dir: Path = typer.Option(Path("data/invoices"), "--in", help="Input directory containing invoice PDFs."),
    out: Path = typer.Option(Path("data/csv/invoice_headers.csv"), help="Output CSV path."),
    enable_llm_fallback: bool = typer.Option(True, "--llm-fallback/--no-llm-fallback", help="Enable LLM fallback for headers extraction."),
) -> None:
    console.print(f"[bold]extract headers[/bold] in={in_dir} out={out}")
    extract_headers_run(pdf_dir=in_dir, output_csv=out, enable_llm_fallback=enable_llm_fallback)


@extract_app.command("tables")
def extract_tables(
    in_dir: Path = typer.Option(Path("data/invoices"), "--in", help="Input directory containing invoice PDFs."),
    line_items_out: Path = typer.Option(Path("data/csv/invoice_line_items.csv"), help="Line items CSV path."),
    summaries_out: Path = typer.Option(Path("data/csv/invoice_summaries.csv"), help="Summaries CSV path."),
    enable_llm_fallback: bool = typer.Option(True, "--llm-fallback/--no-llm-fallback", help="Enable LLM fallback for tables extraction."),
) -> None:
    console.print(f"[bold]extract tables[/bold] in={in_dir} line_items={line_items_out} summaries={summaries_out}")
    extract_tables_run(pdf_dir=in_dir, line_items_csv=line_items_out, summaries_csv=summaries_out, enable_llm_fallback=enable_llm_fallback)


app.add_typer(extract_app, name="extract")


@app.command()
def load(
    csv: Path = typer.Option(Path("data/csv"), "--csv", help="CSV directory."),
    db: Path = typer.Option(Path("data/db.sqlite"), "--db", help="SQLite database path."),
) -> None:
    console.print(f"[bold]load[/bold] csv={csv} db={db}")
    load_run(csv_dir=csv, db_path=db)


@app.command()
def ask(
    question: str = typer.Argument(..., help="Question to ask about loaded invoices."),
    db: Path = typer.Option(Path("data/db.sqlite"), "--db", help="SQLite database path."),
) -> None:
    console.print(f"[bold]ask[/bold] db={db} question={question}")
    ask_run(initial_question=question, db_path=db)


@app.command()
def pipeline(
    count: int = typer.Option(50, help="Number of invoices to generate."),
    out: Path = typer.Option(Path("data/invoices"), help="PDF output directory."),
    zip_path: Path = typer.Option(Path("data/invoices.zip"), help="ZIP output path."),
    csv: Path = typer.Option(Path("data/csv"), "--csv", help="CSV directory."),
    db: Path = typer.Option(Path("data/db.sqlite"), "--db", help="SQLite database path."),
    question: str | None = typer.Option(None, help="Optional question to ask after loading."),
    enable_llm_fallback: bool = typer.Option(True, "--llm-fallback/--no-llm-fallback", help="Enable LLM fallback for extraction."),
) -> None:
    console.print(f"[bold]pipeline[/bold] count={count} out={out} csv={csv} db={db}")
    pipeline_run(count=count, out_dir=out, zip_path=zip_path, csv_dir=csv, db_path=db, question=question, enable_llm_fallback=enable_llm_fallback)


@app.command()
def status(
    csv: Path = typer.Option(Path("data/csv"), "--csv", help="CSV directory."),
    db: Path = typer.Option(Path("data/db.sqlite"), "--db", help="SQLite database path."),
    invoices_dir: Path = typer.Option(Path("data/invoices"), help="Invoice PDF directory."),
) -> None:
    console.print(f"[bold]status[/bold] csv={csv} db={db} invoices_dir={invoices_dir}")
    status_run(csv_dir=csv, db_path=db, invoices_dir=invoices_dir)


if __name__ == "__main__":
    app()
