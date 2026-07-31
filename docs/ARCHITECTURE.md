# Architecture

## 1. Overview

`invoice-agent` is a CLI-first tool that turns invoice PDFs into structured,
queryable data. It has four layers:

```
┌─────────────┐   ┌──────────────┐   ┌────────────┐   ┌───────────────┐
│  Generation  │ → │  Extraction  │ → │  Storage   │ → │  Agent (Q&A)  │
│ (reportlab)  │   │ (pdfplumber, │   │ (SQLite /  │   │ (LangGraph    │
│              │   │  camelot)    │   │  Postgres) │   │  ReAct agent) │
└─────────────┘   └──────────────┘   └────────────┘   └───────────────┘
```

Each layer is a standalone Python module with a `run(...)` function, so it
can be called from the CLI, imported directly, or eventually wrapped by an
API/web layer without rewriting logic.

## 2. Components

### 2.1 Generation (`invoice_agent/generate.py`)
- Produces synthetic invoice PDFs via ReportLab for testing/demo purposes.
- Not part of the production data path — real invoices come from user
  uploads instead of this module once the tool is used for real data.

### 2.2 Extraction (`invoice_agent/extract/`)
- `headers.py` — pdfplumber-based extraction of invoice metadata (invoice
  number, date, seller/client info, tax IDs).
- `tables.py` — Camelot-based extraction of line items and summary tables,
  lattice mode with a stream-mode fallback.
- Each file is processed independently; a failure on one file must not stop
  the batch. Failures are logged and reported at the end of the run.

### 2.3 Storage (`invoice_agent/db/`)
- `models.py` — schema definitions (`invoices`, `line_items`, with a foreign
  key from `line_items.invoice_id → invoices.id`).
- `loader.py` — loads extracted CSVs into the database, idempotently
  (re-running does not create duplicate invoices).
- `session.py` — connection/session management. SQLite for local/dev use,
  Postgres-ready for multi-user/concurrent use.

### 2.4 Agent (`invoice_agent/agent/`)
- `react_agent.py` — LangGraph ReAct agent that translates natural-language
  questions into SQL, executes them, and returns an answer.
- `prompts.py` — system prompt, schema description, and few-shot examples
  given to the agent.
- The agent connects to the database using a **read-only role**. It must
  never hold write/delete permissions.

### 2.5 CLI (`invoice_agent/cli.py`)
- Thin layer. Commands parse arguments and call into the modules above.
  No business logic lives in the CLI file itself.

## 3. Data Flow

1. PDFs land in `data/invoices/` (generated or uploaded).
2. `extract headers` and `extract tables` produce CSVs in `data/csv/`.
3. `load` reads those CSVs and upserts rows into the database.
4. `ask` sends a question to the agent, which queries the database and
   returns a natural-language answer.
5. `status` reads the filesystem + database to summarize pipeline state.

## 4. Technology Choices

| Concern            | Choice                  | Why |
|---------------------|--------------------------|-----|
| CLI framework       | `typer`                 | Type-hint driven, less boilerplate than argparse |
| PDF generation      | `reportlab`              | Already in use, works well for synthetic data |
| Header extraction   | `pdfplumber`             | Reliable for text-layer PDFs |
| Table extraction    | `camelot-py[cv]`         | Best open-source option for ruled tables |
| Database (dev)      | `SQLite`                 | Zero-setup, fine for single-user prototype |
| Database (prod)     | `Postgres`               | Needed once there's concurrent access |
| ORM/schema          | `SQLAlchemy`             | Portable between SQLite and Postgres |
| Agent framework     | `LangGraph` + `LangChain`| Already in stack, good ReAct support |
| Config              | `pydantic-settings`      | Typed `.env` loading, validation |
| Output formatting   | `rich`                   | Progress bars, tables, readable CLI output |

## 5. Key Design Constraints

- **No hardcoded paths.** All paths come from `config.py`, sourced from
  `.env` or CLI flags.
- **No silent failures.** Every extraction failure is logged with the
  filename and reason; the batch continues.
- **Agent is read-only.** SQL execution from the agent uses a database role
  with `SELECT`-only privileges.
- **Idempotent loads.** Loading the same CSV twice must not duplicate rows.
- **Modules are importable.** Every module works when called directly in
  Python, not only through the CLI — this keeps a future API/web layer cheap
  to add.

## 6. Future Extension Points

- Swap `data/invoices/` (folder) for a file-upload endpoint without changing
  extraction logic.
- Wrap `agent.ask()` in a FastAPI endpoint for a web/API interface.
- Add a job queue (Celery/RQ) in front of extraction for async processing.
- Add multi-tenancy at the database layer (an `owner_id` column) if more
  than one user will use the tool.
