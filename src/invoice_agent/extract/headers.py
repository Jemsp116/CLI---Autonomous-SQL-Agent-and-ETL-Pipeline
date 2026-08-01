from __future__ import annotations

import json
import csv
import re
from collections.abc import Callable
from pathlib import Path

import pdfplumber

from invoice_agent.config import get_settings

CLIENT_X_THRESHOLD = 240
ITEMS_SECTION_LABEL = "ITEMS"


def group_words_by_row(words, y_tolerance=3):
    rows = []
    for word in sorted(words, key=lambda w: (round(w["top"] / y_tolerance), w["x0"])):
        placed = False
        for row in rows:
            if abs(row[0]["top"] - word["top"]) <= y_tolerance:
                row.append(word)
                placed = True
                break
        if not placed:
            rows.append([word])
    for row in rows:
        row.sort(key=lambda w: w["x0"])
    rows.sort(key=lambda r: r[0]["top"])
    return rows


def row_text(row):
    return " ".join(w["text"] for w in row)


def split_row_by_column(row, threshold=CLIENT_X_THRESHOLD):
    left = [w["text"] for w in row if w["x0"] < threshold]
    right = [w["text"] for w in row if w["x0"] >= threshold]
    return " ".join(left).strip(), " ".join(right).strip()


def extract_header(pdf_path):
    result = {
        "invoice_no": "",
        "date_of_issue": "",
        "seller_name": "",
        "seller_address": "",
        "seller_tax_id": "",
        "seller_gstin": "",
        "client_name": "",
        "client_address": "",
        "client_tax_id": "",
    }

    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[0]
        words = page.extract_words()

    rows = group_words_by_row(words, y_tolerance=4)

    for row in rows:
        text = row_text(row)

        if text.startswith("Invoice no:"):
            m = re.search(r"Invoice no:\s*(\d+)", text)
            if m:
                result["invoice_no"] = m.group(1)
            continue

        if text.startswith("Date of issue:"):
            m = re.search(r"Date of issue:\s*([\d/]+)", text)
            if m:
                result["date_of_issue"] = m.group(1)
            continue

        if "Seller:" in text and "Client:" in text:
            _parse_seller_client_block(rows, result)
            return result

    if not result["invoice_no"]:
        _parse_alternative_header(rows, result)

    return result


def _parse_seller_client_block(rows, result):
    in_seller_client_block = False
    seller_lines = []
    client_lines = []

    for row in rows:
        text = row_text(row)

        if "Seller:" in text and "Client:" in text:
            in_seller_client_block = True
            continue

        if ITEMS_SECTION_LABEL in text and len(text.strip()) <= 10:
            in_seller_client_block = False
            break

        if in_seller_client_block:
            left, right = split_row_by_column(row)

            if left.startswith("Tax Id:"):
                result["seller_tax_id"] = left.replace("Tax Id:", "").strip()
                if right.startswith("Tax Id:"):
                    result["client_tax_id"] = right.replace("Tax Id:", "").strip()
                continue

            if left.startswith("GSTIN:"):
                result["seller_gstin"] = left.replace("GSTIN:", "").strip()
                continue

            if left:
                seller_lines.append(left)
            if right:
                client_lines.append(right)

    if seller_lines:
        result["seller_name"] = seller_lines[0]
        result["seller_address"] = ", ".join(seller_lines[1:])
    if client_lines:
        result["client_name"] = client_lines[0]
        result["client_address"] = ", ".join(client_lines[1:])


