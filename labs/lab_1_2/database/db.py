"""Only a dedicated SQLite file; no production .env or SQL Server connection."""
from pathlib import Path
from sqlalchemy import event
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine
from . import models  # Register all model tables before create_all.

DATABASE_PATH = Path(__file__).resolve().parents[1] / "database.db"


def make_engine(path=DATABASE_PATH, *, echo=False):
    options = {"connect_args": {"check_same_thread": False}, "echo": echo}
    if str(path) == ":memory:":
        url = "sqlite://"
        options["poolclass"] = StaticPool
    else:
        target = Path(path).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        url = "sqlite:///" + target.as_posix()
    engine = create_engine(url, **options)

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


engine = make_engine()


def init_db(target_engine=engine):
    SQLModel.metadata.create_all(target_engine)


def get_session():
    with Session(engine) as session:
        yield session
