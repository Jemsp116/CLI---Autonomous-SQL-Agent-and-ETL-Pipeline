from __future__ import annotations

import json
from pathlib import Path

from invoice_agent.extract import llm_fallback
from invoice_agent.extract.headers import run as headers_run
from invoice_agent.config import get_settings


FIXTURES = Path(__file__).parent / "fixtures"


class _FakeResponse:
    def __init__(self, content: str) -> None:
        self.content = content


def test_extract_full_invoice_llm_uses_mocked_openai(monkeypatch):
    llm_fallback.clear_cache()
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test-fallback-key-1234567890")
    get_settings.cache_clear()

    payload = {
        "header": {
            "invoice_no": "A-2049",
            "date_of_issue": "2024-07-03",
            "seller_name": "Acme Industrial Supplies",
            "seller_address": "42 Market Street",
            "seller_tax_id": "TIN-123",
            "seller_gstin": "GSTIN-123",
            "client_name": "Northwind Traders",
            "client_address": "1 Harbor Road",
            "client_tax_id": "TIN-456",
        },
        "line_items": [
            {
                "invoice_no": "A-2049",
                "item_no": "1",
                "description": "Alpha Widget",
                "qty": 4,
                "unit": "pcs",
                "net_price": 125.0,
                "net_worth": 500.0,
                "vat_pct": "10%",
                "gross_worth": 550.0,
            }
        ],
        "summary": {
            "invoice_no": "A-2049",
            "vat_pct": "10%",
            "total_net_worth": 500.0,
            "total_vat": 50.0,
            "total_gross_worth": 550.0,
        },
    }

    calls: list[str] = []

    def fake_invoke(self, prompt):
        calls.append(prompt)
        return _FakeResponse(json.dumps(payload))

    monkeypatch.setattr("langchain_openai.ChatOpenAI.invoke", fake_invoke)

    result = llm_fallback.extract_full_invoice_llm(FIXTURES / "malformed_layout_invoice.pdf", "invoice text")

    assert result.used_llm is True
    assert result.header["invoice_no"] == "A-2049"
    assert result.line_items[0]["description"] == "Alpha Widget"
    assert result.summary["total_gross_worth"] == 550.0
    assert len(calls) == 1


def test_headers_run_uses_llm_fallback_on_malformed_fixture(monkeypatch, tmp_path):
    llm_fallback.clear_cache()
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test-fallback-key-1234567890")
    get_settings.cache_clear()

    payload = {
        "header": {
            "invoice_no": "A-2049",
            "date_of_issue": "2024-07-03",
            "seller_name": "Acme Industrial Supplies",
            "seller_address": "42 Market Street",
            "seller_tax_id": "TIN-123",
            "seller_gstin": "GSTIN-123",
            "client_name": "Northwind Traders",
            "client_address": "1 Harbor Road",
            "client_tax_id": "TIN-456",
        },
        "line_items": [],
        "summary": {},
    }

    def fake_invoke(self, prompt):
        return _FakeResponse(json.dumps(payload))

    monkeypatch.setattr("langchain_openai.ChatOpenAI.invoke", fake_invoke)

    output_csv = tmp_path / "headers.csv"
    report_json = tmp_path / "report.json"

    headers_run(
        pdf_dir=FIXTURES,
        output_csv=output_csv,
        report_json=report_json,
        enable_llm_fallback=True,
    )

    report = json.loads(report_json.read_text(encoding="utf-8"))
    fallback_records = [item for item in report["succeeded"] if item["file"] == "malformed_layout_invoice.pdf"]
    assert fallback_records and fallback_records[0]["method"] == "llm"