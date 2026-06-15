"""Database engine/session and initialization."""
from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine

from .config import settings

settings.db_file.parent.mkdir(parents=True, exist_ok=True)
settings.documents_path.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    f"sqlite:///{settings.db_file}",
    connect_args={"check_same_thread": False},
)


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, _connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def _migrate_sqlite() -> None:
    """Add columns introduced after a DB was first created (SQLite ADD COLUMN)."""
    from sqlalchemy import text

    wanted = {
        "patient": {"username": "VARCHAR", "password_hash": "VARCHAR"},
    }
    with engine.begin() as conn:
        for table, cols in wanted.items():
            existing = {row[1] for row in conn.execute(text(f"PRAGMA table_info({table})"))}
            for col, decl in cols.items():
                if col not in existing:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {decl}"))


def init_db() -> None:
    """Create tables and seed the canonical biomarker catalog + a default patient."""
    # Import models so they register on SQLModel.metadata before create_all.
    from . import models  # noqa: F401

    SQLModel.metadata.create_all(engine)
    _migrate_sqlite()

    from .seed.biomarkers import seed_biomarkers, seed_default_patient

    with Session(engine) as session:
        seed_default_patient(session)
        seed_biomarkers(session)
        session.commit()


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
