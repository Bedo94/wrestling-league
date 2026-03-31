from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from src.database import normalize_sqlite_path
from src.db_runtime import (
    DB_MODE_POSTGRES,
    DB_MODE_SQLITE,
    can_sync_between_environments,
)
from src.models import Athlete, Event, Match


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _normalize_dt(value: datetime | None) -> datetime:
    if value is None:
        return datetime.min.replace(tzinfo=timezone.utc)

    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


def _parse_changed_since(value: str | None) -> datetime | None:
    raw = (value or "").strip()
    if not raw:
        return None

    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError(
            "Formato data/ora non valido per il filtro di sincronizzazione. "
            "Usa un valore ISO, ad esempio 2026-03-31T10:30:00+00:00."
        ) from exc

    return _normalize_dt(parsed)


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return _normalize_dt(value).isoformat(timespec="seconds")
    return str(value)


def _build_sqlalchemy_url(
    *,
    mode: str,
    sqlite_path: str = "",
    postgres_url: str = "",
) -> str:
    if mode == DB_MODE_SQLITE:
        resolved_path = normalize_sqlite_path(sqlite_path)
        resolved_path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{resolved_path.as_posix()}"

    if mode == DB_MODE_POSTGRES:
        clean_url = (postgres_url or "").strip()
        if not clean_url:
            raise ValueError("DATABASE_URL PostgreSQL mancante.")
        return clean_url

    raise ValueError(f"Modalità database non supportata: {mode}")


def _build_session_factory(
    *,
    mode: str,
    sqlite_path: str = "",
    postgres_url: str = "",
):
    database_url = _build_sqlalchemy_url(
        mode=mode,
        sqlite_path=sqlite_path,
        postgres_url=postgres_url,
    )

    engine_kwargs: dict[str, Any] = {
        "echo": False,
        "future": True,
    }

    if mode == DB_MODE_SQLITE:
        engine_kwargs["connect_args"] = {"check_same_thread": False}

    engine = create_engine(database_url, **engine_kwargs)

    return engine, sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        future=True,
    )


def _empty_summary() -> dict[str, int]:
    return {
        "scanned": 0,
        "inserted": 0,
        "updated": 0,
        "skipped": 0,
        "conflicts": 0,
    }


def _is_source_newer(
    *,
    source_updated_at: datetime | None,
    target_updated_at: datetime | None,
    source_version_id: int | None,
    target_version_id: int | None,
) -> bool:
    source_dt = _normalize_dt(source_updated_at)
    target_dt = _normalize_dt(target_updated_at)

    if source_dt > target_dt:
        return True

    if source_dt == target_dt:
        return int(source_version_id or 0) > int(target_version_id or 0)

    return False


def _records_differ(existing: Any, payload: dict[str, Any], fields: list[str]) -> bool:
    for field in fields:
        if getattr(existing, field) != payload.get(field):
            return True
    return False


def _make_conflict(
    *,
    table_name: str,
    sync_id: str,
    reason: str,
    source_updated_at: datetime | None,
    target_updated_at: datetime | None,
    source_version_id: int | None,
    target_version_id: int | None,
    details: str = "",
) -> dict[str, Any]:
    return {
        "table": table_name,
        "sync_id": sync_id,
        "reason": reason,
        "source_updated_at": _stringify(source_updated_at),
        "target_updated_at": _stringify(target_updated_at),
        "source_version_id": source_version_id,
        "target_version_id": target_version_id,
        "details": details,
    }


def _build_athlete_insert_payload(source: Athlete) -> dict[str, Any]:
    return {
        "first_name": source.first_name,
        "last_name": source.last_name,
        "nickname": source.nickname,
        "team": source.team,
        "birth_date": source.birth_date,
        "sex": source.sex,
        "style": source.style,
        "level": source.level,
        "default_weight": source.default_weight,
        "rating": source.rating,
        "active": source.active,
        "token_budget": source.token_budget,
        "sync_id": source.sync_id,
        "created_at": source.created_at,
        "updated_at": source.updated_at,
        "version_id": source.version_id,
    }


