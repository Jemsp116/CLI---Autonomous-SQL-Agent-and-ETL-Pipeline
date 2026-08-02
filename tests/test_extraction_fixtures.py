from __future__ import annotations

from pathlib import Path
import json

import pandas as pd

from invoice_agent.extract.headers import run as headers_run
from invoice_agent.extract.tables import run as tables_run


FIXTURES = Path(__file__).parent / "fixtures"


def test_headers_run_on_fixtures(tmp_path):
    output_csv = tmp_path / "headers.csv"
    report_json = tmp_path / "invoice_headers_report.json"

    headers_run(pdf_dir=FIXTURES, output_csv=output_csv, report_json=report_json)

    result = pd.read_csv(output_csv)

    assert len(result) == 3
    assert result.loc[0, "invoice_no"] == 51109301
    assert result.loc[0, "date_of_issue"] == "03/07/2023"
    assert result.loc[0, "seller_name"] == "TechVision Distributors Pvt Ltd"
    assert result.loc[0, "client_name"] == "Raj Electronics Pvt Ltd"
    assert result.loc[1, "invoice_no"] == 51109302
    assert result.loc[1, "client_name"] == "Sharma Tech Solutions"
    assert result.loc[2, "invoice_no"] == 51109303
    assert result.loc[2, "client_address"] == "78 Linking Road, Mumbai, Maharashtra - 400050"

    report = json.loads(report_json.read_text(encoding="utf-8"))
    assert report["succeeded"][0]["method"] == "rules"


def test_tables_run_on_fixtures(tmp_path):
    line_items_csv = tmp_path / "line_items.csv"
    summaries_csv = tmp_path / "summaries.csv"
    report_json = tmp_path / "invoice_tables_report.json"

    tables_run(
        pdf_dir=FIXTURES,
        line_items_csv=line_items_csv,
        summaries_csv=summaries_csv,
        report_json=report_json,
    )

    line_items = pd.read_csv(line_items_csv)
    summaries = pd.read_csv(summaries_csv)

    assert len(line_items) == 13
    assert len(summaries) == 3
    assert list(summaries["invoice_no"]) == [51109301, 51109302, 51109303]
    assert line_items.loc[0, "description"] == "Garmin Fenix 7 Solar Multisport GPS"
    assert line_items.loc[0, "gross_worth"] == 733788.0
    assert summaries.loc[0, "total_gross_worth"] == 1844673.6

    report = json.loads(report_json.read_text(encoding="utf-8"))
    assert report["succeeded"][0]["method"] == "rules"