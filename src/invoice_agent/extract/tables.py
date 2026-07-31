from __future__ import annotations

import json
import csv
import os
import re
from collections.abc import Callable
from pathlib import Path

import camelot
import pandas as pd
import pdfplumber

from invoice_agent.config import get_settings

LATTICE_KWARGS = dict(
    flavor="lattice",
    line_scale=40,
    copy_text=["v"],
)

STREAM_KWARGS = dict(
    flavor="stream",
    edge_tol=50,
    row_tol=10,
    column_tol=10,
)


def clean(val):
    return str(val).replace("\n", " ").strip()


def parse_amount(val):
    val = clean(val)
    val = re.sub(r"[^\d.]", "", val.replace(",", ""))
    try:
        return float(val) if val else None
    except ValueError:
        return None


def invoice_no_from_path(fpath):
    m = re.search(r"invoice_(\d+)", os.path.basename(fpath))
    return m.group(1) if m else ""


def classify_table(df):
    if df.empty:
        return "unknown"
    header = " ".join(str(c) for c in df.iloc[0].tolist()).lower()
    if "description" in header:
        return "items"
    if "net worth" in header and "description" not in header:
        return "summary"
    return "unknown"


def parse_items_table(df, invoice_no):
    records = []
    for _, row in df.iloc[1:].iterrows():
        values = [clean(v) for v in row.tolist()]
        if not any(values):
            continue

        no_ = values[0] if len(values) > 0 else ""
        desc = values[1] if len(values) > 1 else ""
        qty = values[2] if len(values) > 2 else ""
        um = values[3] if len(values) > 3 else ""
        net_price = values[4] if len(values) > 4 else ""
        net_worth = values[5] if len(values) > 5 else ""
        vat_pct = values[6] if len(values) > 6 else ""
        gross_worth = values[7] if len(values) > 7 else ""

        if "description" in desc.lower():
            continue

        records.append({
            "invoice_no": invoice_no,
            "item_no": no_.rstrip("."),
            "description": desc,
            "qty": parse_amount(qty),
            "unit": um,
            "net_price": parse_amount(net_price),
            "net_worth": parse_amount(net_worth),
            "vat_pct": vat_pct,
            "gross_worth": parse_amount(gross_worth),
        })

    return records


def parse_summary_table(df, invoice_no):
    result = {
        "invoice_no": invoice_no,
        "vat_pct": "",
        "total_net_worth": None,
        "total_vat": None,
        "total_gross_worth": None,
    }

    rows = [[clean(v) for v in row.tolist()] for _, row in df.iterrows()]

    for row in rows:
        flat = " ".join(row).lower()
        if "10%" in flat and "total" not in flat and "net worth" not in flat:
            result["vat_pct"] = "10%"
            result["total_net_worth"] = parse_amount(row[2]) if len(row) > 2 else None
            result["total_vat"] = parse_amount(row[3]) if len(row) > 3 else None
            result["total_gross_worth"] = parse_amount(row[4]) if len(row) > 4 else None

        if "total" in flat:
            nw = parse_amount(row[2]) if len(row) > 2 else None
            vat = parse_amount(row[3]) if len(row) > 3 else None
            gw = parse_amount(row[4]) if len(row) > 4 else None
            if nw:
                result["total_net_worth"] = nw
            if vat:
                result["total_vat"] = vat
            if gw:
                result["total_gross_worth"] = gw

    return result


def extract_tables(pdf_path, *, verbose: bool = True):
    invoice_no = invoice_no_from_path(pdf_path)
    tables = camelot.read_pdf(str(pdf_path), pages="1", **LATTICE_KWARGS)
    used_fallback = ""
    if len(tables) == 0:
        if verbose:
            print(f"  lattice found no tables for {Path(pdf_path).name}; retrying with stream mode")
        tables = camelot.read_pdf(str(pdf_path), pages="1", **STREAM_KWARGS)
        used_fallback = "stream"

    line_items = []
    summary = None

    for tbl in tables:
        df = tbl.df
        kind = classify_table(df)
        if kind == "items":
            line_items = parse_items_table(df, invoice_no)
        elif kind == "summary":
            summary = parse_summary_table(df, invoice_no)

    return line_items, summary, used_fallback


