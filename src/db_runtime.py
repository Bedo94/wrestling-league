from pathlib import Path
import os

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

# Ambienti logici
DB_ENV_LEAGUE_LOCAL = "league_local"
DB_ENV_LEAGUE_REMOTE = "league_remote"
DB_ENV_TEST_LOCAL = "test_local"
DB_ENV_TEST_REMOTE = "test_remote"

DB_ENV_OPTIONS = (
    DB_ENV_LEAGUE_LOCAL,
    DB_ENV_LEAGUE_REMOTE,
    DB_ENV_TEST_LOCAL,
    DB_ENV_TEST_REMOTE,
)

DB_ENV_LABELS = {
    DB_ENV_LEAGUE_LOCAL: "League local",
    DB_ENV_LEAGUE_REMOTE: "League remote",
    DB_ENV_TEST_LOCAL: "Test local",
    DB_ENV_TEST_REMOTE: "Test remote",
}

DB_CONTEXT_LEAGUE = "league"
DB_CONTEXT_TEST = "test"

DB_LOCATION_LOCAL = "local"
DB_LOCATION_REMOTE = "remote"

DB_SYNC_DIRECTION_LOCAL_TO_REMOTE = "local_to_remote"
DB_SYNC_DIRECTION_REMOTE_TO_LOCAL = "remote_to_local"

DB_SYNC_DIRECTION_LABELS = {
    DB_SYNC_DIRECTION_LOCAL_TO_REMOTE: "Locale → Remoto",
    DB_SYNC_DIRECTION_REMOTE_TO_LOCAL: "Remoto → Locale",
}

STATE_DB_MODE = "db_mode"
STATE_SQLITE_PATH = "db_sqlite_path"
STATE_POSTGRES_URL = "db_postgres_url"
STATE_ACTIVE_DB_INFO = "active_db_info"

STATE_DB_ENVIRONMENT = "db_environment"

STATE_LEAGUE_LOCAL_PATH = "db_league_local_path"
STATE_TEST_LOCAL_PATH = "db_test_local_path"
STATE_LEAGUE_REMOTE_URL = "db_league_remote_url"
STATE_TEST_REMOTE_URL = "db_test_remote_url"

UPLOADED_DB_DIR = DATA_DIR / "uploaded_dbs"
UPLOADED_DB_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_TEST_DB_PATH = DATA_DIR / "test_local.db"

LEAGUE_REMOTE_URL_ENV_KEYS = (
    "LEAGUE_REMOTE_DATABASE_URL",
    "DATABASE_URL",
    "WL_DATABASE_URL",
)
TEST_REMOTE_URL_ENV_KEYS = (
    "TEST_REMOTE_DATABASE_URL",
    "WL_TEST_DATABASE_URL",
)


def _first_env_value(keys: tuple[str, ...], default: str = "") -> str:
    for key in keys:
        value = os.getenv(key)
        if value:
            return value
    return default


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


def is_test_environment(environment_name: str) -> bool:
    return environment_name in {DB_ENV_TEST_LOCAL, DB_ENV_TEST_REMOTE}


def is_league_environment(environment_name: str) -> bool:
    return environment_name in {DB_ENV_LEAGUE_LOCAL, DB_ENV_LEAGUE_REMOTE}


def is_local_environment(environment_name: str) -> bool:
    return environment_name in {DB_ENV_LEAGUE_LOCAL, DB_ENV_TEST_LOCAL}


def is_remote_environment(environment_name: str) -> bool:
    return environment_name in {DB_ENV_LEAGUE_REMOTE, DB_ENV_TEST_REMOTE}


def get_environment_context(environment_name: str) -> str:
    if is_test_environment(environment_name):
        return DB_CONTEXT_TEST
    return DB_CONTEXT_LEAGUE


def get_environment_location(environment_name: str) -> str:
    if is_local_environment(environment_name):
        return DB_LOCATION_LOCAL
    return DB_LOCATION_REMOTE


