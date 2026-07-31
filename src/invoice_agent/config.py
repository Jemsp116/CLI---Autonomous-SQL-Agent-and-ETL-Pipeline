from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    invoice_output_dir: Path = Path("data/invoices")
    invoice_zip_path: Path = Path("data/invoices.zip")
    invoice_start_no: int = 51109301
    invoice_end_no: int = 51109351
    spot_check_invoice_nos: tuple[int, int, int] = (51109301, 51109325, 51109350)

    headers_input_dir: Path = Path("data/invoices")
    headers_output_csv: Path = Path("data/csv/invoice_headers.csv")
    headers_report_json: Path = Path("data/csv/invoice_headers_report.json")

    tables_input_dir: Path = Path("data/invoices")
    line_items_csv: Path = Path("data/csv/invoice_line_items.csv")
    summaries_csv: Path = Path("data/csv/invoice_summaries.csv")
    tables_report_json: Path = Path("data/csv/invoice_tables_report.json")

    demo_db_path: Path = Path("data/db.sqlite")

    openrouter_api_key: str | None = None
    openrouter_api_base: str = "https://openrouter.ai/api/v1"
    agent_model: str = "openai/gpt-oss-120b"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
