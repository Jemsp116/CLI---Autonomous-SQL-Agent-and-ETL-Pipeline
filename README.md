# invoice-agent

CLI-first invoice extraction and analysis pipeline.

This project generates sample invoice PDFs, extracts structured data from them, loads the results into SQLite or Postgres, and answers SQL-backed questions from the command line.

## What It Does

- Generates deterministic sample invoice PDFs for demos and tests
- Extracts invoice headers with `pdfplumber`
- Extracts line items and summary tables with `camelot` (falls back to `pdfplumber` when Ghostscript is unavailable)
- Loads CSV output into a relational database with SQLAlchemy
- Answers natural-language questions through a read-only SQL agent

## Install

```bash
git clone https://github.com/Jemsp116/CLI---Autonomous-SQL-Agent-and-ETL-Pipeline.git
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

Optional settings are read through `src/invoice_agent/config.py`. Copy
`.env.example` to `.env` if you want local overrides.

## Quick Start

The fastest way to use the tool is to point it at a folder of PDFs:

```bash
invoice-agent /path/to/pdf_folder
```

This runs the full pipeline automatically:
1. Validates the folder and finds PDFs
2. Runs preflight checks (Ghostscript / OpenRouter API key)
3. Extracts invoice headers
4. Extracts tables (Camelot, with pdfplumber fallback)
5. Loads into a SQLite database inside the input folder
6. Prints a summary table
7. Drops you into an interactive Q&A session

Outputs are written inside the input folder by default:

```
pdf_folder/
  invoice_agent_output/
    invoice_headers.csv
    invoice_line_items.csv
    invoice_summaries.csv
  invoice_data.db
```

Override output location with `--out` and `--db`:

```bash
invoice-agent /path/to/pdf_folder --out /tmp/results --db /tmp/invoices.db
```

## Commands

Show the CLI:

```bash
invoice-agent --help
```

Process a folder (default):

```bash
invoice-agent /path/to/pdf_folder
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

## Ghostscript Note

Table extraction uses `camelot`, which requires Ghostscript.
If Ghostscript is not installed, the tool automatically falls back to `pdfplumber` table extraction so the pipeline can still run without extra system dependencies.

## Project Layout

- `src/invoice_agent/generate.py` - invoice PDF generation
- `src/invoice_agent/extract/` - header and table extraction
- `src/invoice_agent/db/` - models, loader, and connection helpers
- `src/invoice_agent/agent/` - read-only SQL agent and prompt templates
- `tests/` - fixture and smoke tests
- `docs/` - architecture, rules, and workflow notes

## Development Notes

- Keep CLI commands thin; the business logic lives in package modules.
- Extraction should keep going when one PDF fails.
- Loading is idempotent.
- The agent connection is read-only.
- Generated files under `data/`, local databases, virtual environments, and
  `.env` files are ignored by git.

## Validation

```bash
pytest
```

If you change the pipeline, rerun the relevant command on real sample data as well.
