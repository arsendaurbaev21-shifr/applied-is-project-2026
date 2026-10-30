"""SQLite файлы әрқашан жоба түбірінде жасалады."""

import os
from pathlib import Path

from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATABASE_PATH = PROJECT_ROOT / "database.db"


def make_engine(url: str, *, echo: bool = False):
    db_engine = create_engine(
        url, echo=echo, connect_args={"check_same_thread": False}
    )

    @event.listens_for(db_engine, "connect")
    def enable_foreign_keys(connection, _record):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return db_engine


engine = make_engine(
    f"sqlite:///{DATABASE_PATH.as_posix()}",
    echo=os.getenv("SQL_ECHO", "1") == "1",
)


def init_db(db_engine=engine):
    # Import before create_all so every table is registered in metadata.
    from app.database import models  # noqa: F401

    SQLModel.metadata.create_all(db_engine)


def get_session():
    with Session(engine) as session:
        yield session
