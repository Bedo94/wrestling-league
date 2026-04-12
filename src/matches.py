from datetime import date
from functools import lru_cache
from typing import Optional, TypedDict

from sqlalchemy import func, select

from src.database import get_database_url, get_session
from src.models import Athlete, Event, Match
from src.query_cache import (
    DOMAIN_ATHLETES,
    DOMAIN_EVENTS,
    DOMAIN_MATCHES,
    build_signature,
    bump_cache_version,
    get_cache_version,
)
from src.reference_data import WIN_TYPE_OPTIONS
from src.scoring import MatchPointsPreview, calculate_match_points
from src.settings import SCORING_SETTINGS, TOKEN_SETTINGS
from src.token_usage import (
    get_token_spender_id_from_used_by,
    get_token_used_by_from_spender_id,
)


class DerivedMatchPoints(TypedDict):
    points_a: float
    points_b: float

def _validate_match_inputs(
    athlete_a_id: int,
    athlete_b_id: int,
    raw_score_a: float,
    raw_score_b: float,
    winner_id: Optional[int],
    win_type: str,
) -> None:
    if athlete_a_id == athlete_b_id:
        raise ValueError("Un atleta non può affrontare sé stesso.")

    if winner_id is None:
        raise ValueError(
            "winner_id è obbligatorio finché il pareggio non sarà gestito nello scoring."
        )

    if winner_id not in {athlete_a_id, athlete_b_id}:
        raise ValueError("Il vincitore deve essere uno dei due atleti del match.")

    if raw_score_a < 0 or raw_score_b < 0:
        raise ValueError("I punti del match non possono essere negativi.")

    if win_type not in WIN_TYPE_OPTIONS:
        raise ValueError("Tipo di vittoria non valido.")


def _normalize_token_fields(
    athlete_a_id: int,
    athlete_b_id: int,
    token_spender_id: Optional[int],
) -> Optional[int]:
    token_used_by = get_token_used_by_from_spender_id(
        athlete_a_id=athlete_a_id,
        athlete_b_id=athlete_b_id,
        token_spender_id=token_spender_id,
    )
    if token_used_by is None:
        return None

    normalized_token_spender_id = get_token_spender_id_from_used_by(
        athlete_a_id=athlete_a_id,
        athlete_b_id=athlete_b_id,
        token_used_by=token_used_by,
    )
    assert normalized_token_spender_id is not None

    return normalized_token_spender_id


def _get_tokens_used_in_event(
    session,
    athlete_id: int,
    event_id: int,
    exclude_match_id: Optional[int] = None,
) -> int:
    stmt = select(func.count(Match.id)).where(
        Match.token_spender_id == athlete_id,
        Match.event_id == event_id,
    )

    if exclude_match_id is not None:
        stmt = stmt.where(Match.id != exclude_match_id)

    total = session.execute(stmt).scalar_one()
    return int(total or 0)


def _validate_token_usage(
    session,
    athlete_a_id: int,
    athlete_b_id: int,
    *,
    event_id: Optional[int],
    token_spender_id: Optional[int],
    exclude_match_id: Optional[int] = None,
) -> Optional[int]:
    token_spender_id = _normalize_token_fields(
        athlete_a_id=athlete_a_id,
        athlete_b_id=athlete_b_id,
        token_spender_id=token_spender_id,
    )

    if token_spender_id is None:
        return None

    token_spender = session.get(Athlete, token_spender_id)
    if token_spender is None:
        raise ValueError("Atleta che spende il token non trovato.")

    assert token_spender_id is not None
    if event_id is None:
        raise ValueError("event_id obbligatorio per validare i token.")

    used_tokens = _get_tokens_used_in_event(
        session=session,
        athlete_id=token_spender_id,
        event_id=event_id,
        exclude_match_id=exclude_match_id,
    )

    remaining_tokens = int(TOKEN_SETTINGS["default_token_budget_per_event"]) - used_tokens
    if remaining_tokens < 1:
        raise ValueError(
            f"{token_spender.first_name} non ha abbastanza token disponibili per questo evento."
        )
    
    return token_spender_id


def _require_sync_id(entity, entity_label: str) -> str:
    sync_id = getattr(entity, "sync_id", None)
    if not sync_id:
        raise ValueError(f"{entity_label} senza sync_id: impossibile creare/allineare il match.")
    return sync_id