def build_environment_name(context: str, location: str) -> str:
    context = (context or "").strip().lower()
    location = (location or "").strip().lower()

    if context == DB_CONTEXT_LEAGUE and location == DB_LOCATION_LOCAL:
        return DB_ENV_LEAGUE_LOCAL
    if context == DB_CONTEXT_LEAGUE and location == DB_LOCATION_REMOTE:
        return DB_ENV_LEAGUE_REMOTE
    if context == DB_CONTEXT_TEST and location == DB_LOCATION_LOCAL:
        return DB_ENV_TEST_LOCAL
    if context == DB_CONTEXT_TEST and location == DB_LOCATION_REMOTE:
        return DB_ENV_TEST_REMOTE

    raise ValueError(f"Combinazione ambiente non valida: {context=} {location=}")


def get_environment_description(environment_name: str) -> str:
    descriptions = {
        DB_ENV_LEAGUE_LOCAL: (
            "Ambiente ufficiale locale. Utile come copia offline/backup operativo "
            "del database ufficiale."
        ),
        DB_ENV_LEAGUE_REMOTE: (
            "Ambiente ufficiale remoto. È la fonte di verità dei dati reali."
        ),
        DB_ENV_TEST_LOCAL: (
            "Ambiente di test locale. Serve per prove personali senza toccare "
            "i dati ufficiali."
        ),
        DB_ENV_TEST_REMOTE: (
            "Ambiente di test remoto. Serve per prove condivise senza toccare "
            "i dati ufficiali."
        ),
    }
    return descriptions.get(environment_name, "")


def can_sync_between_environments(source_environment: str, target_environment: str) -> bool:
    if source_environment == target_environment:
        return False

    allowed_pairs = {
        frozenset({DB_ENV_LEAGUE_LOCAL, DB_ENV_LEAGUE_REMOTE}),
        frozenset({DB_ENV_TEST_LOCAL, DB_ENV_TEST_REMOTE}),
    }

    return frozenset({source_environment, target_environment}) in allowed_pairs


def get_sync_policy_message(source_environment: str, target_environment: str) -> str:
    if source_environment == target_environment:
        return "Nessuna sincronizzazione necessaria: ambiente identico."

    if can_sync_between_environments(source_environment, target_environment):
        return "Sincronizzazione consentita."

    if (
        is_test_environment(source_environment) and is_league_environment(target_environment)
    ) or (
        is_league_environment(source_environment) and is_test_environment(target_environment)
    ):
        return (
            "Sincronizzazione NON consentita: gli ambienti di test non possono "
            "essere sincronizzati con quelli ufficiali."
        )

    return "Sincronizzazione NON consentita per questa combinazione di ambienti."


def list_sync_compatible_targets(source_environment: str) -> list[str]:
    return [
        environment_name
        for environment_name in DB_ENV_OPTIONS
        if can_sync_between_environments(source_environment, environment_name)
    ]


def build_sync_route(context: str, direction: str) -> tuple[str, str]:
    context = (context or "").strip().lower()
    direction = (direction or "").strip().lower()

    if context == DB_CONTEXT_LEAGUE:
        if direction == DB_SYNC_DIRECTION_LOCAL_TO_REMOTE:
            return DB_ENV_LEAGUE_LOCAL, DB_ENV_LEAGUE_REMOTE
        if direction == DB_SYNC_DIRECTION_REMOTE_TO_LOCAL:
            return DB_ENV_LEAGUE_REMOTE, DB_ENV_LEAGUE_LOCAL

    if context == DB_CONTEXT_TEST:
        if direction == DB_SYNC_DIRECTION_LOCAL_TO_REMOTE:
            return DB_ENV_TEST_LOCAL, DB_ENV_TEST_REMOTE
        if direction == DB_SYNC_DIRECTION_REMOTE_TO_LOCAL:
            return DB_ENV_TEST_REMOTE, DB_ENV_TEST_LOCAL

    raise ValueError(f"Combinazione sync non valida: {context=} {direction=}")


def get_sync_route_description(context: str, direction: str) -> str:
    source_environment, target_environment = build_sync_route(context, direction)
    return (
        f"{DB_ENV_LABELS[source_environment]} → "
        f"{DB_ENV_LABELS[target_environment]}"
    )


