from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from invoice_agent.cli import app, InvoiceAgentCLI
from invoice_agent.extract.llm_fallback import LlmExtractionResult
from invoice_agent.folder_pipeline import run as folder_pipeline_run
from invoice_agent.preflight import ApiKeyResult

FIXTURES = Path(__file__).parent / "fixtures"
runner = CliRunner()


def test_folder_pipeline_smoke(tmp_path):
    fake_llm_result = LlmExtractionResult(
        header={
            "invoice_no": "MALFORMED-001",
            "date_of_issue": "2024-01-01",
            "seller_name": "Test Seller",
            "seller_address": "123 Test St",
            "seller_tax_id": "TIN-001",
            "seller_gstin": "GSTIN-001",
            "client_name": "Test Client",
            "client_address": "456 Client Ave",
            "client_tax_id": "TIN-002",
        },
        line_items=[
            {
                "invoice_no": "MALFORMED-001",
                "item_no": "1",
                "description": "Test Item",
                "qty": 1,
                "unit": "pcs",
                "net_price": 100.0,
                "net_worth": 100.0,
                "vat_pct": "10%",
                "gross_worth": 110.0,
            }
        ],
        summary={
            "invoice_no": "MALFORMED-001",
            "vat_pct": "10%",
            "total_net_worth": 100.0,
            "total_vat": 10.0,
            "total_gross_worth": 110.0,
        },
        used_llm=True,
    )
    with patch("invoice_agent.folder_pipeline.ensure_openrouter_api_key", return_value=ApiKeyResult(key_found=True, persisted=True)), \
         patch("invoice_agent.folder_pipeline.run_interactive"), \
         patch("invoice_agent.extract.headers.extract_full_invoice_llm", return_value=fake_llm_result), \
         patch("invoice_agent.extract.tables.extract_full_invoice_llm", return_value=fake_llm_result):
        out_dir = tmp_path / "output"
        result = folder_pipeline_run(
            pdf_folder=FIXTURES,
            out_dir=out_dir,
        )
        assert result.total_files >= 3
        assert result.succeeded >= 3
        assert result.failed == []
        assert (out_dir / "invoice_headers.csv").exists()
        assert (out_dir / "invoice_line_items.csv").exists()
        assert (out_dir / "invoice_summaries.csv").exists()
        assert (out_dir / "invoice_data.db").exists()


def test_cli_default_command_routes_folder():
    with patch.object(sys, "argv", ["invoice-agent", str(FIXTURES)]):
        cli = InvoiceAgentCLI(add_completion=False, help="Test CLI.")
        
        called = {}
        
        @cli.command()
        def process(pdf_folder: Path, db: Path | None = None, out: Path | None = None):
            called["args"] = (pdf_folder, db, out)
        
        @cli.command()
        def extract():
            pass
        
        with pytest.raises(SystemExit) as exc_info:
            cli()
        assert exc_info.value.code == 0
        assert "args" in called
        assert called["args"][0] == FIXTURES