def populate_match_sync_fields(
    *,
    match: Match,
    event: Event,
    athlete_a: Athlete,
    athlete_b: Athlete,
    winner: Athlete | None = None,
    token_spender: Athlete | None = None,
) -> None:
    match.event_sync_id = _require_sync_id(event, "Evento")
    match.athlete_a_sync_id = _require_sync_id(athlete_a, "Athlete A")
    match.athlete_b_sync_id = _require_sync_id(athlete_b, "Athlete B")
    match.winner_sync_id = (
        _require_sync_id(winner, "Vincitore") if winner is not None else None
    )
    match.token_spender_sync_id = (
        _require_sync_id(token_spender, "Token spender")
        if token_spender is not None
        else None
    )


def _load_match_entities(
    session,
    *,
    event_id: int,
    athlete_a_id: int,
    athlete_b_id: int,
    winner_id: Optional[int],
    token_spender_id: Optional[int],
) -> tuple[Event, Athlete, Athlete, Optional[Athlete], Optional[Athlete]]:
    event = session.get(Event, event_id)
    if event is None:
        raise ValueError(f"Evento con ID {event_id} non trovato.")

    athlete_a = session.get(Athlete, athlete_a_id)
    if athlete_a is None:
        raise ValueError(f"Atleta A con ID {athlete_a_id} non trovato.")

    athlete_b = session.get(Athlete, athlete_b_id)
    if athlete_b is None:
        raise ValueError(f"Atleta B con ID {athlete_b_id} non trovato.")

    winner = None
    if winner_id is not None:
        winner = session.get(Athlete, winner_id)
        if winner is None:
            raise ValueError(f"Vincitore con ID {winner_id} non trovato.")

    token_spender = None
    if token_spender_id is not None:
        token_spender = session.get(Athlete, token_spender_id)
        if token_spender is None:
            raise ValueError(f"Token spender con ID {token_spender_id} non trovato.")

    return event, athlete_a, athlete_b, winner, token_spender


def _build_match(
    event_id: int,
    athlete_a_id: int,
    athlete_b_id: int,
    style: str,
    weight_a: float,
    weight_b: float,
    level_a: int,
    level_b: int,
    raw_score_a: float,
    raw_score_b: float,
    winner_id: Optional[int],
    win_type: str,
    token_spender_id: Optional[int],
    notes: Optional[str] = None,
) -> Match:
    return Match(
        event_id=event_id,
        athlete_a_id=athlete_a_id,
        athlete_b_id=athlete_b_id,
        style=style,
        weight_a=weight_a,
        weight_b=weight_b,
        level_a=level_a,
        level_b=level_b,
        raw_score_a=raw_score_a,
        raw_score_b=raw_score_b,
        winner_id=winner_id,
        win_type=win_type,
        token_spender_id=token_spender_id,
        notes=(notes or "").strip() or None,
    )


def _apply_match_fields(
    *,
    match: Match,
    event_id: int,
    athlete_a_id: int,
    athlete_b_id: int,
    style: str,
    weight_a: float,
    weight_b: float,
    level_a: int,
    level_b: int,
    raw_score_a: float,
    raw_score_b: float,
    winner_id: Optional[int],
    win_type: str,
    token_spender_id: Optional[int],
    notes: Optional[str],
) -> None:
    match.event_id = event_id
    match.athlete_a_id = athlete_a_id
    match.athlete_b_id = athlete_b_id
    match.style = style
    match.weight_a = weight_a
    match.weight_b = weight_b
    match.level_a = level_a
    match.level_b = level_b
    match.raw_score_a = raw_score_a
    match.raw_score_b = raw_score_b
    match.winner_id = winner_id
    match.win_type = win_type
    match.token_spender_id = token_spender_id
    match.notes = (notes or "").strip() or None


def _calculate_score_data(
    athlete_a_id: int,
    athlete_b_id: int,
    winner_id: Optional[int],
    win_type: str,
    weight_a: float,
    weight_b: float,
    raw_score_a: float,
    raw_score_b: float,
    athlete_a_sex: str,
    athlete_b_sex: str,
    athlete_a_birth_date: date,
    athlete_b_birth_date: date,
    event_date: date,
) -> MatchPointsPreview:
    _validate_match_inputs(
        athlete_a_id=athlete_a_id,
        athlete_b_id=athlete_b_id,
        raw_score_a=raw_score_a,
        raw_score_b=raw_score_b,
        winner_id=winner_id,
        win_type=win_type,
    )

    assert winner_id is not None

    return calculate_match_points(
        athlete_a_id=athlete_a_id,
        athlete_b_id=athlete_b_id,
        winner_id=winner_id,
        win_type=win_type,
        weight_a=weight_a,
        weight_b=weight_b,
        raw_score_a=raw_score_a,
        raw_score_b=raw_score_b,
        athlete_a_sex=athlete_a_sex,
        athlete_b_sex=athlete_b_sex,
        athlete_a_birth_date=athlete_a_birth_date,
        athlete_b_birth_date=athlete_b_birth_date,
        event_date=event_date,
    )