def _infer_initial_state() -> tuple[str, str, str, str]:
    current_sqlite_path = get_current_sqlite_path()

    if current_sqlite_path is None:
        current_url = get_database_url(hide_password=False)
        test_remote_url = sanitize_database_url(
            _first_env_value(TEST_REMOTE_URL_ENV_KEYS)
        )

        if test_remote_url and current_url == test_remote_url:
            environment_name = DB_ENV_TEST_REMOTE
        else:
            environment_name = DB_ENV_LEAGUE_REMOTE

        return (
            DB_MODE_POSTGRES,
            "",
            current_url,
            environment_name,
        )

    resolved_path = current_sqlite_path.resolve()

    if resolved_path == DEFAULT_TEST_DB_PATH.resolve():
        environment_name = DB_ENV_TEST_LOCAL
    else:
        environment_name = DB_ENV_LEAGUE_LOCAL

    return (
        DB_MODE_SQLITE,
        str(resolved_path),
        "",
        environment_name,
    )


def ensure_db_state() -> None:
    if STATE_DB_MODE in st.session_state:
        return

    st.session_state[STATE_LEAGUE_LOCAL_PATH] = str(DEFAULT_DB_PATH.resolve())
    st.session_state[STATE_TEST_LOCAL_PATH] = str(DEFAULT_TEST_DB_PATH.resolve())
    st.session_state[STATE_LEAGUE_REMOTE_URL] = sanitize_database_url(
        _first_env_value(LEAGUE_REMOTE_URL_ENV_KEYS)
    )
    st.session_state[STATE_TEST_REMOTE_URL] = sanitize_database_url(
        _first_env_value(TEST_REMOTE_URL_ENV_KEYS)
    )

    mode, sqlite_path, postgres_url, environment_name = _infer_initial_state()

    st.session_state[STATE_DB_MODE] = mode
    st.session_state[STATE_SQLITE_PATH] = sqlite_path
    st.session_state[STATE_POSTGRES_URL] = postgres_url
    st.session_state[STATE_DB_ENVIRONMENT] = environment_name


def get_selected_mode() -> str:
    ensure_db_state()
    return st.session_state[STATE_DB_MODE]


def get_selected_sqlite_path() -> str:
    ensure_db_state()
    return st.session_state[STATE_SQLITE_PATH]


def get_selected_postgres_url() -> str:
    ensure_db_state()
    return st.session_state[STATE_POSTGRES_URL]


def get_selected_environment_name() -> str:
    ensure_db_state()
    return st.session_state[STATE_DB_ENVIRONMENT]


def get_mode_index(mode: str) -> int:
    try:
        return DB_MODE_OPTIONS.index(mode)
    except ValueError:
        return 0


def _infer_environment_from_selection(
    *,
    mode: str,
    sqlite_path: str,
    postgres_url: str,
) -> str:
    if mode == DB_MODE_SQLITE:
        clean_path = sanitize_sqlite_path(sqlite_path)
        resolved_path = normalize_sqlite_path(clean_path or DEFAULT_DB_PATH)

        if resolved_path.resolve() == DEFAULT_TEST_DB_PATH.resolve():
            return DB_ENV_TEST_LOCAL

        return DB_ENV_LEAGUE_LOCAL

    if mode == DB_MODE_POSTGRES:
        clean_url = sanitize_database_url(postgres_url)
        test_remote_url = sanitize_database_url(
            st.session_state.get(STATE_TEST_REMOTE_URL, "")
        )

        if clean_url and test_remote_url and clean_url == test_remote_url:
            return DB_ENV_TEST_REMOTE

        return DB_ENV_LEAGUE_REMOTE

    raise ValueError(f"Modalità database non supportata: {mode}")


