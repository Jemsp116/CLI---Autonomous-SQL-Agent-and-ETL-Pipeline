from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pandas as pd
from rich.console import Console
from rich.table import Table

from invoice_agent.config import get_settings

console = Console()


def _safe_count(path: Path) -> int:
    if not path.exists():
        return 0
    return len(list(path.iterdir())) if path.is_dir() else 1


def _load_report(path: Path) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _report_entry_name(entry: object) -> str:
    if isinstance(entry, dict):
        return str(entry.get("file", entry))
    return str(entry)


def run(
    csv_dir: str | Path | None = None,
    db_path: str | Path | None = None,
    invoices_dir: str | Path | None = None,
    report_dir: str | Path | None = None,
) -> None:
    settings = get_settings()
    resolved_csv_dir = Path(csv_dir or settings.headers_output_csv.parent)
    resolved_db_path = Path(db_path or settings.demo_db_path)
    resolved_invoices_dir = Path(invoices_dir or settings.headers_input_dir)
    resolved_report_dir = Path(report_dir or resolved_csv_dir)
    headers_report = _load_report(resolved_report_dir / "invoice_headers_report.json")
    tables_report = _load_report(resolved_report_dir / "invoice_tables_report.json")

    rows = [
        ("PDF invoices", resolved_invoices_dir, _safe_count(resolved_invoices_dir)),
        ("CSV dir", resolved_csv_dir, _safe_count(resolved_csv_dir)),
        ("Database", resolved_db_path, 1 if resolved_db_path.exists() else 0),
    ]

    table = Table(title="Pipeline Status")
    table.add_column("Artifact")
    table.add_column("Path")
    table.add_column("Count", justify="right")
    for label, path, count in rows:
        table.add_row(label, str(path), str(count))

    if resolved_db_path.exists():
        with sqlite3.connect(resolved_db_path) as conn:
            for table_name in ["invoices", "line_items"]:
                try:
                    count = pd.read_sql_query(f"SELECT COUNT(*) AS row_count FROM {table_name}", conn)["row_count"][0]
                except Exception:
                    count = 0
                table.add_row(f"DB: {table_name}", str(resolved_db_path), str(count))

    console.print(table)

    for label, report in [("Headers", headers_report), ("Tables", tables_report)]:
        if not report:
            console.print(f"[bold]{label} report[/bold]: not found")
            continue

        succeeded = report.get("succeeded", [])
        failed = report.get("failed", [])
        console.print(f"[bold]{label} report[/bold]: {len(succeeded)} succeeded, {len(failed)} failed")
        if succeeded:
            console.print(f"  succeeded: {', '.join(_report_entry_name(item) for item in succeeded)}")
        if failed:
            for item in failed:
                console.print(f"  failed: {item.get('file')} — {item.get('reason')}")

        mismatches = report.get("validation_mismatches", [])
        if mismatches:
            console.print(f"  validation mismatches: {len(mismatches)}")
            for item in mismatches:
                issues = "; ".join(item.get("issues", []))
                console.print(f"    {item.get('file')} — {issues}")


def main() -> None:
    run()


if __name__ == "__main__":
    main()