def _copy_athlete_fields(source: Athlete, target: Athlete) -> None:
    target.first_name = source.first_name
    target.last_name = source.last_name
    target.nickname = source.nickname
    target.team = source.team
    target.birth_date = source.birth_date
    target.sex = source.sex
    target.style = source.style
    target.level = source.level
    target.default_weight = source.default_weight
    target.rating = source.rating
    target.active = source.active
    target.token_budget = source.token_budget


def _build_event_insert_payload(source: Event) -> dict[str, Any]:
    return {
        "name": source.name,
        "event_date": source.event_date,
        "season": source.season,
        "notes": source.notes,
        "sync_id": source.sync_id,
        "created_at": source.created_at,
        "updated_at": source.updated_at,
        "version_id": source.version_id,
    }


def _copy_event_fields(source: Event, target: Event) -> None:
    target.name = source.name
    target.event_date = source.event_date
    target.season = source.season
    target.notes = source.notes


def _sync_athletes(
    *,
    source_session: Session,
    target_session: Session,
    conflicts: list[dict[str, Any]],
    log_lines: list[str],
    changed_since: datetime | None,
) -> dict[str, int]:
    summary = _empty_summary()

    stmt = select(Athlete).order_by(Athlete.id.asc())
    if changed_since is not None:
        stmt = stmt.where(Athlete.updated_at >= changed_since)

    source_rows = list(source_session.scalars(stmt).all())
    summary["scanned"] = len(source_rows)

    compare_fields = [
        "first_name",
        "last_name",
        "nickname",
        "team",
        "birth_date",
        "sex",
        "style",
        "level",
        "default_weight",
        "rating",
        "active",
        "token_budget",
    ]

    for source_row in source_rows:
        existing = target_session.scalar(
            select(Athlete).where(Athlete.sync_id == source_row.sync_id)
        )

        if existing is None:
            target_session.add(Athlete(**_build_athlete_insert_payload(source_row)))
            summary["inserted"] += 1
            log_lines.append(
                f"[athletes] INSERT sync_id={source_row.sync_id} name={source_row.first_name}"
            )
            continue

        payload = _build_athlete_insert_payload(source_row)

        if _is_source_newer(
            source_updated_at=source_row.updated_at,
            target_updated_at=existing.updated_at,
            source_version_id=source_row.version_id,
            target_version_id=existing.version_id,
        ):
            _copy_athlete_fields(source_row, existing)
            summary["updated"] += 1
            log_lines.append(
                f"[athletes] UPDATE sync_id={source_row.sync_id} name={source_row.first_name}"
            )
            continue

        if _records_differ(existing, payload, compare_fields):
            conflict = _make_conflict(
                table_name="athletes",
                sync_id=source_row.sync_id,
                reason="target_newer_than_source",
                source_updated_at=source_row.updated_at,
                target_updated_at=existing.updated_at,
                source_version_id=source_row.version_id,
                target_version_id=existing.version_id,
                details=f"name={source_row.first_name}",
            )
            conflicts.append(conflict)
            summary["conflicts"] += 1
            log_lines.append(
                f"[athletes] CONFLICT sync_id={source_row.sync_id} reason=target_newer_than_source"
            )
        else:
            summary["skipped"] += 1
            log_lines.append(
                f"[athletes] SKIP sync_id={source_row.sync_id} reason=already_in_sync"
            )

    return summary