def extract_tables_pdfplumber(pdf_path, *, verbose: bool = True):
    invoice_no = invoice_no_from_path(pdf_path)
    line_items = []
    summary = None

    try:
        with pdfplumber.open(pdf_path) as pdf:
            page = pdf.pages[0]
            raw_tables = page.extract_tables()
    except Exception as exc:
        if verbose:
            print(f"  pdfplumber failed for {Path(pdf_path).name}: {exc}")
        raise

    if not raw_tables:
        if verbose:
            print(f"  pdfplumber found no tables for {Path(pdf_path).name}")
        return line_items, summary, "pdfplumber"

    for raw in raw_tables:
        if not raw or len(raw) < 2:
            continue
        header = " ".join(str(cell or "") for cell in raw[0]).lower()
        df = pd.DataFrame(raw[1:], columns=raw[0])
        df = df.fillna("")
        kind = classify_table(df)
        if kind == "items":
            line_items = parse_items_table(df, invoice_no)
        elif kind == "summary":
            summary = parse_summary_table(df, invoice_no)

    return line_items, summary, "pdfplumber"


def validate_totals(line_items, summary):
    if not summary:
        return {"status": "missing_summary", "issues": ["No summary table extracted"]}

    issues = []
    line_net = sum(item.get("net_worth") or 0 for item in line_items)
    line_gross = sum(item.get("gross_worth") or 0 for item in line_items)
    line_vat = sum((item.get("gross_worth") or 0) - (item.get("net_worth") or 0) for item in line_items)

    if summary.get("total_net_worth") is not None and round(line_net, 2) != round(summary["total_net_worth"], 2):
        issues.append(f"net_worth mismatch: line items={line_net:.2f} summary={summary['total_net_worth']:.2f}")
    if summary.get("total_vat") is not None and round(line_vat, 2) != round(summary["total_vat"], 2):
        issues.append(f"vat mismatch: line items={line_vat:.2f} summary={summary['total_vat']:.2f}")
    if summary.get("total_gross_worth") is not None and round(line_gross, 2) != round(summary["total_gross_worth"], 2):
        issues.append(f"gross_worth mismatch: line items={line_gross:.2f} summary={summary['total_gross_worth']:.2f}")

    return {
        "status": "ok" if not issues else "mismatch",
        "issues": issues,
        "line_totals": {
            "net_worth": round(line_net, 2),
            "vat": round(line_vat, 2),
            "gross_worth": round(line_gross, 2),
        },
        "summary_totals": {
            "net_worth": summary.get("total_net_worth"),
            "vat": summary.get("total_vat"),
            "gross_worth": summary.get("total_gross_worth"),
        },
    }


