# Architecture

## 1. Overview

`invoice-agent` is a CLI-first invoice pipeline with four stages:

```
Generation -> Extraction -> Storage -> Agent / Status
```

Each stage is implemented as an importable module with a `run(...)` function.

## 2. Components

### 2.1 Generation

`src/invoice_agent/generate.py` produces synthetic invoices for tests and demos.

### 2.2 Extraction

- `src/invoice_agent/extract/headers.py` extracts invoice metadata from the text layer.
- `src/invoice_agent/extract/tables.py` extracts line items and summary totals.
- `src/invoice_agent/extract/llm_fallback.py` provides the shared full-invoice LLM fallback used by both extraction stages.

Extraction is rules-first. The fallback only runs when the rules path fails or validation detects a mismatch, and the fallback result is still validated before it is accepted.

### 2.3 Storage

- `src/invoice_agent/db/models.py` defines the invoice and line-item schema.
- `src/invoice_agent/db/loader.py` loads extracted CSVs idempotently.
- `src/invoice_agent/db/session.py` creates the database engine and sessions.

### 2.4 Agent

- `src/invoice_agent/agent/react_agent.py` handles SQL question answering.
- `src/invoice_agent/agent/prompts.py` contains the SQL system prompt and the invoice extraction prompt.

The database connection used by the agent is read-only.

### 2.5 UI

`src/invoice_agent/ui/` contains the Rich-based chat interface used by `ask`.

### 2.6 CLI

`src/invoice_agent/cli.py` stays thin. It parses arguments and forwards them to module-level `run(...)` functions.

## 3. Data Flow

1. Invoice PDFs are generated or supplied by the user.
2. `extract headers` writes header CSV rows and a report JSON file.
3. `extract tables` writes line-item and summary CSVs and a report JSON file.
4. `load` imports the CSVs into SQLite.
5. `ask` queries the database through the read-only agent.
6. `status` summarizes the current pipeline state.

## 4. Configuration

Settings are loaded from `src/invoice_agent/config.py` via `pydantic-settings`.

Key options now include:

- `enable_llm_fallback`
- `extraction_model`
- `llm_fallback_max_retries`

## 5. Design Constraints

- Keep the CLI thin.
- Keep modules independently importable.
- Keep batch processing resilient to per-file failures.
- Validate extracted totals before trusting them.
- Keep generated output and local databases out of version control.