def derive_match_points(
    *,
    match: Match,
    event: Event,
    athlete_a: Athlete,
    athlete_b: Athlete,
) -> DerivedMatchPoints:
    if match.winner_id is None or match.win_type is None:
        raise ValueError("Il match non ha ancora un vincitore o un tipo di vittoria valido.")

    score_data = _calculate_score_data(
        athlete_a_id=match.athlete_a_id,
        athlete_b_id=match.athlete_b_id,
        winner_id=match.winner_id,
        win_type=match.win_type,
        weight_a=float(match.weight_a),
        weight_b=float(match.weight_b),
        raw_score_a=float(match.raw_score_a),
        raw_score_b=float(match.raw_score_b),
        athlete_a_sex=athlete_a.sex,
        athlete_b_sex=athlete_b.sex,
        athlete_a_birth_date=athlete_a.birth_date,
        athlete_b_birth_date=athlete_b.birth_date,
        event_date=event.event_date,
    )
    return {
        "points_a": float(score_data["total_points_a"]),
        "points_b": float(score_data["total_points_b"]),
    }


def _fallback_derived_match_points(match: Match) -> DerivedMatchPoints:
    return {
        "points_a": 0.0,
        "points_b": 0.0,
    }


def build_match_points_map_from_loaded(
    *,
    matches: list[Match],
    events_by_id: dict[int, Event],
    athletes_by_id: dict[int, Athlete],
) -> dict[int, DerivedMatchPoints]:
    points_by_match_id: dict[int, DerivedMatchPoints] = {}

    for match in matches:
        event = events_by_id.get(match.event_id)
        athlete_a = athletes_by_id.get(match.athlete_a_id)
        athlete_b = athletes_by_id.get(match.athlete_b_id)

        if event is None or athlete_a is None or athlete_b is None:
            points_by_match_id[match.id] = _fallback_derived_match_points(match)
            continue

        try:
            points_by_match_id[match.id] = derive_match_points(
                match=match,
                event=event,
                athlete_a=athlete_a,
                athlete_b=athlete_b,
            )
        except ValueError:
            points_by_match_id[match.id] = _fallback_derived_match_points(match)

    return points_by_match_id


@lru_cache(maxsize=32)
def _build_match_points_map_cached(
    database_url: str,
    athletes_version: int,
    events_version: int,
    matches_version: int,
    scoring_signature: str,
) -> tuple[tuple[int, float, float], ...]:
    session = get_session()
    try:
        matches = list(session.scalars(select(Match).order_by(Match.id.asc())).all())
        events = list(session.scalars(select(Event)).all())
        athletes = list(session.scalars(select(Athlete)).all())

        points_by_match_id = build_match_points_map_from_loaded(
            matches=matches,
            events_by_id={event.id: event for event in events},
            athletes_by_id={athlete.id: athlete for athlete in athletes},
        )

        return tuple(
            (
                match_id,
                float(values["points_a"]),
                float(values["points_b"]),
            )
            for match_id, values in sorted(points_by_match_id.items())
        )
    finally:
        session.close()


def build_match_points_map() -> dict[int, DerivedMatchPoints]:
    """
    Calcola i punti classifica dei match senza scrivere nel DB.

    Per record incompleti o non ricalcolabili mantiene un fallback
    neutro a zero, così il read-side resta stabile durante la transizione.
    """
    cached_rows = _build_match_points_map_cached(
        get_database_url(hide_password=False),
        get_cache_version(DOMAIN_ATHLETES),
        get_cache_version(DOMAIN_EVENTS),
        get_cache_version(DOMAIN_MATCHES),
        build_signature(SCORING_SETTINGS),
    )
    return {
        match_id: {
            "points_a": points_a,
            "points_b": points_b,
        }
        for match_id, points_a, points_b in cached_rows
    }


