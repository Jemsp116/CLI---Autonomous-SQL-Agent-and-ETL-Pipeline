from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path

from langchain_community.utilities.sql_database import SQLDatabase
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from rich.console import Console
from rich.logging import RichHandler
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from invoice_agent.config import get_settings
from invoice_agent.db.session import create_read_only_engine

from .prompts import build_system_prompt

console = Console()
logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(message)s", handlers=[RichHandler(console=console, show_time=False, show_path=False)])
logger.setLevel(logging.INFO)


class SqlPlan:
    def __init__(self, reasoning_summary: str, sql_query: str) -> None:
        self.reasoning_summary = reasoning_summary.strip()
        self.sql_query = sql_query.strip()


def _require_openrouter_key() -> str:
    settings = get_settings()
    api_key = settings.openrouter_api_key or os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY environment variable is not set.")
    return api_key


def _create_llm():
    settings = get_settings()
    return ChatOpenAI(
        model=settings.agent_model,
        openai_api_key=_require_openrouter_key(),
        openai_api_base=settings.openrouter_api_base,
        temperature=0,
    )


def _parse_plan(payload: str) -> SqlPlan:
    text_payload = payload.strip()
    if text_payload.startswith("```"):
        text_payload = re.sub(r"^```(?:json)?\s*", "", text_payload)
        text_payload = re.sub(r"\s*```$", "", text_payload)

    data = json.loads(text_payload)
    return SqlPlan(
        reasoning_summary=str(data["reasoning_summary"]),
        sql_query=str(data["sql_query"]),
    )


def _ensure_select_only(sql_query: str) -> None:
    normalized = sql_query.strip().lower()
    if not (normalized.startswith("select") or normalized.startswith("with")):
        raise ValueError("Generated SQL must be SELECT-only.")


def _format_rows(rows: list[dict[str, object]]) -> str:
    return json.dumps(rows, indent=2, default=str)


def _summarize_answer(question: str, sql_query: str, rows: list[dict[str, object]]) -> str:
    llm = _create_llm()
    summary_prompt = [
        SystemMessage(
            content=(
                "You answer invoice database questions concisely from SQL results. "
                "Do not invent data. If the result set is empty, say so directly."
            )
        ),
        HumanMessage(
            content=(
                f"Question: {question}\n\nSQL: {sql_query}\n\nResult rows:\n{_format_rows(rows)}\n\n"
                "Write a short answer using only the result rows."
            )
        ),
    ]
    return llm.invoke(summary_prompt).content.strip()


def ask(question: str, db_path: str | Path | None = None, max_attempts: int = 3) -> str:
    settings = get_settings()
    resolved_db_path = Path(db_path or settings.demo_db_path)

    if not resolved_db_path.exists():
        raise FileNotFoundError(f"Database not found: {resolved_db_path}")

    engine = create_read_only_engine(resolved_db_path)
    sql_db = SQLDatabase(engine=engine)
    system_prompt = build_system_prompt(sql_db.get_table_info())
    llm = _create_llm()

    error_context = ""
    last_error: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        prompt = (
            f"Question: {question}\n"
            f"{error_context}"
            "Return JSON with keys reasoning_summary and sql_query."
        )
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=prompt),
        ])
        plan = _parse_plan(response.content)
        _ensure_select_only(plan.sql_query)

        logger.info("Attempt %s reasoning summary: %s", attempt, plan.reasoning_summary)
        logger.info("Attempt %s generated SQL: %s", attempt, plan.sql_query)

        try:
            with engine.connect() as connection:
                result = connection.execute(text(plan.sql_query))
                rows = [dict(row) for row in result.mappings().all()]
            answer = _summarize_answer(question, plan.sql_query, rows)
            logger.info("Attempt %s final answer: %s", attempt, answer)
            console.print(answer)
            return answer
        except (SQLAlchemyError, ValueError, json.JSONDecodeError) as exc:
            last_error = exc
            logger.info("Attempt %s query failed: %s", attempt, exc)
            error_context = f"The previous SQL failed with this error: {exc}. Revise the query and try again.\n"

    if last_error is not None:
        raise last_error
    raise RuntimeError("Unable to answer the question.")


def main() -> None:
    raise SystemExit("Use invoice-agent ask <question> from the CLI.")


if __name__ == "__main__":
    main()
