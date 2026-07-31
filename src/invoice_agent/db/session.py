from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import create_engine, event, make_url
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


def database_url(db_path: str | Path) -> str:
    db_path_str = str(db_path)
    if "://" in db_path_str:
        return db_path_str
    path = Path(db_path_str)
    if path.is_absolute():
        return f"sqlite:///{path.as_posix()}"
    return f"sqlite:///{path.as_posix()}"


def create_db_engine(db_path: str | Path) -> Engine:
    engine = create_engine(database_url(db_path), future=True)

    if engine.url.drivername.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def _set_sqlite_pragmas(dbapi_connection, _connection_record) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def create_read_only_engine(db_path_or_url: str | Path) -> Engine:
    db_value = str(db_path_or_url)

    if "://" in db_value:
        url = make_url(db_value)
        engine = create_engine(url, future=True)

        if engine.url.drivername.startswith("postgresql"):
            @event.listens_for(engine, "connect")
            def _set_postgres_read_only(dbapi_connection, _connection_record) -> None:
                cursor = dbapi_connection.cursor()
                cursor.execute("SET default_transaction_read_only = on")
                cursor.close()

        return engine

    path = Path(db_value)
    if not path.exists():
        raise FileNotFoundError(f"Database file not found: {path}")

    def _creator():
        return sqlite3.connect(f"file:{path.resolve()}?mode=ro", uri=True)

    return create_engine("sqlite+pysqlite://", creator=_creator, future=True)


def create_session_factory(db_path: str | Path) -> sessionmaker[Session]:
    engine = create_db_engine(db_path)
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)


def session_scope(db_path: str | Path) -> Iterator[Session]:
    session_factory = create_session_factory(db_path)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
