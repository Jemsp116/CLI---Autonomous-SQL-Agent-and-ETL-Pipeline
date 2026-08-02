# Invoice Agent — Project Documentation

## 1. Project Overview

Invoice Agent is a CLI-first tool for turning invoice PDFs into structured data and answering SQL-backed questions over the loaded results. The current extraction path is rules-first, with an optional LLM fallback for malformed invoices.

Each major stage is a standalone Python module with a `run(...)` entry point so it can be called from the CLI, imported directly, or reused by tests and future integrations.

## 2. Repository Layout

```
CLI - Autonomous-SQL-Agent-and-ETL-Pipeline/
├── src/invoice_agent/
│   ├── config.py
│   ├── cli.py
│   ├── generate.py
│   ├── preflight.py
│   ├── status.py
│   ├── pipeline.py
│   ├── folder_pipeline.py
│   ├── ask.py
│   ├── load.py
│   ├── extract/
│   │   ├── headers.py
│   │   ├── tables.py
│   │   └── llm_fallback.py
│   ├── db/
│   ├── agent/
│   └── ui/
├── tests/
├── docs/
├── README.md
└── pyproject.toml
```

## 3. Data Flow

1. PDFs are generated or supplied by the user.
2. `extract headers` and `extract tables` write CSV reports.
3. `load` imports those CSVs into SQLite.
4. `ask` queries the database through a read-only SQL agent.
5. `status` summarizes the current inputs, CSVs, and database state.

## 4. Main Modules

### Generation

`src/invoice_agent/generate.py` creates deterministic sample invoices for tests and demos.

### Extraction

`src/invoice_agent/extract/headers.py` parses invoice metadata from the PDF text layer.

`src/invoice_agent/extract/tables.py` parses item rows and summary totals, validates totals, and can fall back to the shared LLM helper when rules output is missing or inconsistent.

`src/invoice_agent/extract/llm_fallback.py` wraps the shared full-invoice LLM extraction call and caches results per PDF path in-process.

### Storage

`src/invoice_agent/db/` defines the schema and the idempotent loader.

### Agent

`src/invoice_agent/agent/` contains the read-only SQL question-answering agent and prompt templates.

### UI

`src/invoice_agent/ui/` contains the Rich-based terminal chat interface.

## 5. Hybrid Extraction Behavior

- Rules run first.
- The LLM fallback is only used when rules fail or totals mismatch.
- Fallback remains off unless enabled by config or CLI.
- Fallback results are still validated before being accepted.

## 6. CLI Entry Points

- `invoice-agent generate`
- `invoice-agent extract headers`
- `invoice-agent extract tables`
- `invoice-agent load`
- `invoice-agent ask`
- `invoice-agent pipeline`
- `invoice-agent status`

## 7. Project Rules to Preserve

- Keep the CLI thin.
- Keep modules independently importable.
- Preserve batch resilience and per-file error handling.
- Keep the agent read-only.
- Keep generated data out of version control.

## 8. Testing Notes

- Fixture tests cover the rules-only extraction path.
- LLM fallback is tested with a mocked `ChatOpenAI.invoke` call.
- No live API call should be required for the standard test suite.
| Function | Purpose |
|----------|---------|
| `build_invoice(invoice_no, out_dir)` | Creates a single PDF invoice with randomized items, client, and date |
| `run(out_dir, zip_path, start_invoice_no, end_invoice_no, spot_check_invoice_nos)` | Batch-generates invoices and creates a ZIP archive |

**Constants:**
- `PRODUCTS` — 38 product names with price ranges
- `CLIENTS` — 40 client tuples (name, address, city, state, pincode)
- `SELLER_NAME`, `SELLER_ADDR1`, `SELLER_ADDR2`, `SELLER_TAX`, `SELLER_GSTIN`
- `VAT_RATE = 0.10`, `START_DATE = 2023-04-07`, `END_DATE = 2024-04-07`

**PDF Layout:**
- Page 1: Invoice number, date, Seller/Client blocks, ITEMS table, SUMMARY table
- ITEMS table columns: No., Description, Qty, UM, Net Price, Net Worth, VAT %, Gross Worth
- SUMMARY table: VAT %, Net Worth, VAT, Gross Worth + Total row