def create_match(
    event_id: int,
    athlete_a_id: int,
    athlete_b_id: int,
    style: str,
    weight_a: float,
    weight_b: float,
    level_a: int,
    level_b: int,
    raw_score_a: float,
    raw_score_b: float,
    athlete_a_sex: str,
    athlete_b_sex: str,
    athlete_a_birth_date: date,
    athlete_b_birth_date: date,
    event_date: date,
    winner_id: Optional[int],
    win_type: str,
    token_spender_id: Optional[int] = None,
    notes: Optional[str] = None,
) -> Match:
    _calculate_score_data(
        athlete_a_id=athlete_a_id,
        athlete_b_id=athlete_b_id,
        winner_id=winner_id,
        win_type=win_type,
        weight_a=weight_a,
        weight_b=weight_b,
        raw_score_a=raw_score_a,
        raw_score_b=raw_score_b,
        athlete_a_sex=athlete_a_sex,
        athlete_b_sex=athlete_b_sex,
        athlete_a_birth_date=athlete_a_birth_date,
        athlete_b_birth_date=athlete_b_birth_date,
        event_date=event_date,
    )

    session = get_session()
    try:
        event = session.get(Event, event_id)
        if event is None:
            raise ValueError(f"Evento con ID {event_id} non trovato.")

        token_spender_id = _validate_token_usage(
            session=session,
            athlete_a_id=athlete_a_id,
            athlete_b_id=athlete_b_id,
            event_id=event.id,
            token_spender_id=token_spender_id,
        )

        event, athlete_a, athlete_b, winner, token_spender = _load_match_entities(
            session,
            event_id=event_id,
            athlete_a_id=athlete_a_id,
            athlete_b_id=athlete_b_id,
            winner_id=winner_id,
            token_spender_id=token_spender_id,
        )

        match = _build_match(
            event_id=event_id,
            athlete_a_id=athlete_a_id,
            athlete_b_id=athlete_b_id,
            style=style,
            weight_a=weight_a,
            weight_b=weight_b,
            level_a=level_a,
            level_b=level_b,
            raw_score_a=raw_score_a,
            raw_score_b=raw_score_b,
            winner_id=winner_id,
            win_type=win_type,
            token_spender_id=token_spender_id,
            notes=notes,
        )

        populate_match_sync_fields(
            match=match,
            event=event,
            athlete_a=athlete_a,
            athlete_b=athlete_b,
            winner=winner,
            token_spender=token_spender,
        )

        session.add(match)
        session.commit()
        session.refresh(match)
        session.expunge(match)
        bump_cache_version(DOMAIN_MATCHES)
        return match
    finally:
        session.close()


def replace_match(
    match_id: int,
    event_id: int,
    athlete_a_id: int,
    athlete_b_id: int,
    style: str,
    weight_a: float,
    weight_b: float,
    level_a: int,
    level_b: int,
    raw_score_a: float,
    raw_score_b: float,
    athlete_a_sex: str,
    athlete_b_sex: str,
    athlete_a_birth_date: date,
    athlete_b_birth_date: date,
    event_date: date,
    winner_id: Optional[int],
    win_type: str,
    token_spender_id: Optional[int] = None,
    notes: Optional[str] = None,
) -> Match:
    _calculate_score_data(
        athlete_a_id=athlete_a_id,
        athlete_b_id=athlete_b_id,
        winner_id=winner_id,
        win_type=win_type,
        weight_a=weight_a,
        weight_b=weight_b,
        raw_score_a=raw_score_a,
        raw_score_b=raw_score_b,
        athlete_a_sex=athlete_a_sex,
        athlete_b_sex=athlete_b_sex,
        athlete_a_birth_date=athlete_a_birth_date,
        athlete_b_birth_date=athlete_b_birth_date,
        event_date=event_date,
    )

    session = get_session()
    try:
        with session.begin():
            existing_match = session.get(Match, match_id)
            if existing_match is None:
                raise ValueError(f"Incontro con ID {match_id} non trovato.")

            event = session.get(Event, event_id)
            if event is None:
                raise ValueError(f"Evento con ID {event_id} non trovato.")

            token_spender_id = _validate_token_usage(
                session=session,
                athlete_a_id=athlete_a_id,
                athlete_b_id=athlete_b_id,
                event_id=event.id,
                token_spender_id=token_spender_id,
                exclude_match_id=match_id,
            )

            event, athlete_a, athlete_b, winner, token_spender = _load_match_entities(
                session,
                event_id=event_id,
                athlete_a_id=athlete_a_id,
                athlete_b_id=athlete_b_id,
                winner_id=winner_id,
                token_spender_id=token_spender_id,
            )

            _apply_match_fields(
                match=existing_match,
                event_id=event_id,
                athlete_a_id=athlete_a_id,
                athlete_b_id=athlete_b_id,
                style=style,
                weight_a=weight_a,
                weight_b=weight_b,
                level_a=level_a,
                level_b=level_b,
                raw_score_a=raw_score_a,
                raw_score_b=raw_score_b,
                winner_id=winner_id,
                win_type=win_type,
                token_spender_id=token_spender_id,
                notes=notes,
            )

            populate_match_sync_fields(
                match=existing_match,
                event=event,
                athlete_a=athlete_a,
                athlete_b=athlete_b,
                winner=winner,
                token_spender=token_spender,
            )

            session.flush()

        session.refresh(existing_match)
        session.expunge(existing_match)
        bump_cache_version(DOMAIN_MATCHES)
        return existing_match
    finally:
        session.close()


