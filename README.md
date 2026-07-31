# invoice-agent

CLI-first invoice extraction and analysis pipeline.

This project generates sample invoice PDFs, extracts structured data from them, loads the results into SQLite or Postgres, and answers SQL-backed questions from the command line.

## What It Does

- Generates deterministic sample invoice PDFs for demos and tests
- Extracts invoice headers with `pdfplumber`
- Extracts line items and summary tables with `camelot`
- Loads CSV output into a relational database with SQLAlchemy
- Answers natural-language questions through a read-only SQL agent

## Install

```bash
git clone <repo-url>
cd CLI - Autonomous-SQL-Agent-and-ETL-Pipeline
python -m venv .venv
# Windows
.venv\Scripts\Activate.ps1
pip install -e .
```

## Configure

Create a `.env` file for local settings and secrets.

Required for the agent:

- `OPENROUTER_API_KEY`

Optional settings are read through `src/invoice_agent/config.py`.

## Commands

Show the CLI:

```bash
invoice-agent --help
```

Generate sample invoices:

```bash
invoice-agent generate --count 5 --out data/invoices/
```

Extract headers:

```bash
invoice-agent extract headers --in data/invoices/ --out data/csv/invoice_headers.csv
```

Extract tables:

```bash
invoice-agent extract tables --in data/invoices/ --line-items-out data/csv/invoice_line_items.csv --summaries-out data/csv/invoice_summaries.csv
```

Load extracted CSVs into the database:

```bash
invoice-agent load --csv data/csv/ --db data/db.sqlite
```

Ask a question:

```bash
invoice-agent ask "which client has the highest total spend?" --db data/db.sqlite
```

Run the full pipeline:

```bash
invoice-agent pipeline --count 5 --csv data/csv/ --db data/db.sqlite
```

Check run status:

```bash
invoice-agent status --csv data/csv/ --db data/db.sqlite
```

## Project Layout

- `src/invoice_agent/generate.py` - invoice PDF generation
- `src/invoice_agent/extract/` - header and table extraction
- `src/invoice_agent/db/` - models, loader, and connection helpers
- `src/invoice_agent/agent/` - read-only SQL agent and prompt templates
- `tests/` - fixture and smoke tests
- `docs/` - architecture, phases, rules, and workflow notes

## Development Notes

- Keep CLI commands thin; the business logic lives in package modules.
- Extraction should keep going when one PDF fails.
- Loading is idempotent.
- The agent connection is read-only.

## Validation

```bash
pytest
```

If you change the pipeline, rerun the relevant command on real sample data as well.
