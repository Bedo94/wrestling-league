from __future__ import annotations

from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd
import src.models  # noqa: F401
from sqlalchemy import inspect, select
from sqlalchemy import create_engine as sa_create_engine

from src.database import Base, get_current_sqlite_path, get_engine

SQLITE_DOWNLOAD_MIME = "application/octet-stream"
EXCEL_DOWNLOAD_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

_INVALID_EXCEL_SHEET_CHARS = set('[]:*?/\\')


def list_exportable_tables() -> list[str]:
    inspector = inspect(get_engine())
    return inspector.get_table_names()


def _sanitize_sheet_name(sheet_name: str, used_names: set[str]) -> str:
    cleaned = "".join(
        "_" if char in _INVALID_EXCEL_SHEET_CHARS else char
        for char in sheet_name
    ).strip()

    if not cleaned:
        cleaned = "Sheet"

    cleaned = cleaned[:31]

    candidate = cleaned
    counter = 1

    while candidate in used_names:
        suffix = f"_{counter}"
        candidate = f"{cleaned[: 31 - len(suffix)]}{suffix}"
        counter += 1

    used_names.add(candidate)
    return candidate


def export_active_database_to_excel_bytes() -> bytes:
    engine = get_engine()
    table_names = list_exportable_tables()

    output = BytesIO()
    used_sheet_names: set[str] = set()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        if not table_names:
            pd.DataFrame(
                [{"info": "Nessuna tabella presente nel database attivo."}]
            ).to_excel(writer, sheet_name="Info", index=False)
        else:
            for table_name in table_names:
                dataframe = pd.read_sql_table(table_name, engine)
                sheet_name = _sanitize_sheet_name(table_name, used_sheet_names)
                dataframe.to_excel(writer, sheet_name=sheet_name, index=False)

    output.seek(0)
    return output.getvalue()


def _copy_model_tables_to_sqlite_snapshot(snapshot_path: Path) -> None:
    source_engine = get_engine()

    snapshot_engine = sa_create_engine(
        f"sqlite:///{snapshot_path.as_posix()}",
        echo=False,
        future=True,
        connect_args={"check_same_thread": False},
    )

    try:
        Base.metadata.create_all(bind=snapshot_engine)

        with source_engine.connect() as source_conn, snapshot_engine.begin() as snapshot_conn:
            for table in Base.metadata.sorted_tables:
                rows = source_conn.execute(select(table)).mappings().all()

                if rows:
                    snapshot_conn.execute(
                        table.insert(),
                        [dict(row) for row in rows],
                    )
    finally:
        snapshot_engine.dispose()


def _build_sqlite_snapshot_bytes() -> bytes:
    with TemporaryDirectory() as temp_dir:
        snapshot_path = Path(temp_dir) / "wrestling_league_snapshot.db"
        _copy_model_tables_to_sqlite_snapshot(snapshot_path)
        return snapshot_path.read_bytes()


def export_active_database_to_sqlite_bytes() -> bytes:
    current_sqlite_path = get_current_sqlite_path()

    if current_sqlite_path is not None and current_sqlite_path.exists():
        return current_sqlite_path.read_bytes()

    return _build_sqlite_snapshot_bytes()