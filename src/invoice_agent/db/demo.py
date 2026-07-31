from __future__ import annotations

from pathlib import Path
import sqlite3

from invoice_agent.config import get_settings


def run(db_path: str | Path | None = None, table_name: str | None = None) -> None:
    settings = get_settings()
    resolved_db_path = Path(db_path or settings.demo_db_path)
    resolved_table_name = table_name or settings.demo_table_name

    conn = sqlite3.connect(str(resolved_db_path))
    cursor = conn.cursor()

    cursor.execute(f"SELECT * FROM {resolved_table_name}")
    orders = cursor.fetchall()
    for order in orders:
        print(order)

    conn.close()


def main() -> None:
    run()


if __name__ == "__main__":
    main()