def delete_match(match_id: int) -> None:
    session = get_session()
    try:
        with session.begin():
            match = session.get(Match, match_id)
            if match is None:
                raise ValueError(f"Incontro con ID {match_id} non trovato.")
            session.delete(match)
        bump_cache_version(DOMAIN_MATCHES)
    finally:
        session.close()


@lru_cache(maxsize=32)
def _list_matches_cached(database_url: str, version: int) -> tuple[Match, ...]:
    session = get_session()
    try:
        stmt = select(Match).order_by(Match.id.desc())
        return tuple(session.scalars(stmt).all())
    finally:
        session.close()


def list_matches() -> list[Match]:
    return list(
        _list_matches_cached(
            get_database_url(hide_password=False),
            get_cache_version(DOMAIN_MATCHES),
        )
    )

def recompute_all_match_scores() -> int:
    session = get_session()
    processed_count = 0

    try:
        matches = list(session.scalars(select(Match).order_by(Match.id.asc())).all())

        for match in matches:
            event = session.get(Event, match.event_id)
            athlete_a = session.get(Athlete, match.athlete_a_id)
            athlete_b = session.get(Athlete, match.athlete_b_id)

            if event is None or athlete_a is None or athlete_b is None:
                continue

            if match.win_type is None:
                continue

            try:
                derive_match_points(
                    match=match,
                    event=event,
                    athlete_a=athlete_a,
                    athlete_b=athlete_b,
                )
            except ValueError as exc:
                athlete_a_name = f"{athlete_a.first_name} {athlete_a.last_name or ''}".strip()
                athlete_b_name = f"{athlete_b.first_name} {athlete_b.last_name or ''}".strip()
                raise ValueError(
                    f"Impossibile ricalcolare il match ID {match.id} "
                    f"({athlete_a_name} vs {athlete_b_name}): {exc}"
                ) from exc

            processed_count += 1

        return processed_count
    except Exception:
        raise
    finally:
        session.close()


def backfill_match_sync_fields() -> int:
    session = get_session()
    updated_count = 0

    try:
        matches = session.scalars(select(Match).order_by(Match.id.asc())).all()

        for match in matches:
            event = session.get(Event, match.event_id)
            athlete_a = session.get(Athlete, match.athlete_a_id)
            athlete_b = session.get(Athlete, match.athlete_b_id)

            winner = (
                session.get(Athlete, match.winner_id)
                if match.winner_id is not None
                else None
            )

            token_spender = (
                session.get(Athlete, match.token_spender_id)
                if match.token_spender_id is not None
                else None
            )

            if event is None or athlete_a is None or athlete_b is None:
                continue

            before = (
                match.event_sync_id,
                match.athlete_a_sync_id,
                match.athlete_b_sync_id,
                match.winner_sync_id,
                match.token_spender_sync_id,
            )

            populate_match_sync_fields(
                match=match,
                event=event,
                athlete_a=athlete_a,
                athlete_b=athlete_b,
                winner=winner,
                token_spender=token_spender,
            )

            after = (
                match.event_sync_id,
                match.athlete_a_sync_id,
                match.athlete_b_sync_id,
                match.winner_sync_id,
                match.token_spender_sync_id,
            )

            if before != after:
                updated_count += 1

        session.commit()
        if updated_count:
            bump_cache_version(DOMAIN_MATCHES)
        return updated_count
    finally:
        session.close()
