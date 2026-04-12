from threading import Lock

import src.models  # noqa: F401
from sqlalchemy import inspect, text

from src.database import Base, get_engine

POSTGRES_SYNC_TRIGGER_LOCK_ID = 937451
_INITIALIZED_DATABASE_URLS: set[str] = set()
_INITIALIZATION_LOCK = Lock()


def _get_column_names(table_name: str) -> set[str]:
    inspector = inspect(get_engine())
    return {column["name"] for column in inspector.get_columns(table_name)}


def _drop_legacy_athlete_rating_seed_level() -> None:
    engine = get_engine()
    athlete_columns = _get_column_names("athletes")

    if "rating_seed_level" not in athlete_columns:
        return

    try:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE athletes DROP COLUMN rating_seed_level"))
    except Exception:
        # Best effort: il codice applicativo non usa piu' la colonna.
        pass


def _drop_legacy_match_token_cost() -> None:
    engine = get_engine()
    match_columns = _get_column_names("matches")

    if "token_cost" not in match_columns:
        return

    try:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE matches DROP COLUMN token_cost"))
    except Exception:
        # Best effort: il codice applicativo non usa piu' la colonna.
        pass


def _ensure_postgres_sync_metadata_triggers(engine) -> None:
    with engine.begin() as connection:
        # Serializza il bootstrap DDL tra sessioni concorrenti sullo stesso DB remoto.
        connection.execute(
            text("SELECT pg_advisory_xact_lock(:lock_id)"),
            {"lock_id": POSTGRES_SYNC_TRIGGER_LOCK_ID},
        )

        connection.execute(
            text(
                """
                CREATE OR REPLACE FUNCTION wl_apply_sync_metadata_defaults()
                RETURNS trigger AS $$
                BEGIN
                    IF NEW.updated_at IS NOT DISTINCT FROM OLD.updated_at THEN
                        NEW.updated_at := NOW();
                    END IF;

                    IF COALESCE(NEW.version_id, 0) = COALESCE(OLD.version_id, 0) THEN
                        NEW.version_id := COALESCE(OLD.version_id, 0) + 1;
                    END IF;

                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql
                """
            )
        )

        for table_name in ("athletes", "events", "matches"):
            trigger_name = f"wl_{table_name}_sync_metadata_defaults"
            connection.execute(
                text(
                    f"""
                    DO $$
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1
                            FROM pg_trigger
                            WHERE tgname = '{trigger_name}'
                              AND tgrelid = '{table_name}'::regclass
                        ) THEN
                            CREATE TRIGGER {trigger_name}
                            BEFORE UPDATE ON {table_name}
                            FOR EACH ROW
                            EXECUTE FUNCTION wl_apply_sync_metadata_defaults();
                        END IF;
                    END
                    $$;
                    """
                )
            )


def _ensure_sqlite_sync_metadata_triggers(engine) -> None:
    with engine.begin() as connection:
        for table_name in ("athletes", "events", "matches"):
            trigger_name = f"wl_{table_name}_sync_metadata_defaults"
            connection.execute(text(f"DROP TRIGGER IF EXISTS {trigger_name}"))
            connection.execute(
                text(
                    f"""
                    CREATE TRIGGER {trigger_name}
                    AFTER UPDATE ON {table_name}
                    FOR EACH ROW
                    WHEN COALESCE(NEW.version_id, 0) = COALESCE(OLD.version_id, 0)
                     AND NEW.updated_at IS OLD.updated_at
                    BEGIN
                        UPDATE {table_name}
                        SET
                            updated_at = CURRENT_TIMESTAMP,
                            version_id = COALESCE(OLD.version_id, 0) + 1
                        WHERE id = NEW.id;
                    END
                    """
                )
            )


def ensure_engine_sync_metadata_triggers(engine) -> None:
    dialect_name = engine.dialect.name

    if dialect_name == "postgresql":
        _ensure_postgres_sync_metadata_triggers(engine)
        return

    if dialect_name == "sqlite":
        _ensure_sqlite_sync_metadata_triggers(engine)
        return


def init_db() -> None:
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    _drop_legacy_athlete_rating_seed_level()
    _drop_legacy_match_token_cost()
    ensure_engine_sync_metadata_triggers(engine)


def ensure_initialized_database() -> None:
    engine = get_engine()
    database_url = engine.url.render_as_string(hide_password=False)

    if database_url in _INITIALIZED_DATABASE_URLS:
        return

    with _INITIALIZATION_LOCK:
        if database_url in _INITIALIZED_DATABASE_URLS:
            return

        init_db()
        _INITIALIZED_DATABASE_URLS.add(database_url)
