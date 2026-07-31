# Project Rules

Non-negotiable constraints for this project. If a change conflicts with one
of these, the change is wrong â€” not the rule.

## Code Organization

1. **No logic in `cli.py`.** CLI commands only parse args and call a
   `run(...)` function from another module. If you can't unit test it
   without invoking the CLI, it's in the wrong place.
2. **Every module is independently importable.** No module should assume
   it's only ever called from `cli.py`. This keeps a future web/API layer
   cheap to add.
3. **No hardcoded paths, API keys, or DB URLs anywhere in code.** Everything
   comes from `config.py`, which reads `.env`. If you're tempted to
   hardcode a path "just for now," add it to `.env.example` instead.

## Data Handling

4. **One bad file must not kill a batch.** Extraction, loading, and any
   batch operation must catch per-item errors, log them, and continue.
5. **All extraction failures are logged with filename + reason.** Silent
   failures (a file that just doesn't show up in output, with no log line)
   are treated as bugs.
6. **Loads are idempotent.** Running `load` twice on the same input must
   not create duplicate rows. Enforce this with a unique constraint
   (`invoice_number`), not just application logic.
7. **Validate before trusting extracted data.** Where possible, reconcile
   line item totals against summary totals and flag mismatches rather than
   loading unchecked numbers.

## Agent / SQL Safety

8. **The agent's database connection is read-only, always.** No exceptions,
   including in development. Use a dedicated DB role with `SELECT` only.
9. **No raw string interpolation into SQL.** All agent-generated queries go
   through parameterized execution or a query-validation step before
   running.
10. **Agent reasoning/tool calls are logged.** If a query returns a wrong
    answer, you need to be able to see what SQL was generated and why.

## Testing

11. **New extraction logic ships with a fixture test.** If you change how
    headers or tables are parsed, add or update a test using a fixed sample
    PDF with known expected values â€” don't rely on eyeballing the CSV.
12. **The full pipeline must run on 5 invoices in CI without network/API
    dependencies** (mock the LLM call in the agent test, or skip it in CI
    and test it separately).

## Git / Change Management

13. **Don't commit `.env`, `data/`, or generated PDFs/CSVs.** Keep
    `.gitignore` current; only `tests/fixtures/` sample PDFs are committed.
14. **Keep each commit/PR focused.** Don't mix unrelated cleanup, database,
    extraction, and agent changes in one change.
15. **Update `ARCHITECTURE.md` in the same PR** if a change alters the data
    flow, adds a component, or changes a technology choice.

## Scope Discipline

16. **Keep the workflow stable before expanding features.** This project
    stalls if the agent gets attention before the database and extraction
    path are stable.
17. **New dependencies need a one-line justification** in the PR/commit
    message â€” this project's dependency list should stay intentional, not
    accumulated.