def run(
    pdf_dir: str | Path | None = None,
    line_items_csv: str | Path | None = None,
    summaries_csv: str | Path | None = None,
    report_json: str | Path | None = None,
    *,
    verbose: bool = True,
    progress_callback: Callable[[Path, bool, str | None], None] | None = None,
) -> dict:
    settings = get_settings()
    resolved_pdf_dir = Path(pdf_dir or settings.tables_input_dir)
    resolved_line_items_csv = Path(line_items_csv or settings.line_items_csv)
    resolved_summaries_csv = Path(summaries_csv or settings.summaries_csv)
    resolved_report_json = Path(report_json or settings.tables_report_json)

    invoice_files = sorted([
        f for f in resolved_pdf_dir.iterdir()
        if f.is_file() and f.suffix.lower() == ".pdf"
    ])

    if not invoice_files:
        if verbose:
            print(f"No invoice PDFs found in {resolved_pdf_dir}")
        return {
            "input_dir": str(resolved_pdf_dir),
            "line_items_csv": str(resolved_line_items_csv),
            "summaries_csv": str(resolved_summaries_csv),
            "succeeded": [],
            "failed": [],
            "validation_mismatches": [],
            "total_input_files": 0,
            "total_succeeded": 0,
            "total_failed": 0,
            "total_validation_mismatches": 0,
        }

    all_line_items = []
    all_summaries = []
    succeeded = []
    failed = []
    validation_mismatches = []

    if verbose:
        print(f"Extracting tables from {len(invoice_files)} invoices ...\n")

    for file_path in invoice_files:
        try:
            try:
                items, summary, used_fallback = extract_tables(file_path, verbose=verbose)
            except Exception as camelot_exc:
                if verbose:
                    print(f"  Camelot failed for {file_path.name}: {camelot_exc}; trying pdfplumber fallback")
                items, summary, used_fallback = extract_tables_pdfplumber(file_path, verbose=verbose)
            all_line_items.extend(items)
            if summary:
                all_summaries.append(summary)

            validation = validate_totals(items, summary)
            if validation["status"] == "mismatch":
                validation_mismatches.append({
                    "file": file_path.name,
                    "issues": validation["issues"],
                    "line_totals": validation["line_totals"],
                    "summary_totals": validation["summary_totals"],
                })

            succeeded.append({
                "file": file_path.name,
                "used_fallback": used_fallback,
                "validation_status": validation["status"],
            })

            if verbose:
                print(f"  OK: {file_path.name}")
                print(f"       Line items extracted : {len(items)}")
                if used_fallback:
                    print(f"       Camelot mode         : {used_fallback}")
                if summary:
                    print(f"       Total Net Worth      : INR {summary['total_net_worth']:,.2f}")
                    print(f"       Total VAT            : INR {summary['total_vat']:,.2f}")
                    print(f"       Total Gross Worth    : INR {summary['total_gross_worth']:,.2f}")
                if validation["status"] == "mismatch":
                    print("       Validation           : MISMATCH")
                    for issue in validation["issues"]:
                        print(f"         - {issue}")
                else:
                    print("       Validation           : OK")
                print()
            if progress_callback:
                progress_callback(file_path, True, None)
        except Exception as exc:
            reason = str(exc)
            failed.append({"file": file_path.name, "reason": reason})
            if verbose:
                print(f"  ERROR: {file_path.name} - {reason}")
            if progress_callback:
                progress_callback(file_path, False, reason)

    li_fields = [
        "invoice_no", "item_no", "description",
        "qty", "unit", "net_price", "net_worth", "vat_pct", "gross_worth",
    ]
    resolved_line_items_csv.parent.mkdir(parents=True, exist_ok=True)
    with resolved_line_items_csv.open("w", newline="", encoding="utf-8") as file_handle:
        writer = csv.DictWriter(file_handle, fieldnames=li_fields)
        writer.writeheader()
        writer.writerows(all_line_items)

    sum_fields = ["invoice_no", "vat_pct", "total_net_worth", "total_vat", "total_gross_worth"]
    with resolved_summaries_csv.open("w", newline="", encoding="utf-8") as file_handle:
        writer = csv.DictWriter(file_handle, fieldnames=sum_fields)
        writer.writeheader()
        writer.writerows(all_summaries)

    report = {
        "input_dir": str(resolved_pdf_dir),
        "line_items_csv": str(resolved_line_items_csv),
        "summaries_csv": str(resolved_summaries_csv),
        "succeeded": succeeded,
        "failed": failed,
        "validation_mismatches": validation_mismatches,
        "total_input_files": len(invoice_files),
        "total_succeeded": len(succeeded),
        "total_failed": len(failed),
        "total_validation_mismatches": len(validation_mismatches),
    }

    if verbose:
        print("=" * 55)
        print(f" Line items saved -> {resolved_line_items_csv}")
        print(f"   Total line item rows : {len(all_line_items)}")
        print()
        print(f"Summaries saved  -> {resolved_summaries_csv}")
        print(f"   Total summary rows   : {len(all_summaries)}")

        li_df = pd.read_csv(resolved_line_items_csv)
        sum_df = pd.read_csv(resolved_summaries_csv)
        print()
        print("Line Items sample ")
        print(li_df.head(3).to_string(index=False))
        print()
        print("Summaries sample ")
        print(sum_df.head(3).to_string(index=False))
        print(f"\n Report saved -> {resolved_report_json}")
    return report


def main() -> None:
    run()


if __name__ == "__main__":
    main()
