# Project Rules

Non-negotiable constraints for this project.

## Code Organization

1. No logic in `cli.py`. CLI commands only parse arguments and forward them.
2. Every module must remain independently importable.
3. No hardcoded paths, API keys, or database URLs in code.

## Data Handling

4. One bad file must not kill a batch.
5. Every extraction failure must log the filename and reason.
6. Loads must remain idempotent.
7. Validate extracted totals before trusting them.

## Agent / SQL Safety

8. The agent database connection must remain read-only.
9. No raw string interpolation into SQL.
10. Agent reasoning and SQL generation should remain observable in logs.

## Testing

11. Any extraction logic change must include or update a fixture-backed test.
12. The standard test suite must stay free of live API dependencies.

## Git / Change Management

13. Do not commit `.env`, generated PDFs, CSVs, or local databases.
14. Keep changes focused on one logical area.
15. Update `ARCHITECTURE.md` when the data flow or component set changes.

## Scope Discipline

16. Keep the workflow stable before expanding features.
17. New dependencies need a one-line justification.