**Dependencies:** `reportlab`, `pdfplumber` (for spot-checking), `random`, `zipfile`

---

### 4.2 Extraction Layer (`extract/`)

#### 4.2.1 `headers.py`

**Purpose:** Extracts invoice metadata from PDF text layer using pdfplumber.

**Key Functions:**
| Function | Purpose |
|----------|---------|
| `group_words_by_row(words, y_tolerance)` | Groups pdfplumber words into horizontal rows |
| `row_text(row)` | Concatenates words in a row into a single string |
| `split_row_by_column(row, threshold)` | Splits a row into left/right columns at x=240 |
| `extract_header(pdf_path)` | Main extraction — returns dict with invoice fields |
| `_parse_seller_client_block(rows, result)` | Parses Seller/Client two-column layout |
| `_parse_alternative_header(rows, result)` | Fallback for TO: block layout |
| `run(pdf_dir, output_csv, report_json, verbose, progress_callback)` | Batch extraction with progress reporting |

**Extracted Fields:**
`invoice_no`, `date_of_issue`, `seller_name`, `seller_address`, `seller_tax_id`, `seller_gstin`, `client_name`, `client_address`, `client_tax_id`

**Two Parsing Strategies:**
1. **Primary:** Looks for "Seller:" and "Client:" on the same line, then splits subsequent rows into two columns
2. **Fallback:** Looks for "TO:" block followed by COMMENTS/OR/SPECIAL/INSTRUCTIONS/P.O./TERMS boundary

**Invoice Number Extraction:**
- Primary: `Invoice no: (\d+)`
- Alternative: `INVOICE\s*#\s*(\S+)` or `Invoice no:\s*(\d+)`

#### 4.2.2 `tables.py`

**Purpose:** Extracts line items and summary tables from PDFs using pdfplumber.

**Key Functions:**
| Function | Purpose |
|----------|---------|
| `clean(val)` | Normalize whitespace |
| `parse_amount(val)` | Convert "1,234.56" → 1234.56 |
| `invoice_no_from_path(fpath)` | Extract invoice number from filename (e.g., `invoice_51109301.pdf` → `51109301`) |
| `invoice_no_from_pdf(pdf_path)` | Fallback: extract invoice number from PDF text |
| `_normalize_header(value)` | Lowercase, strip whitespace for column matching |
| `_column_map(df)` | Build {header_name: column_index} dict from first row |
| `classify_table(df)` | Identify table type: "items" or "summary" |
| `parse_items_table(df, invoice_no)` | Extract line items with header-based column mapping |
| `parse_summary_table(df, invoice_no)` | Extract totals (net worth, VAT, gross worth) |
| `extract_tables(pdf_path, verbose)` | Main extraction using pdfplumber |
| `validate_totals(line_items, summary)` | Reconcile line item sums against summary totals |
| `run(pdf_dir, line_items_csv, summaries_csv, report_json, verbose, progress_callback)` | Batch extraction |

**Column Mapping Strategy:**
Instead of fixed indices, the parser maps columns by normalized header text:
- Items table headers: `no.`, `description`, `qty`, `um`, `net price`, `net worth`, `vat %`, `gross worth`
- Summary table headers: `vat %`, `net worth`, `vat`, `gross worth`

**Validation:**
Compares `SUM(line_items.net_worth)` against `summary.total_net_worth`, etc. Flags mismatches but does not block loading.

---

### 4.3 Storage Layer (`db/`)

#### 4.3.1 `models.py`

**SQLAlchemy ORM Models:**

```
Table: invoices
├── id (PK, autoincrement)
├── invoice_number (VARCHAR, UNIQUE, INDEXED)
├── date_of_issue (VARCHAR, nullable)
├── seller_name (VARCHAR, nullable)
├── seller_address (VARCHAR, nullable)
├── seller_tax_id (VARCHAR, nullable)
├── seller_gstin (VARCHAR, nullable)
├── client_name (VARCHAR, nullable)
├── client_address (VARCHAR, nullable)
├── client_tax_id (VARCHAR, nullable)
└── line_items (1:N relationship)

Table: line_items
├── id (PK, autoincrement)
├── invoice_id (FK → invoices.id, CASCADE)
├── item_no (INTEGER, nullable)
├── description (VARCHAR, nullable)
├── qty (FLOAT, nullable)
├── unit (VARCHAR, nullable)
├── net_price (FLOAT, nullable)
├── net_worth (FLOAT, nullable)
├── vat_pct (VARCHAR, nullable)
├── gross_worth (FLOAT, nullable)
└── UNIQUE(invoice_id, item_no)
```

