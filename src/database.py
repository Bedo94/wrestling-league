import os
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DEFAULT_DB_PATH = DATA_DIR / "league.db"

DATABASE_URL_ENV_KEYS = ("DATABASE_URL", "WL_DATABASE_URL")
SQLITE_PATH_ENV_KEY = "WL_SQLITE_PATH"


class Base(DeclarativeBase):
    pass


engine: Engine | None = None

SessionLocal = sessionmaker(
    autoflush=False,
    autocommit=False,
    future=True,
)


def normalize_sqlite_path(raw_path: str | Path | None = None) -> Path:
    candidate = Path(raw_path).expanduser() if raw_path else DEFAULT_DB_PATH

    if not candidate.is_absolute():
        candidate = (BASE_DIR / candidate).resolve()

    return candidate


def build_sqlite_url(sqlite_path: str | Path | None = None) -> str:
    path = normalize_sqlite_path(sqlite_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{path.as_posix()}"


def resolve_database_url() -> str:
    for env_key in DATABASE_URL_ENV_KEYS:
        value = os.getenv(env_key)
        if value:
            return value

    sqlite_path = os.getenv(SQLITE_PATH_ENV_KEY)
    return build_sqlite_url(sqlite_path)


DATABASE_URL = resolve_database_url()


def is_sqlite_url(database_url: str) -> bool:
    return database_url.startswith("sqlite")


def _engine_kwargs(database_url: str) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "echo": False,
        "future": True,
    }

    if is_sqlite_url(database_url):
        kwargs["connect_args"] = {"check_same_thread": False}

    return kwargs


def configure_database(
    *,
    database_url: str | None = None,
    sqlite_path: str | Path | None = None,
) -> Engine:
    global engine, DATABASE_URL

    if database_url:
        resolved_url = database_url.strip()
    elif sqlite_path is not None:
        resolved_url = build_sqlite_url(sqlite_path)
    else:
        resolved_url = resolve_database_url()

    if engine is not None:
        engine.dispose()

    engine = create_engine(
        resolved_url,
        **_engine_kwargs(resolved_url),
    )

    SessionLocal.configure(bind=engine)
    DATABASE_URL = resolved_url

    return engine


def get_engine() -> Engine:
    global engine

    if engine is None:
        configure_database()

    if engine is None:
        raise RuntimeError("Database engine non configurato.")

    return engine


def get_database_url(*, hide_password: bool = False) -> str:
    return get_engine().url.render_as_string(hide_password=hide_password)


def get_current_sqlite_path() -> Path | None:
    current_engine = get_engine()
    current_url = str(current_engine.url)

    if not is_sqlite_url(current_url):
        return None

    database_part = current_engine.url.database
    if not database_part:
        return None

    return Path(database_part).resolve()


def sqlite_file_exists(sqlite_path: str | Path | None = None) -> bool:
    return normalize_sqlite_path(sqlite_path).exists()


def get_session():
    get_engine()
    return SessionLocal()


configure_database()