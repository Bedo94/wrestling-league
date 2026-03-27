from pathlib import Path

import streamlit as st

from src.database import (
    DATA_DIR,
    DEFAULT_DB_PATH,
    configure_database,
    get_current_sqlite_path,
    get_database_url,
    normalize_sqlite_path,
)
from src.init_db import init_db

from src.formula_config_service import load_config

DB_MODE_SQLITE = "sqlite"
DB_MODE_POSTGRES = "postgresql"

DB_MODE_OPTIONS = (
    DB_MODE_SQLITE,
    DB_MODE_POSTGRES,
)

DB_MODE_LABELS = {
    DB_MODE_SQLITE: "SQLite locale",
    DB_MODE_POSTGRES: "PostgreSQL remoto",
}

STATE_DB_MODE = "db_mode"
STATE_SQLITE_PATH = "db_sqlite_path"
STATE_POSTGRES_URL = "db_postgres_url"
STATE_ACTIVE_DB_INFO = "active_db_info"

UPLOADED_DB_DIR = DATA_DIR / "uploaded_dbs"
UPLOADED_DB_DIR.mkdir(parents=True, exist_ok=True)


def _clean_wrapped_text(raw_value: str | None) -> str:
    value = (raw_value or "").strip()

    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1].strip()

    return value


def sanitize_sqlite_path(raw_path: str | None) -> str:
    return _clean_wrapped_text(raw_path)


def sanitize_database_url(raw_url: str | None) -> str:
    return _clean_wrapped_text(raw_url)


def build_uploaded_sqlite_destination(filename: str) -> Path:
    safe_name = Path(filename).name.strip()

    if not safe_name:
        raise ValueError("Nome file non valido.")

    return (UPLOADED_DB_DIR / safe_name).resolve()


def save_uploaded_sqlite_file(uploaded_file) -> Path:
    destination = build_uploaded_sqlite_destination(uploaded_file.name)

    with destination.open("wb") as output_file:
        output_file.write(uploaded_file.getbuffer())

    return destination


def _infer_initial_state() -> tuple[str, str, str]:
    current_sqlite_path = get_current_sqlite_path()

    if current_sqlite_path is None:
        return (
            DB_MODE_POSTGRES,
            str(DEFAULT_DB_PATH.resolve()),
            get_database_url(hide_password=False),
        )

    return (
        DB_MODE_SQLITE,
        str(current_sqlite_path.resolve()),
        "",
    )


def ensure_db_state() -> None:
    if STATE_DB_MODE in st.session_state:
        return

    mode, sqlite_path, postgres_url = _infer_initial_state()

    st.session_state[STATE_DB_MODE] = mode
    st.session_state[STATE_SQLITE_PATH] = sqlite_path
    st.session_state[STATE_POSTGRES_URL] = postgres_url


def get_selected_mode() -> str:
    ensure_db_state()
    return st.session_state[STATE_DB_MODE]


def get_selected_sqlite_path() -> str:
    ensure_db_state()
    return st.session_state[STATE_SQLITE_PATH]


def get_selected_postgres_url() -> str:
    ensure_db_state()
    return st.session_state[STATE_POSTGRES_URL]


def get_mode_index(mode: str) -> int:
    try:
        return DB_MODE_OPTIONS.index(mode)
    except ValueError:
        return 0


def _apply_database(
    *,
    mode: str,
    sqlite_path: str,
    postgres_url: str,
) -> dict:
    if mode == DB_MODE_SQLITE:
        clean_path = sanitize_sqlite_path(sqlite_path)

        resolved_path = normalize_sqlite_path(clean_path or DEFAULT_DB_PATH)

        configure_database(sqlite_path=resolved_path)
        init_db()
        try:
            load_config()
        except Exception:
            pass

        return {
            "mode": mode,
            "mode_label": DB_MODE_LABELS[mode],
            "label": str(resolved_path),
            "database_url": get_database_url(hide_password=False),
            "database_url_masked": get_database_url(hide_password=True),
            "sqlite_path": str(resolved_path),
        }

    if mode == DB_MODE_POSTGRES:
        clean_url = sanitize_database_url(postgres_url)

        if not clean_url:
            raise ValueError("Inserisci una DATABASE_URL valida per PostgreSQL.")

        configure_database(database_url=clean_url)
        init_db()
        try:
            load_config()
        except Exception:
            pass

        return {
            "mode": mode,
            "mode_label": DB_MODE_LABELS[mode],
            "label": "PostgreSQL remoto",
            "database_url": get_database_url(hide_password=False),
            "database_url_masked": get_database_url(hide_password=True),
            "sqlite_path": None,
        }

    raise ValueError(f"Modalità database non supportata: {mode}")


def set_database_selection(
    *,
    mode: str,
    sqlite_path: str,
    postgres_url: str,
) -> dict:
    ensure_db_state()

    st.session_state[STATE_DB_MODE] = mode
    st.session_state[STATE_SQLITE_PATH] = sqlite_path
    st.session_state[STATE_POSTGRES_URL] = postgres_url

    info = _apply_database(
        mode=mode,
        sqlite_path=sqlite_path,
        postgres_url=postgres_url,
    )

    st.session_state[STATE_ACTIVE_DB_INFO] = info
    return info


def bootstrap_database_from_state() -> dict:
    ensure_db_state()

    info = _apply_database(
        mode=get_selected_mode(),
        sqlite_path=get_selected_sqlite_path(),
        postgres_url=get_selected_postgres_url(),
    )

    st.session_state[STATE_ACTIVE_DB_INFO] = info
    return info


def get_active_database_info() -> dict:
    ensure_db_state()

    if STATE_ACTIVE_DB_INFO not in st.session_state:
        return bootstrap_database_from_state()

    return st.session_state[STATE_ACTIVE_DB_INFO]