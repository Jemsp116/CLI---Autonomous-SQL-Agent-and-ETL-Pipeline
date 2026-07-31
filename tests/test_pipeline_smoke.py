from __future__ import annotations

import sqlite3
from pathlib import Path

from invoice_agent.pipeline import run as pipeline_run


def test_full_pipeline_smoke(tmp_path):
    out_dir = tmp_path / "invoices"
    zip_path = tmp_path / "invoices.zip"
    csv_dir = tmp_path / "csv"
    db_path = tmp_path / "invoices.db"

    pipeline_run(
        count=5,
        out_dir=out_dir,
        zip_path=zip_path,
        csv_dir=csv_dir,
        db_path=db_path,
    )

    with sqlite3.connect(db_path) as conn:
        invoice_count = conn.execute("SELECT COUNT(*) FROM invoices").fetchone()[0]
        line_item_count = conn.execute("SELECT COUNT(*) FROM line_items").fetchone()[0]

    assert invoice_count == 5
    assert line_item_count == 25
    assert (csv_dir / "invoice_headers.csv").exists()
    assert (csv_dir / "invoice_line_items.csv").exists()
    assert (csv_dir / "invoice_summaries.csv").exists()