def _sync_events(
    *,
    source_session: Session,
    target_session: Session,
    conflicts: list[dict[str, Any]],
    log_lines: list[str],
    changed_since: datetime | None,
) -> dict[str, int]:
    summary = _empty_summary()

    stmt = select(Event).order_by(Event.id.asc())
    if changed_since is not None:
        stmt = stmt.where(Event.updated_at >= changed_since)

    source_rows = list(source_session.scalars(stmt).all())
    summary["scanned"] = len(source_rows)

    compare_fields = [
        "name",
        "event_date",
        "season",
        "notes",
    ]

    for source_row in source_rows:
        existing = target_session.scalar(
            select(Event).where(Event.sync_id == source_row.sync_id)
        )

        if existing is None:
            target_session.add(Event(**_build_event_insert_payload(source_row)))
            summary["inserted"] += 1
            log_lines.append(
                f"[events] INSERT sync_id={source_row.sync_id} name={source_row.name}"
            )
            continue

        payload = _build_event_insert_payload(source_row)

        if _is_source_newer(
            source_updated_at=source_row.updated_at,
            target_updated_at=existing.updated_at,
            source_version_id=source_row.version_id,
            target_version_id=existing.version_id,
        ):
            _copy_event_fields(source_row, existing)
            summary["updated"] += 1
            log_lines.append(
                f"[events] UPDATE sync_id={source_row.sync_id} name={source_row.name}"
            )
            continue

        if _records_differ(existing, payload, compare_fields):
            conflict = _make_conflict(
                table_name="events",
                sync_id=source_row.sync_id,
                reason="target_newer_than_source",
                source_updated_at=source_row.updated_at,
                target_updated_at=existing.updated_at,
                source_version_id=source_row.version_id,
                target_version_id=existing.version_id,
                details=f"name={source_row.name}",
            )
            conflicts.append(conflict)
            summary["conflicts"] += 1
            log_lines.append(
                f"[events] CONFLICT sync_id={source_row.sync_id} reason=target_newer_than_source"
            )
        else:
            summary["skipped"] += 1
            log_lines.append(
                f"[events] SKIP sync_id={source_row.sync_id} reason=already_in_sync"
            )

    return summary


def _resolve_match_payload(
    *,
    source_match: Match,
    source_athlete_sync_by_id: dict[int, str],
    source_event_sync_by_id: dict[int, str],
    target_athlete_id_by_sync: dict[str, int],
    target_event_id_by_sync: dict[str, int],
) -> tuple[dict[str, Any] | None, str | None]:
    event_sync_id = source_match.event_sync_id or source_event_sync_by_id.get(source_match.event_id)
    athlete_a_sync_id = source_match.athlete_a_sync_id or source_athlete_sync_by_id.get(source_match.athlete_a_id)
    athlete_b_sync_id = source_match.athlete_b_sync_id or source_athlete_sync_by_id.get(source_match.athlete_b_id)

    winner_sync_id = source_match.winner_sync_id
    if winner_sync_id is None and source_match.winner_id is not None:
        winner_sync_id = source_athlete_sync_by_id.get(source_match.winner_id)

    if not event_sync_id:
        return None, "missing_source_event_sync_id"

    if not athlete_a_sync_id or not athlete_b_sync_id:
        return None, "missing_source_athlete_sync_id"

    target_event_id = target_event_id_by_sync.get(event_sync_id)
    target_athlete_a_id = target_athlete_id_by_sync.get(athlete_a_sync_id)
    target_athlete_b_id = target_athlete_id_by_sync.get(athlete_b_sync_id)

    if target_event_id is None:
        return None, "missing_target_event_reference"

    if target_athlete_a_id is None or target_athlete_b_id is None:
        return None, "missing_target_athlete_reference"

    target_winner_id = None
    if winner_sync_id:
        target_winner_id = target_athlete_id_by_sync.get(winner_sync_id)
        if target_winner_id is None:
            return None, "missing_target_winner_reference"

    target_token_spender_id = None
    if source_match.token_spender_id is not None:
        token_spender_sync_id = source_athlete_sync_by_id.get(source_match.token_spender_id)
        if token_spender_sync_id:
            target_token_spender_id = target_athlete_id_by_sync.get(token_spender_sync_id)
            if target_token_spender_id is None:
                return None, "missing_target_token_spender_reference"

    payload = {
        "event_id": target_event_id,
        "athlete_a_id": target_athlete_a_id,
        "athlete_b_id": target_athlete_b_id,
        "style": source_match.style,
        "weight_a": source_match.weight_a,
        "weight_b": source_match.weight_b,
        "level_a": source_match.level_a,
        "level_b": source_match.level_b,
        "raw_score_a": source_match.raw_score_a,
        "raw_score_b": source_match.raw_score_b,
        "winner_id": target_winner_id,
        "win_type": source_match.win_type,
        "points_a": source_match.points_a,
        "points_b": source_match.points_b,
        "is_token_match": source_match.is_token_match,
        "token_spender_id": target_token_spender_id,
        "token_cost": source_match.token_cost,
        "notes": source_match.notes,
        "event_sync_id": event_sync_id,
        "athlete_a_sync_id": athlete_a_sync_id,
        "athlete_b_sync_id": athlete_b_sync_id,
        "winner_sync_id": winner_sync_id,
        "sync_id": source_match.sync_id,
        "created_at": source_match.created_at,
        "updated_at": source_match.updated_at,
        "version_id": source_match.version_id,
    }

    return payload, None


