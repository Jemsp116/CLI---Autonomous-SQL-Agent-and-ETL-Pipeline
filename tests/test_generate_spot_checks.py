from __future__ import annotations

from pathlib import Path

from invoice_agent.generate import run as generate_run


def test_generate_small_batch_skips_missing_spot_checks(tmp_path):
    out_dir = tmp_path / "invoices"
    zip_path = tmp_path / "invoices.zip"

    generate_run(
        out_dir=out_dir,
        zip_path=zip_path,
        start_invoice_no=51109301,
        end_invoice_no=51109306,
        spot_check_invoice_nos=(51109301, 51109325, 51109350),
    )

    generated_pdfs = sorted(out_dir.glob("invoice_*.pdf"))
    assert len(generated_pdfs) == 5
    assert zip_path.exists()