def _parse_alternative_header(rows, result):
    to_blocks = []
    current_block = []
    in_block = False

    for row in rows:
        text = row_text(row)

        if re.match(r"^TO:\s*$", text):
            in_block = True
            current_block = []
            continue

        if re.match(r"^(COMMENTS|OR|SPECIAL|INSTRUCTIONS|SALESPERSON|P\.O\.|TERMS)", text):
            in_block = False
            if current_block:
                to_blocks.append(current_block)
                current_block = []
            continue

        if in_block:
            current_block.append(row_text(row))

    if current_block:
        to_blocks.append(current_block)

    for row in rows:
        text = row_text(row)

        m = re.search(r"INVOICE\s*#\s*(\S+)", text, re.IGNORECASE)
        if m:
            result["invoice_no"] = m.group(1)
            continue

        m = re.search(r"DATE:\s*([\d./-]+)", text, re.IGNORECASE)
        if m:
            result["date_of_issue"] = m.group(1)
            continue

    if len(to_blocks) >= 1:
        result["seller_name"] = to_blocks[0][0] if to_blocks[0] else ""
        result["seller_address"] = ", ".join(to_blocks[0][1:]) if len(to_blocks[0]) > 1 else ""
    if len(to_blocks) >= 2:
        result["client_name"] = to_blocks[1][0] if to_blocks[1] else ""
        result["client_address"] = ", ".join(to_blocks[1][1:]) if len(to_blocks[1]) > 1 else ""


def run(
    pdf_dir: str | Path | None = None,
    output_csv: str | Path | None = None,
    report_json: str | Path | None = None,
    *,
    verbose: bool = True,
    progress_callback: Callable[[Path, bool, str | None], None] | None = None,
) -> dict:
    settings = get_settings()
    resolved_pdf_dir = Path(pdf_dir or settings.headers_input_dir)
    resolved_output_csv = Path(output_csv or settings.headers_output_csv)
    resolved_report_json = Path(report_json or settings.headers_report_json)

    invoice_files = sorted([
        f for f in resolved_pdf_dir.iterdir()
        if f.is_file() and f.suffix.lower() == ".pdf"
    ])

    if not invoice_files:
        if verbose:
            print(f"No invoice PDFs found in {resolved_pdf_dir}")
        return {
            "input_dir": str(resolved_pdf_dir),
            "output_csv": str(resolved_output_csv),
            "succeeded": [],
            "failed": [],
            "total_input_files": 0,
            "total_succeeded": 0,
            "total_failed": 0,
        }

    fieldnames = [
        "invoice_no", "date_of_issue",
        "seller_name", "seller_address", "seller_tax_id", "seller_gstin",
        "client_name", "client_address", "client_tax_id",
    ]

    records = []
    succeeded = []
    failed = []
    if verbose:
        print(f"Extracting headers from {len(invoice_files)} invoices ...\n")

    for file_path in invoice_files:
        try:
            data = extract_header(file_path)
            if not data.get("invoice_no"):
                raise ValueError("Invoice number not found in PDF")
            records.append(data)
            succeeded.append(file_path.name)
            if verbose:
                print(f"   {file_path.name}")
                print(f"       Invoice No  : {data['invoice_no']}")
                print(f"       Date        : {data['date_of_issue']}")
                print(f"       Seller      : {data['seller_name']}")
                print(f"       Client      : {data['client_name']}")
                print(f"       Client Addr : {data['client_address']}")
                print(f"       Client TaxId: {data['client_tax_id']}")
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

    resolved_output_csv.parent.mkdir(parents=True, exist_ok=True)
    with resolved_output_csv.open("w", newline="", encoding="utf-8") as file_handle:
        writer = csv.DictWriter(file_handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(records)

    report = {
        "input_dir": str(resolved_pdf_dir),
        "output_csv": str(resolved_output_csv),
        "succeeded": succeeded,
        "failed": failed,
        "total_input_files": len(invoice_files),
        "total_succeeded": len(succeeded),
        "total_failed": len(failed),
    }
    resolved_report_json.parent.mkdir(parents=True, exist_ok=True)
    resolved_report_json.write_text(json.dumps(report, indent=2), encoding="utf-8")

    if verbose:
        print(f"\n Headers saved -> {resolved_output_csv}")
        print(f"   Total records : {len(records)}")
        print(f"   Report saved  -> {resolved_report_json}")
    return report


def main() -> None:
    run()


if __name__ == "__main__":
    main()