def _copy_match_fields(payload: dict[str, Any], target: Match) -> None:
    target.event_id = payload["event_id"]
    target.athlete_a_id = payload["athlete_a_id"]
    target.athlete_b_id = payload["athlete_b_id"]
    target.style = payload["style"]
    target.weight_a = payload["weight_a"]
    target.weight_b = payload["weight_b"]
    target.level_a = payload["level_a"]
    target.level_b = payload["level_b"]
    target.raw_score_a = payload["raw_score_a"]
    target.raw_score_b = payload["raw_score_b"]
    target.winner_id = payload["winner_id"]
    target.win_type = payload["win_type"]
    target.points_a = payload["points_a"]
    target.points_b = payload["points_b"]
    target.is_token_match = payload["is_token_match"]
    target.token_spender_id = payload["token_spender_id"]
    target.token_cost = payload["token_cost"]
    target.notes = payload["notes"]
    target.event_sync_id = payload["event_sync_id"]
    target.athlete_a_sync_id = payload["athlete_a_sync_id"]
    target.athlete_b_sync_id = payload["athlete_b_sync_id"]
    target.winner_sync_id = payload["winner_sync_id"]


def _sync_matches(
    *,
    source_session: Session,
    target_session: Session,
    conflicts: list[dict[str, Any]],
    log_lines: list[str],
    changed_since: datetime | None,
) -> dict[str, int]:
    summary = _empty_summary()

    source_athletes = list(source_session.scalars(select(Athlete)).all())
    source_events = list(source_session.scalars(select(Event)).all())
    target_athletes = list(target_session.scalars(select(Athlete)).all())
    target_events = list(target_session.scalars(select(Event)).all())

    source_athlete_sync_by_id = {row.id: row.sync_id for row in source_athletes}
    source_event_sync_by_id = {row.id: row.sync_id for row in source_events}
    target_athlete_id_by_sync = {row.sync_id: row.id for row in target_athletes}
    target_event_id_by_sync = {row.sync_id: row.id for row in target_events}

    stmt = select(Match).order_by(Match.id.asc())
    if changed_since is not None:
        stmt = stmt.where(Match.updated_at >= changed_since)

    source_rows = list(source_session.scalars(stmt).all())
    summary["scanned"] = len(source_rows)

    compare_fields = [
        "event_id",
        "athlete_a_id",
        "athlete_b_id",
        "style",
        "weight_a",
        "weight_b",
        "level_a",
        "level_b",
        "raw_score_a",
        "raw_score_b",
        "winner_id",
        "win_type",
        "points_a",
        "points_b",
        "is_token_match",
        "token_spender_id",
        "token_cost",
        "notes",
        "event_sync_id",
        "athlete_a_sync_id",
        "athlete_b_sync_id",
        "winner_sync_id",
    ]

    for source_row in source_rows:
        payload, payload_error = _resolve_match_payload(
            source_match=source_row,
            source_athlete_sync_by_id=source_athlete_sync_by_id,
            source_event_sync_by_id=source_event_sync_by_id,
            target_athlete_id_by_sync=target_athlete_id_by_sync,
            target_event_id_by_sync=target_event_id_by_sync,
        )

        if payload is None:
            conflict = _make_conflict(
                table_name="matches",
                sync_id=source_row.sync_id,
                reason=payload_error or "payload_resolution_error",
                source_updated_at=source_row.updated_at,
                target_updated_at=None,
                source_version_id=source_row.version_id,
                target_version_id=None,
                details="Impossibile risolvere le foreign key nel target.",
            )
            conflicts.append(conflict)
            summary["conflicts"] += 1
            log_lines.append(
                f"[matches] CONFLICT sync_id={source_row.sync_id} reason={payload_error or 'payload_resolution_error'}"
            )
            continue

        existing = target_session.scalar(
            select(Match).where(Match.sync_id == source_row.sync_id)
        )

        if existing is None:
            target_session.add(Match(**payload))
            summary["inserted"] += 1
            log_lines.append(
                f"[matches] INSERT sync_id={source_row.sync_id}"
            )
            continue

        if _is_source_newer(
            source_updated_at=source_row.updated_at,
            target_updated_at=existing.updated_at,
            source_version_id=source_row.version_id,
            target_version_id=existing.version_id,
        ):
            _copy_match_fields(payload, existing)
            summary["updated"] += 1
            log_lines.append(
                f"[matches] UPDATE sync_id={source_row.sync_id}"
            )
            continue

        if _records_differ(existing, payload, compare_fields):
            conflict = _make_conflict(
                table_name="matches",
                sync_id=source_row.sync_id,
                reason="target_newer_than_source",
                source_updated_at=source_row.updated_at,
                target_updated_at=existing.updated_at,
                source_version_id=source_row.version_id,
                target_version_id=existing.version_id,
                details="Record presente nel target ma più recente del sorgente.",
            )
            conflicts.append(conflict)
            summary["conflicts"] += 1
            log_lines.append(
                f"[matches] CONFLICT sync_id={source_row.sync_id} reason=target_newer_than_source"
            )
        else:
            summary["skipped"] += 1
            log_lines.append(
                f"[matches] SKIP sync_id={source_row.sync_id} reason=already_in_sync"
            )

    return summary


