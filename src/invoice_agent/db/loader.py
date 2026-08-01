from __future__ import annotations

from pathlib import Path

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from invoice_agent.config import get_settings

from .models import Base, Invoice, LineItem
from .session import create_db_engine


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [column.strip().lower() for column in df.columns]
    return df


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing required CSV: {path}")
    return normalize_columns(pd.read_csv(path))


def _to_text(value) -> str | None:
    if pd.isna(value):
        return None
    text = str(value).strip()
    return text or None


def _to_int(value) -> int | None:
    if pd.isna(value):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _to_float(value) -> float | None:
    if pd.isna(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def run(csv_dir: str | Path | None = None, db_path: str | Path | None = None, *, verbose: bool = True) -> Path:
    settings = get_settings()
    resolved_csv_dir = Path(csv_dir or settings.headers_output_csv.parent)
    resolved_db_path = Path(db_path or settings.demo_db_path)
    resolved_db_path.parent.mkdir(parents=True, exist_ok=True)

    headers_csv = resolved_csv_dir / "invoice_headers.csv"
    items_csv = resolved_csv_dir / "invoice_line_items.csv"

    headers_df = _read_csv(headers_csv)
    items_df = _read_csv(items_csv)

    required_header_columns = {
        "invoice_no",
        "date_of_issue",
        "seller_name",
        "seller_address",
        "seller_tax_id",
        "seller_gstin",
        "client_name",
        "client_address",
        "client_tax_id",
    }
    required_item_columns = {
        "invoice_no",
        "item_no",
        "description",
        "qty",
        "unit",
        "net_price",
        "net_worth",
        "vat_pct",
        "gross_worth",
    }

    missing_header_columns = sorted(required_header_columns - set(headers_df.columns))
    missing_item_columns = sorted(required_item_columns - set(items_df.columns))
    if missing_header_columns:
        raise ValueError(f"Missing columns in invoice_headers.csv: {missing_header_columns}")
    if missing_item_columns:
        raise ValueError(f"Missing columns in invoice_line_items.csv: {missing_item_columns}")

    engine = create_db_engine(resolved_db_path)
    Base.metadata.create_all(engine)

    inserted_invoices = 0
    inserted_line_items = 0

    with Session(engine) as session, session.begin():
        existing_invoices = {
            invoice.invoice_number: invoice
            for invoice in session.scalars(select(Invoice)).all()
        }
        existing_line_item_keys = {
            (line_item.invoice_id, line_item.item_no)
            for line_item in session.scalars(select(LineItem)).all()
        }

        for record in headers_df.to_dict(orient="records"):
            invoice_number = _to_text(record["invoice_no"])
            if invoice_number is None:
                continue

            invoice = existing_invoices.get(invoice_number)
            if invoice is None:
                invoice = Invoice(
                    invoice_number=invoice_number,
                    date_of_issue=_to_text(record["date_of_issue"]),
                    seller_name=_to_text(record["seller_name"]),
                    seller_address=_to_text(record["seller_address"]),
                    seller_tax_id=_to_text(record["seller_tax_id"]),
                    seller_gstin=_to_text(record["seller_gstin"]),
                    client_name=_to_text(record["client_name"]),
                    client_address=_to_text(record["client_address"]),
                    client_tax_id=_to_text(record["client_tax_id"]),
                )
                session.add(invoice)
                session.flush()
                existing_invoices[invoice_number] = invoice
                inserted_invoices += 1

        for idx, record in enumerate(items_df.to_dict(orient="records"), start=1):
            invoice_number = _to_text(record["invoice_no"])
            if invoice_number is None:
                continue

            invoice = existing_invoices.get(invoice_number)
            if invoice is None:
                continue

            item_no = _to_int(record["item_no"])
            if item_no is None:
                item_no = idx
            line_item_key = (invoice.id, item_no)
            if line_item_key in existing_line_item_keys:
                continue

            session.add(
                LineItem(
                    invoice_id=invoice.id,
                    item_no=item_no,
                    description=_to_text(record["description"]),
                    qty=_to_float(record["qty"]),
                    unit=_to_text(record["unit"]),
                    net_price=_to_float(record["net_price"]),
                    net_worth=_to_float(record["net_worth"]),
                    vat_pct=_to_text(record["vat_pct"]),
                    gross_worth=_to_float(record["gross_worth"]),
                )
            )
            existing_line_item_keys.add(line_item_key)
            inserted_line_items += 1

    if verbose:
        print(f"Database created at: {resolved_db_path}")
        print(f"Inserted {inserted_invoices} invoice rows.")
        print(f"Inserted {inserted_line_items} invoice item rows.")
    return resolved_db_path


def main() -> None:
    run()


if __name__ == "__main__":
    main()