#### 4.3.2 `loader.py`

**Purpose:** Idempotently loads extracted CSVs into the database.

**Key Functions:**
| Function | Purpose |
|----------|---------|
| `normalize_columns(df)` | Strip/lowercase column names |
| `_read_csv(path)` | Read CSV with validation |
| `_to_text(value)` | Safe text conversion |
| `_to_int(value)` | Safe integer conversion |
| `_to_float(value)` | Safe float conversion |
| `run(csv_dir, db_path, verbose)` | Main load function |

**Idempotency Mechanism:**
1. Load all existing invoices into `existing_invoices` dict keyed by `invoice_number`
2. Load all existing line items into `existing_line_item_keys` set of `(invoice_id, item_no)` tuples
3. For each header record: skip if `invoice_number` already exists
4. For each line item: skip if `(invoice_id, item_no)` already exists
5. If `item_no` is missing, assign sequential `1, 2, 3...`

#### 4.3.3 `session.py`

**Purpose:** Database connection management with read-only support.

**Key Functions:**
| Function | Purpose |
|----------|---------|
| `database_url(db_path)` | Convert file path to SQLAlchemy URL |
| `create_db_engine(db_path)` | Read-write engine with SQLite pragmas |
| `create_read_only_engine(db_path_or_url)` | Read-only engine (SQLite: `mode=ro`, Postgres: `SET default_transaction_read_only = on`) |
| `create_session_factory(db_path)` | Session factory for read-write operations |
| `session_scope(db_path)` | Context manager for session lifecycle |