def _build_log_text(
    *,
    source_environment: str,
    target_environment: str,
    changed_since: str | None,
    started_at: str,
    finished_at: str,
    summary: dict[str, dict[str, int]],
    conflicts: list[dict[str, Any]],
    ok: bool,
    error_message: str | None,
    log_lines: list[str],
    anteprima_sync: bool,
) -> str:
    lines: list[str] = []
    lines.append("SYNC REPORT")
    lines.append("===========")
    lines.append(f"Mode: {'ANTEPRIMA_SYNC' if anteprima_sync else 'APPLY_SYNC'}")
    lines.append(f"Source environment: {source_environment}")
    lines.append(f"Target environment: {target_environment}")
    lines.append(f"Changed since: {changed_since or 'FULL_SYNC'}")
    lines.append(f"Started at: {started_at}")
    lines.append(f"Finished at: {finished_at}")
    lines.append(f"Result: {'OK' if ok else 'ERROR'}")

    if error_message:
        lines.append(f"Error: {error_message}")

    lines.append("")
    lines.append("SUMMARY")
    lines.append("-------")

    for table_name, table_summary in summary.items():
        lines.append(f"[{table_name}]")
        lines.append(f"scanned={table_summary['scanned']}")
        lines.append(f"inserted={table_summary['inserted']}")
        lines.append(f"updated={table_summary['updated']}")
        lines.append(f"skipped={table_summary['skipped']}")
        lines.append(f"conflicts={table_summary['conflicts']}")
        lines.append("")

    lines.append("CONFLICTS")
    lines.append("---------")

    if not conflicts:
        lines.append("No conflicts.")
    else:
        for index, conflict in enumerate(conflicts, start=1):
            lines.append(f"[{index}] table={conflict['table']} sync_id={conflict['sync_id']}")
            lines.append(f"reason={conflict['reason']}")
            lines.append(f"source_updated_at={conflict['source_updated_at']}")
            lines.append(f"target_updated_at={conflict['target_updated_at']}")
            lines.append(f"source_version_id={conflict['source_version_id']}")
            lines.append(f"target_version_id={conflict['target_version_id']}")
            if conflict.get("details"):
                lines.append(f"details={conflict['details']}")
            lines.append("")

    lines.append("ACTIONS")
    lines.append("-------")
    lines.extend(log_lines)

    return "\n".join(lines)


