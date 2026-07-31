from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from invoice_agent.db.loader import run


def _write_sample_csvs(csv_dir: Path) -> None:
    csv_dir.mkdir(parents=True, exist_ok=True)

    pd.DataFrame([
        {
            "invoice_no": "1001",
            "date_of_issue": "01/01/2024",
            "seller_name": "Seller One",
            "seller_address": "1 Market Street",
            "seller_tax_id": "TAX-1",
            "seller_gstin": "GSTIN-1",
            "client_name": "Client A",
            "client_address": "10 Client Road",
            "client_tax_id": "CTAX-1",
        },
        {
            "invoice_no": "1002",
            "date_of_issue": "02/01/2024",
            "seller_name": "Seller One",
            "seller_address": "1 Market Street",
            "seller_tax_id": "TAX-1",
            "seller_gstin": "GSTIN-1",
            "client_name": "Client B",
            "client_address": "20 Client Road",
            "client_tax_id": "CTAX-2",
        },
    ]).to_csv(csv_dir / "invoice_headers.csv", index=False)

    pd.DataFrame([
        {
            "invoice_no": "1001",
            "item_no": 1,
            "description": "Item A",
            "qty": 2,
            "unit": "pcs",
            "net_price": 10.0,
            "net_worth": 20.0,
            "vat_pct": "10%",
            "gross_worth": 22.0,
        },
        {
            "invoice_no": "1002",
            "item_no": 1,
            "description": "Item B",
            "qty": 1,
            "unit": "pcs",
            "net_price": 15.0,
            "net_worth": 15.0,
            "vat_pct": "10%",
            "gross_worth": 16.5,
        },
        {
            "invoice_no": "1002",
            "item_no": 2,
            "description": "Item C",
            "qty": 3,
            "unit": "pcs",
            "net_price": 5.0,
            "net_worth": 15.0,
            "vat_pct": "10%",
            "gross_worth": 16.5,
        },
    ]).to_csv(csv_dir / "invoice_line_items.csv", index=False)


def _table_count(db_path: Path, table_name: str) -> int:
    with sqlite3.connect(db_path) as conn:
        return conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]


def test_loader_is_idempotent(tmp_path):
    csv_dir = tmp_path / "csv"
    db_path = tmp_path / "invoices.db"
    _write_sample_csvs(csv_dir)

    run(csv_dir=csv_dir, db_path=db_path)
    first_invoices = _table_count(db_path, "invoices")
    first_line_items = _table_count(db_path, "line_items")

    run(csv_dir=csv_dir, db_path=db_path)
    second_invoices = _table_count(db_path, "invoices")
    second_line_items = _table_count(db_path, "line_items")

    assert first_invoices == 2
    assert first_line_items == 3
    assert second_invoices == first_invoices
    assert second_line_items == first_line_items