**Read-Only Guarantee (Rule #8):**
- SQLite: Uses `sqlite3.connect(f"file:{path}?mode=ro", uri=True)` — OS-level read-only
- Postgres: Executes `SET default_transaction_read_only = on` on connect

---

### 4.4 Agent Layer (`agent/`)

#### 4.4.1 `prompts.py`

**Purpose:** Defines the system prompt and few-shot examples for the LLM.

**Components:**
| Constant | Purpose |
|----------|---------|
| `SCHEMA_DESCRIPTION` | Database schema, relationships, query rules |
| `FEW_SHOT_EXAMPLES` | 4 example Q&A pairs with SQL |
| `SYSTEM_PROMPT_TEMPLATE` | Full prompt template with format rules |
| `build_system_prompt(table_info)` | Renders template with live schema info |

**Query Rules Embedded in Prompt:**
- SELECT-only SQL
- Read-only database
- Join through `invoices.id = line_items.invoice_id`
- Use `gross_worth` for VAT-inclusive, `net_worth` for pre-VAT
- Aggregate functions: `SUM`, `COUNT`, `GROUP BY`, `ORDER BY`, `LIMIT`

#### 4.4.2 `react_agent.py`

**Purpose:** LangChain ReAct agent that translates natural language to SQL, executes it, and summarizes results.

**Key Classes/Functions:**
| Name | Purpose |
|------|---------|
| `SqlPlan` | Dataclass holding `reasoning_summary` and `sql_query` |
| `_require_openrouter_key()` | Validates API key exists |
| `_create_llm(streaming)` | Creates ChatOpenAI instance configured for OpenRouter |
| `_parse_plan(payload)` | Extracts JSON plan from LLM response |
| `_ensure_select_only(sql)` | Validates SQL is SELECT-only (Rule #9) |
| `_format_rows(rows)` | JSON-serializes query results |
| `_summarize_answer(question, sql, rows, on_token)` | LLM summarization with streaming support |
| `ask(question, db_path, max_attempts, on_thinking, on_token)` | Main entry point with retry logic |

**Agent Flow:**
```
1. User question
2. Build system prompt with schema + few-shots
3. LLM generates {reasoning_summary, sql_query}
4. Validate: SELECT-only check
5. Execute SQL on read-only engine
6. Summarize results via LLM (streaming)
7. Return answer
```

**Retry Logic:** Up to 3 attempts. If SQL fails, error context is appended and LLM revises.

**Streaming Support:**
- `_summarize_answer()` uses `llm.stream()` for token-by-token delivery
- `on_token` callback enables UI to render tokens in real-time
- `on_thinking` callback signals when LLM is generating the plan

**Safety (Rules #8, #9):**
- Database engine is read-only (SQLite `mode=ro`, Postgres `SET default_transaction_read_only = on`)
- SQL validated via `_ensure_select_only()` before execution
- SQL executed via SQLAlchemy `text()` parameterized queries

---

### 4.5 Preflight Layer (`preflight.py`)

**Purpose:** Validates environment before pipeline execution.

**Key Functions:**
| Function | Purpose |
|----------|---------|
| `is_plausible_openrouter_key(value)` | Validates key format (starts with `sk-or-` or `sk-`, length ≥ 20, no spaces) |
| `ensure_openrouter_api_key(prompt_func)` | Checks for existing key, prompts user if missing, saves to `.env` |

**Behavior:**
1. Check `.env` for `OPENROUTER_API_KEY`
2. If found and valid → return `ApiKeyResult(key_found=True, persisted=True)`
3. If missing → prompt user with instructions
4. Validate input → save to `.env` (create from `.env.example` if needed)
5. On write failure → return session-only key with warning

---

### 4.6 Pipeline Layer

#### 4.6.1 `folder_pipeline.py`

**Purpose:** Default end-to-end pipeline triggered by `invoice-agent /path/to/folder`.

**Flow:**
```
1. Validate folder exists + contains PDFs
2. Preflight checks (API key)
3. Extract headers (pdfplumber, silent mode)
4. Extract tables (pdfplumber, silent mode)
5. Load into database (idempotent)
6. Print summary table
7. If succeeded > 0: launch interactive Q&A
   Else: print skip message
8. Print hint line
```

**Output Location Rules:**
- If no `--out`/`--db` specified: outputs go inside the input folder
  - `{pdf_folder}/invoice_agent_output/` (CSVs)
  - `{pdf_folder}/invoice_data.db`
- If `--out` specified: CSVs go to `{out}/`, DB goes to `{out}/invoice_data.db`
- If `--db` specified: DB goes to that path, CSVs to `{db.parent}/`

#### 4.6.2 `pipeline.py`

**Purpose:** Alternative pipeline that generates PDFs first, then extracts and loads.

**Flow:**
```
1. Generate sample invoices (reportlab)
2. Create ZIP archive
3. Spot-check 3 invoices with pdfplumber
4. Extract headers
5. Extract tables
6. Load database
7. Optional: ask question
8. Print status
```

---

### 4.7 UI Layer (`ui/`)

#### 4.7.1 `chat.py`

**Purpose:** Main chat loop with raw terminal input handling.

**Key Features:**
- Raw keyboard input via `msvcrt.getwch()` (Windows) or `os.read(0, 1)` (Unix)
- Non-blocking LLM calls using `threading.Thread`
- History navigation with Up/Down arrows
- Clean exit on Ctrl+C

**State Machine:**
```
READY → (Enter pressed) → LOCKED + THINKING → STREAMING → READY
                                      ↑                    |
                                      └── (error) ──────────┘
```

**Key Functions:**
| Function | Purpose |
|----------|---------|
| `run(initial_question, db_path, console)` | Main entry point |
| `_get_key()` | Raw keyboard input with special key handling |
| `_question_history_handler(key, buffer, history, history_index)` | Up/Down arrow history |
| `submit_question(question, live)` | Lock input, spawn worker thread, animate thinking |
| `worker()` | Background thread calling `ask_question()` |
| `on_thinking()` | Callback when LLM starts generating plan |
| `on_token(token)` | Callback for each streaming token |

#### 4.7.2 `renderer.py`

**Purpose:** Assembles the three-panel Rich layout.

**Key Components:**
| Component | Purpose |
|-----------|---------|
| `ChatState` | Dataclass holding all UI state |
| `build_layout(state, console)` | Creates Rich Layout with header/conversation/input |

**Layout Structure:**
```
Layout (root)
├── header (size=4)
├── conversation (ratio=1, auto-sized)
└── input (size=6)
```

#### 4.7.3 `header.py`

**Purpose:** Renders the fixed top panel.

**Output:**
```
╭────────────────────────────────────────────────────╮
│ Invoice Agent                              Ready ●  │
│ Database : invoice_data.db                         │
│ PDFs     : 120                                     │
╰────────────────────────────────────────────────────╯
```

**Function:** `render_header(status, db_name, pdf_count) → Panel`

#### 4.7.4 `conversation.py`

**Purpose:** Renders scrollable message history with thinking indicator.

**Key Functions:**
| Function | Purpose |
|----------|---------|
| `_wrapped_line_count(content, width)` | Calculate display height of text |
| `_message_height(content, width)` | Total height including padding |
| `_select_visible_messages(messages, width, max_height)` | Scroll to show newest messages |
| `_message_renderable(role, content)` | Format single message block |
| `render_conversation(messages, width, max_height, thinking, draft_assistant)` | Main render function |

**Message Format:**
```
User

Show invoices from Amazon.

────────────────────────

Assistant

I found 17 invoices from Amazon totaling ₹143,820.
```

**Thinking Indicator:**
```
Assistant

⠋ Thinking...
```

#### 4.7.5 `input_box.py`

**Purpose:** Renders the fixed bottom input area.

**States:**
1. **Empty + Unlocked:** Shows placeholder + example prompts
2. **Typing:** Shows `> {buffer}█` with cursor
3. **Locked/Thinking:** Shows `{buffer or "Thinking..."}` dimmed

**Function:** `render_input_box(buffer, focused, locked, placeholder) → Panel`

---

### 4.8 CLI Layer (`cli.py`)

**Purpose:** Thin command parser. No business logic.

**Commands:**
| Command | Default Args | Calls |
|---------|-------------|-------|
| `process` (default) | `pdf_folder` positional | `folder_pipeline_run()` |
| `generate` | `count=50, out=data/invoices, zip=data/invoices.zip` | `generate_run()` |
| `extract headers` | `in=data/invoices, out=data/csv/invoice_headers.csv` | `extract_headers_run()` |
| `extract tables` | `in=data/invoices, line-items-out=..., summaries-out=...` | `extract_tables_run()` |
| `load` | `csv=data/csv, db=data/db.sqlite` | `load_run()` |
| `ask` | `question` positional, `db=data/db.sqlite` | `ask_run()` |
| `pipeline` | `count=50, out=..., csv=..., db=...` | `pipeline_run()` |
| `status` | `csv=data/csv, db=data/db.sqlite, invoices_dir=data/invoices` | `status_run()` |

**Smart Routing:** If first argument is an existing directory, automatically routes to `process` command.

---

### 4.9 `ask.py`

**Purpose:** Bridge between CLI and agent/UI layers.

**Functions:**
| Function | Purpose |
|----------|---------|
| `run(question, db_path)` | Single-question mode (CLI `ask` command) |
| `run_interactive(initial_question, db_path, console)` | Launches full-screen chat UI |

---

## 5. Data Flow Diagrams

### 5.1 Folder Pipeline (Default)

```
┌─────────────────────────────────────────────────────────────────────┐
│                    invoice-agent /path/to/folder                     │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│ folder_pipeline.py                                                 │
│                                                                     │
│  1. _validate_pdf_folder()                                          │
│     - Check folder exists                                           │
│     - Check ≥1 .pdf file                                            │
│                                                                     │
│  2. _run_preflight()                                                │
│     - ensure_openrouter_api_key()                                   │
│                                                                     │
│  3. headers_run()                                                   │
│     └─> extract/headers.py                                          │
│         └─> pdfplumber → invoice_headers.csv                        │
│                                                                     │
│  4. tables_run()                                                    │
│     └─> extract/tables.py                                           │
│         └─> pdfplumber → invoice_line_items.csv                     │
│                      → invoice_summaries.csv                         │
│                                                                     │
│  5. load_run()                                                      │
│     └─> db/loader.py                                                │
│         └─> SQLite database (idempotent)                            │
│                                                                     │
│  6. _print_summary()                                                │
│                                                                     │
│  7. run_interactive() [if succeeded > 0]                            │
│     └─> ui/chat.py (full-screen chat)                               │
└─────────────────────────────────────────────────────────────────────┘
```

### 5.2 Agent Query Flow

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  User    │────▶│  LLM     │────▶│  Valid.  │────▶│  Execute │
│  Query   │     │  Plan    │     │  SELECT  │     │  SQL     │
└──────────┘     └──────────┘     └──────────┘     └────┬─────┘
                                                         │
┌──────────┐     ┌──────────┐     ┌──────────┐          │
│  Answer  │◀────│  LLM     │◀────│  Format  │◀─────────┘
│  Display │     │  Summary │     │  Rows    │
└──────────┘     └──────────┘     └──────────┘

Streaming path:
  on_thinking() → "Thinking..."
  on_token() → stream tokens to conversation area
```

### 5.3 Database Schema

```
┌───────────────────────────────────────────────────────────────────┐
│ invoices                                                         │
├───────────────────────────────────────────────────────────────────┤
│ id (PK)                                                          │
│ invoice_number (UNIQUE)                                          │
│ date_of_issue                                                    │
│ seller_name                                                      │
│ seller_address                                                   │
│ seller_tax_id                                                    │
│ seller_gstin                                                     │
│ client_name                                                      │
│ client_address                                                   │
│ client_tax_id                                                    │
└───────────────────────────┬───────────────────────────────────────┘
                            │ 1:N
                            ▼
┌───────────────────────────────────────────────────────────────────┐
│ line_items                                                       │
├───────────────────────────────────────────────────────────────────┤
│ id (PK)                                                          │
│ invoice_id (FK → invoices.id)                                    │
│ item_no (UNIQUE with invoice_id)                                 │
│ description                                                     │
│ qty                                                              │
│ unit                                                             │
│ net_price                                                        │
│ net_worth                                                        │
│ vat_pct                                                          │
│ gross_worth                                                      │
└───────────────────────────────────────────────────────────────────┘
```

---

## 6. Dependencies (`pyproject.toml`)

| Package | Version | Purpose |
|---------|---------|---------|
| `typer` | ≥0.12 | CLI framework |
| `rich` | ≥13.0 | Terminal UI (panels, progress, live display) |
| `pdfplumber` | ≥0.11 | PDF text/table extraction |
| `pandas` | ≥2.0 | CSV processing, data manipulation |
| `sqlalchemy` | ≥2.0 | ORM and database connectivity |
| `reportlab` | ≥4.0 | Synthetic PDF generation |
| `pydantic-settings` | ≥2.0 | `.env` configuration loading |
| `langchain` | ≥0.3 | Agent orchestration |
| `langchain-community` | ≥0.3 | SQLDatabase utility |
| `langchain-openai` | ≥0.3 | ChatOpenAI (OpenRouter-compatible) |

**Note:** `camelot-py` and `ghostscript` were removed. Table extraction uses `pdfplumber` exclusively.

---

## 7. Configuration (`config.py`)

**Settings Class (Pydantic BaseSettings):**

| Setting | Default | Purpose |
|---------|---------|---------|
| `invoice_output_dir` | `data/invoices` | Generated PDF output directory |
| `invoice_zip_path` | `data/invoices.zip` | ZIP archive path |
| `invoice_start_no` | `51109301` | Starting invoice number |
| `invoice_end_no` | `51109351` | Ending invoice number (exclusive) |
| `spot_check_invoice_nos` | `(51109301, 51109325, 51109350)` | Invoices to spot-check |
| `headers_input_dir` | `data/invoices` | PDF input for header extraction |
| `headers_output_csv` | `data/csv/invoice_headers.csv` | Headers output path |
| `headers_report_json` | `data/csv/invoice_headers_report.json` | Headers report path |
| `tables_input_dir` | `data/invoices` | PDF input for table extraction |
| `line_items_csv` | `data/csv/invoice_line_items.csv` | Line items output |
| `summaries_csv` | `data/csv/invoice_summaries.csv` | Summaries output |
| `tables_report_json` | `data/csv/invoice_tables_report.json` | Tables report |
| `demo_db_path` | `data/db.sqlite` | Default database path |
| `openrouter_api_key` | `None` | LLM API key |
| `openrouter_api_base` | `https://openrouter.ai/api/v1` | API base URL |
| `agent_model` | `openai/gpt-oss-120b` | LLM model |

**Cached:** `get_settings()` uses `@lru_cache(maxsize=1)` for singleton access.

---

## 8. Test Coverage

| Test File | Purpose |
|-----------|---------|
| `test_pipeline_smoke.py` | Full pipeline with 5 generated invoices |
| `test_extraction_fixtures.py` | Headers + tables extraction on fixture PDFs |
| `test_loader_idempotent.py` | Loading same CSV twice doesn't duplicate |
| `test_generate_spot_checks.py` | PDF generation spot-checks |
| `test_folder_pipeline.py` | Folder pipeline smoke + CLI routing |
| `test_ask_interactive.py` | Q&A exit/quit/Ctrl+C/ask/skip/hint |
| `test_ask_missing_key.py` | Missing API key error handling |
| `test_config_defaults.py` | Config defaults validation |
| `test_chat_ui_rendering.py` | UI component rendering |

**Total: 9 test files, 15 test functions**

---

## 9. Key Design Patterns

### 9.1 Thin CLI
Every CLI command in `cli.py` only parses arguments and calls a `run()` function from another module. No business logic lives in the CLI.

### 9.2 Independent Modules
Every module (`generate.py`, `extract/headers.py`, `extract/tables.py`, `db/loader.py`, `agent/react_agent.py`) can be imported and called directly without the CLI.

### 9.3 Idempotent Loading
The loader checks for existing invoices and line items before inserting. Re-running `load` on the same CSV never creates duplicates.

### 9.4 Per-File Error Handling
Extraction failures are logged per-file with filename and reason. The batch continues processing remaining files.

### 9.5 Read-Only Agent
The agent's database connection uses SQLite `mode=ro` or Postgres `SET default_transaction_read_only = on`. The agent can never write to the database.

### 9.6 Callback-Based UI
The agent exposes `on_thinking` and `on_token` callbacks. The UI consumes these to render thinking indicators and stream tokens without blocking.

---

## 10. Usage Examples

### 10.1 Generate Sample Data
```bash
invoice-agent generate --count 10 --out data/invoices/
```

### 10.2 Process a Folder (Default)
```bash
invoice-agent C:\path\to\pdf_folder
# Outputs go inside the folder by default
```

### 10.3 Extract Headers
```bash
invoice-agent extract headers --in data/invoices/ --out data/csv/invoice_headers.csv
```

### 10.4 Extract Tables
```bash
invoice-agent extract tables \
  --in data/invoices/ \
  --line-items-out data/csv/invoice_line_items.csv \
  --summaries-out data/csv/invoice_summaries.csv
```

### 10.5 Load into Database
```bash
invoice-agent load --csv data/csv/ --db data/db.sqlite
```

### 10.6 Ask a Question
```bash
invoice-agent ask "Which client has the highest total spend?" --db data/db.sqlite
```

### 10.7 Full Pipeline
```bash
invoice-agent pipeline --count 10
```

### 10.8 Check Status
```bash
invoice-agent status
```

---

## 11. Project Rules Summary

1. **No logic in `cli.py`** — CLI only parses args and calls `run()`
2. **Every module is independently importable**
3. **No hardcoded paths/keys** — everything from `config.py`/`.env`
4. **Per-file error handling** — failures logged with filename + reason
5. **Idempotent loads** — unique constraint on `(invoice_id, item_no)`
6. **Validate before trusting** — totals reconciliation
7. **Agent is read-only** — `mode=ro` / `SET default_transaction_read_only`
8. **No raw SQL interpolation** — parameterized execution + validation
9. **Agent reasoning logged** — SQL + reasoning summary in logs
10. **New extraction logic ships with fixture test**
11. **Full pipeline runs on 5 invoices in CI**
12. **Don't commit `.env`, `data/`, generated files**
13. **Keep commits focused**
14. **Update `ARCHITECTURE.md` if data flow changes**
15. **Keep workflow stable before expanding features**
16. **New dependencies need justification**

---

*Document generated from source scan. For architecture details, see `docs/ARCHITECTURE.md`. For development workflow, see `docs/WORKFLOW.md`. For non-negotiable constraints, see `docs/RULES.md`.*
