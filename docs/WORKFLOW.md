# Development Workflow

## 1. First-Time Setup

```bash
git clone <repo-url>
cd invoice-agent
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e .
cp .env.example .env             # then fill in OPENROUTER_API_KEY etc.
invoice-agent --help             # confirm install worked
```

## 2. Everyday Commands

```bash
# Generate synthetic test invoices
invoice-agent generate --count 10 --out data/invoices/

# Extract headers and tables
invoice-agent extract headers --in data/invoices/ --out data/csv/headers.csv
invoice-agent extract tables --in data/invoices/ --line-items-out data/csv/invoice_line_items.csv --summaries-out data/csv/invoice_summaries.csv

# Load into the database
invoice-agent load --csv data/csv/ --db data/db.sqlite

# Ask a question
invoice-agent ask "which client has the highest total spend?"

# Run everything end-to-end
invoice-agent pipeline --count 10

# Check what's been processed
invoice-agent status
```

## 3. Working on a New Feature

1. Confirm the change fits the architecture and project rules.
2. Create a branch: `git checkout -b short-description`
3. Make the change in the relevant module (`generate.py`, `extract/*.py`,
   `db/*.py`, `agent/*.py`) — not in `cli.py` (see `RULES.md`).
4. Add/update a test if the change touches extraction, DB loading, or
   agent behavior.
5. Run the test suite:
   ```bash
   pytest
   ```
6. Run the affected command manually against real generated data to sanity
   check output, not just unit tests.
7. Update `ARCHITECTURE.md` if the change affects data flow or adds a
   component.
8. Commit with a message referencing the rule if relevant:
   `feat(extract): fallback to stream mode when lattice finds no tables`
9. Open a PR (or, for solo work, review your own diff before merging) —
   keep it scoped to one change.

## 4. Debugging Extraction Failures

1. Run `invoice-agent status` to see which files failed.
2. Check the log output for the filename + error reason (see `RULES.md`
   #5 — this should always be present).
3. Reproduce in isolation:
   ```python
   from invoice_agent.extract import headers
   headers.run(in_dir="data/invoices/", out="/tmp/debug.csv")
   ```
4. If it's a Camelot table-detection issue, try switching flavor
   (`lattice` → `stream`) on that specific file before changing the
   default for everything.
5. Add the problem file (or a redacted version) to `tests/fixtures/` if it
   represents a new edge case worth testing permanently.

## 5. Database Changes

1. Update `db/models.py`.
2. If using Alembic (post-Phase 4), generate a migration:
   ```bash
   alembic revision --autogenerate -m "add invoice status column"
   alembic upgrade head
   ```
3. Re-run `load` against a clean DB to confirm idempotency still holds.
4. Update `ARCHITECTURE.md`'s schema description if applicable.

## 6. Testing the Agent

1. Keep a running list of test questions and expected answer shapes (not
   exact wording — LLM output varies) in `tests/agent_questions.md`.
2. After any prompt or schema change, manually run the full list through
   `invoice-agent ask` and spot-check.
3. Check logs for the generated SQL, not just the final answer — a right
   answer from wrong SQL is still a bug waiting to happen.

## 7. Before Merging to Main

- [ ] `pytest` passes
- [ ] `invoice-agent pipeline --count 5` runs clean
- [ ] No hardcoded paths/keys introduced (`RULES.md` #3)
- [ ] `ARCHITECTURE.md` updated if scope changed
- [ ] `.env.example` updated if new config was added

## 8. Release Checklist (once past Phase 7)

- [ ] Bump version in `pyproject.toml`
- [ ] Update changelog
- [ ] Tag release: `git tag vX.Y.Z && git push --tags`
- [ ] Confirm fresh clone + install + `pipeline` still works
