# Development Workflow

## 1. First-Time Setup

```bash
git clone <repo-url>
cd CLI - Autonomous-SQL-Agent-and-ETL-Pipeline
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .
invoice-agent --help
```

## 2. Everyday Commands

```bash
invoice-agent generate --count 10 --out data/invoices/
invoice-agent extract headers --in data/invoices/ --out data/csv/invoice_headers.csv
invoice-agent extract tables --in data/invoices/ --line-items-out data/csv/invoice_line_items.csv --summaries-out data/csv/invoice_summaries.csv
invoice-agent extract headers --in data/invoices/ --no-llm-fallback
invoice-agent extract tables --in data/invoices/ --no-llm-fallback
invoice-agent load --csv data/csv/ --db data/db.sqlite
invoice-agent ask "which client has the highest total spend?"
invoice-agent pipeline --count 10 --no-llm-fallback
invoice-agent status
```

## 3. Working on a Change

1. Check the relevant module first (`generate.py`, `extract/*.py`, `db/*.py`, `agent/*.py`, `ui/*.py`).
2. Keep `cli.py` limited to argument parsing and forwarding.
3. Update or add fixture-backed tests when extraction logic changes.
4. Run `pytest` before and after the change.
5. Manually sanity-check the affected command on real or generated invoice data.
6. Update `ARCHITECTURE.md` if the data flow or components change.

## 4. Debugging Extraction

1. Run `invoice-agent status` to inspect reports and current artifacts.
2. Check the per-file failure reason in the extraction report JSON.
3. Reproduce the issue by calling the relevant module directly from Python.
4. Add a test fixture if the file represents a durable edge case.

## 5. Before Merging

- `pytest` passes.
- `invoice-agent pipeline --count 5` works without network-dependent behavior in CI mode.
- No generated data, `.env`, or local databases are committed.
- `ARCHITECTURE.md` and `RULES.md` stay in sync with the code.
