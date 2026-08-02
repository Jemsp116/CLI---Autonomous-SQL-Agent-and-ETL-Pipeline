# invoice-agent

CLI-first invoice extraction and analysis pipeline.

The project generates synthetic invoice PDFs, extracts structured data with a rules-first hybrid parser, loads the results into SQLite, and answers SQL-backed questions from the command line.

## Highlights

- Rules-first extraction for headers and tables
- Optional LLM fallback for malformed invoices
- Idempotent loading into SQLite
- Read-only SQL question answering
- Rich-based terminal UI for interactive Q&A

## Install

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .
```

## Configure

Create a `.env` file if you want local overrides. The main settings live in `src/invoice_agent/config.py`.

Required for LLM fallback and the SQL agent:

- `OPENROUTER_API_KEY`

## Common Commands

```bash
invoice-agent --help
invoice-agent generate --count 5 --out data/invoices/
invoice-agent extract headers --in data/invoices/ --out data/csv/invoice_headers.csv
invoice-agent extract tables --in data/invoices/ --line-items-out data/csv/invoice_line_items.csv --summaries-out data/csv/invoice_summaries.csv
invoice-agent extract headers --in data/invoices/ --no-llm-fallback
invoice-agent pipeline --count 5 --no-llm-fallback
invoice-agent load --csv data/csv/ --db data/db.sqlite
invoice-agent ask "which client has the highest total spend?" --db data/db.sqlite
invoice-agent status --csv data/csv/ --db data/db.sqlite
```

## Project Layout

- `src/invoice_agent/generate.py` generates sample invoices.
- `src/invoice_agent/extract/` contains rules-based extraction and the LLM fallback helper.
- `src/invoice_agent/db/` contains the schema and loader.
- `src/invoice_agent/agent/` contains the SQL question-answering agent.
- `src/invoice_agent/ui/` contains the terminal chat UI.
- `tests/` contains fixture and regression tests.
- `docs/` contains architecture, rules, and workflow notes.

## Notes

- Keep CLI commands thin; the work belongs in the package modules.
- Extraction continues per file when one invoice fails.
- The LLM fallback is off by default unless explicitly enabled.
- Generated artifacts belong outside the repository and should not be committed.
