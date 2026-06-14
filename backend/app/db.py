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


def init_db() -> None:
    """Create tables and seed the canonical biomarker catalog + a default patient."""
    # Import models so they register on SQLModel.metadata before create_all.
    from . import models  # noqa: F401

    SQLModel.metadata.create_all(engine)

    from .seed.biomarkers import seed_biomarkers, seed_default_patient

    with Session(engine) as session:
        seed_default_patient(session)
        seed_biomarkers(session)
        session.commit()


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