def sync_raw_data(
    *,
    source_environment: str,
    source_mode: str,
    source_sqlite_path: str = "",
    source_postgres_url: str = "",
    target_environment: str,
    target_mode: str,
    target_sqlite_path: str = "",
    target_postgres_url: str = "",
    changed_since: str | None = None,
    anteprima_sync: bool = False,
) -> dict[str, Any]:
    if not can_sync_between_environments(source_environment, target_environment):
        raise ValueError(
            "Sincronizzazione non consentita tra questi ambienti."
        )

    changed_since_dt = _parse_changed_since(changed_since)

    started_at = _utc_now_iso()
    finished_at = started_at
    ok = False
    error_message: str | None = None
    conflicts: list[dict[str, Any]] = []
    log_lines: list[str] = []
    summary: dict[str, dict[str, int]] = {
        "athletes": _empty_summary(),
        "events": _empty_summary(),
        "matches": _empty_summary(),
    }

    source_engine = None
    target_engine = None

    try:
        source_engine, source_session_factory = _build_session_factory(
            mode=source_mode,
            sqlite_path=source_sqlite_path,
            postgres_url=source_postgres_url,
        )
        target_engine, target_session_factory = _build_session_factory(
            mode=target_mode,
            sqlite_path=target_sqlite_path,
            postgres_url=target_postgres_url,
        )

        with source_session_factory() as source_session, target_session_factory() as target_session:
            summary["athletes"] = _sync_athletes(
                source_session=source_session,
                target_session=target_session,
                conflicts=conflicts,
                log_lines=log_lines,
                changed_since=changed_since_dt,
            )
            if anteprima_sync:
                target_session.flush()
            else:
                target_session.commit()

            summary["events"] = _sync_events(
                source_session=source_session,
                target_session=target_session,
                conflicts=conflicts,
                log_lines=log_lines,
                changed_since=changed_since_dt,
            )
            if anteprima_sync:
                target_session.flush()
            else:
                target_session.commit()

            summary["matches"] = _sync_matches(
                source_session=source_session,
                target_session=target_session,
                conflicts=conflicts,
                log_lines=log_lines,
                changed_since=changed_since_dt,
            )
            if anteprima_sync:
                target_session.flush()
                target_session.rollback()
                log_lines.append(
                    "[sync] ANTEPRIMA_SYNC completata: nessuna modifica è stata salvata."
                )
            else:
                target_session.commit()

        ok = True

    except Exception as exc:
        error_message = str(exc)
        log_lines.append(f"[error] {error_message}")

    finally:
        finished_at = _utc_now_iso()

        if source_engine is not None:
            source_engine.dispose()

        if target_engine is not None:
            target_engine.dispose()

    log_text = _build_log_text(
        source_environment=source_environment,
        target_environment=target_environment,
        changed_since=changed_since,
        started_at=started_at,
        finished_at=finished_at,
        summary=summary,
        conflicts=conflicts,
        ok=ok,
        error_message=error_message,
        log_lines=log_lines,
        anteprima_sync=anteprima_sync,
    )

    return {
        "ok": ok,
        "error_message": error_message,
        "source_environment": source_environment,
        "target_environment": target_environment,
        "changed_since": changed_since,
        "anteprima_sync": anteprima_sync,
        "started_at": started_at,
        "finished_at": finished_at,
        "summary": summary,
        "conflicts": conflicts,
        "log_text": log_text,
    }