def _apply_database(
    *,
    mode: str,
    sqlite_path: str,
    postgres_url: str,
    environment_name: str,
) -> dict:
    if mode == DB_MODE_SQLITE:
        if environment_name == DB_ENV_TEST_LOCAL:
            fallback_path = st.session_state.get(
                STATE_TEST_LOCAL_PATH,
                str(DEFAULT_TEST_DB_PATH.resolve()),
            )
        else:
            fallback_path = st.session_state.get(
                STATE_LEAGUE_LOCAL_PATH,
                str(DEFAULT_DB_PATH.resolve()),
            )

        clean_path = sanitize_sqlite_path(sqlite_path)
        resolved_path = normalize_sqlite_path(clean_path or fallback_path)

        configure_database(sqlite_path=resolved_path)
        init_db()

        try:
            load_config()
        except Exception:
            pass

        return {
            "mode": mode,
            "mode_label": DB_MODE_LABELS[mode],
            "environment_name": environment_name,
            "environment_label": DB_ENV_LABELS[environment_name],
            "environment_description": get_environment_description(environment_name),
            "label": str(resolved_path),
            "database_url": get_database_url(hide_password=False),
            "database_url_masked": get_database_url(hide_password=True),
            "sqlite_path": str(resolved_path),
        }

    if mode == DB_MODE_POSTGRES:
        if environment_name == DB_ENV_TEST_REMOTE:
            fallback_url = st.session_state.get(STATE_TEST_REMOTE_URL, "")
        else:
            fallback_url = st.session_state.get(STATE_LEAGUE_REMOTE_URL, "")

        clean_url = sanitize_database_url(postgres_url or fallback_url)

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
            "environment_name": environment_name,
            "environment_label": DB_ENV_LABELS[environment_name],
            "environment_description": get_environment_description(environment_name),
            "label": DB_ENV_LABELS[environment_name],
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
    environment_name: str | None = None,
) -> dict:
    ensure_db_state()

    resolved_environment_name = environment_name or _infer_environment_from_selection(
        mode=mode,
        sqlite_path=sqlite_path,
        postgres_url=postgres_url,
    )

    clean_sqlite_path = sanitize_sqlite_path(sqlite_path)
    clean_postgres_url = sanitize_database_url(postgres_url)

    st.session_state[STATE_DB_MODE] = mode
    st.session_state[STATE_DB_ENVIRONMENT] = resolved_environment_name

    if mode == DB_MODE_SQLITE:
        if resolved_environment_name == DB_ENV_TEST_LOCAL:
            stored_sqlite_path = clean_sqlite_path or str(DEFAULT_TEST_DB_PATH.resolve())
            st.session_state[STATE_TEST_LOCAL_PATH] = stored_sqlite_path
        else:
            stored_sqlite_path = clean_sqlite_path or str(DEFAULT_DB_PATH.resolve())
            st.session_state[STATE_LEAGUE_LOCAL_PATH] = stored_sqlite_path

        st.session_state[STATE_SQLITE_PATH] = stored_sqlite_path
        st.session_state[STATE_POSTGRES_URL] = ""

    elif mode == DB_MODE_POSTGRES:
        if resolved_environment_name == DB_ENV_TEST_REMOTE:
            st.session_state[STATE_TEST_REMOTE_URL] = clean_postgres_url
        else:
            st.session_state[STATE_LEAGUE_REMOTE_URL] = clean_postgres_url

        st.session_state[STATE_SQLITE_PATH] = ""
        st.session_state[STATE_POSTGRES_URL] = clean_postgres_url

    info = _apply_database(
        mode=mode,
        sqlite_path=st.session_state[STATE_SQLITE_PATH],
        postgres_url=st.session_state[STATE_POSTGRES_URL],
        environment_name=resolved_environment_name,
    )

    st.session_state[STATE_ACTIVE_DB_INFO] = info
    return info


def bootstrap_database_from_state() -> dict:
    ensure_db_state()

    info = _apply_database(
        mode=get_selected_mode(),
        sqlite_path=get_selected_sqlite_path(),
        postgres_url=get_selected_postgres_url(),
        environment_name=get_selected_environment_name(),
    )

    st.session_state[STATE_ACTIVE_DB_INFO] = info
    return info


def get_active_database_info() -> dict:
    ensure_db_state()

    if STATE_ACTIVE_DB_INFO not in st.session_state:
        return bootstrap_database_from_state()

    return st.session_state[STATE_ACTIVE_DB_INFO]