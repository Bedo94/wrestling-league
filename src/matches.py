from datetime import date
from typing import Optional

from sqlalchemy import func, select

from src.database import get_session
from src.models import Athlete, Event, Match
from src.reference_data import WIN_TYPE_OPTIONS
from src.scoring import calculate_match_points
from src.settings import TOKEN_SETTINGS


def _validate_match_inputs(
    athlete_a_id: int,
    athlete_b_id: int,
    raw_score_a: float,
    raw_score_b: float,
    winner_id: int,
    win_type: str,
) -> None:
    if athlete_a_id == athlete_b_id:
        raise ValueError("Un atleta non può affrontare sé stesso.")

    if winner_id not in {athlete_a_id, athlete_b_id}:
        raise ValueError("Il vincitore deve essere uno dei due atleti del match.")

    if raw_score_a < 0 or raw_score_b < 0:
        raise ValueError("I punti del match non possono essere negativi.")

    if win_type not in WIN_TYPE_OPTIONS:
        raise ValueError("Tipo di vittoria non valido.")


def _normalize_token_fields(
    athlete_a_id: int,
    athlete_b_id: int,
    is_token_match: bool,
    token_spender_id: Optional[int],
    token_cost: int,
) -> tuple[bool, Optional[int], int]:
    if not is_token_match:
        return False, None, 0

    if token_spender_id is None:
        raise ValueError("Devi indicare quale atleta spende il token.")

    if token_spender_id not in {athlete_a_id, athlete_b_id}:
        raise ValueError("L'atleta che spende il token deve essere uno dei due partecipanti.")

    if token_cost <= 0:
        raise ValueError("Il costo token deve essere maggiore di zero.")

    return True, token_spender_id, token_cost


def _get_tokens_used_in_season(
    session,
    athlete_id: int,
    season: str,
    exclude_match_id: Optional[int] = None,
) -> int:
    stmt = (
        select(func.coalesce(func.sum(Match.token_cost), 0))
        .join(Event, Match.event_id == Event.id)
        .where(
            Match.is_token_match.is_(True),
            Match.token_spender_id == athlete_id,
            Event.season == season,
        )
    )

    if exclude_match_id is not None:
        stmt = stmt.where(Match.id != exclude_match_id)

    total = session.execute(stmt).scalar_one()
    return int(total or 0)


def _validate_token_usage(
    session,
    athlete_a_id: int,
    athlete_b_id: int,
    season: str,
    is_token_match: bool,
    token_spender_id: Optional[int],
    token_cost: int,
    exclude_match_id: Optional[int] = None,
) -> tuple[bool, Optional[int], int]:
    is_token_match, token_spender_id, token_cost = _normalize_token_fields(
        athlete_a_id=athlete_a_id,
        athlete_b_id=athlete_b_id,
        is_token_match=is_token_match,
        token_spender_id=token_spender_id,
        token_cost=token_cost,
    )

    if not is_token_match:
        return False, None, 0

    token_spender = session.get(Athlete, token_spender_id)
    if token_spender is None:
        raise ValueError("Atleta che spende il token non trovato.")

    used_tokens = _get_tokens_used_in_season(
        session=session,
        athlete_id=token_spender_id,
        season=season,
        exclude_match_id=exclude_match_id,
    )

    remaining_tokens = int(token_spender.token_budget) - used_tokens
    if remaining_tokens < token_cost:
        raise ValueError(
            f"{token_spender.first_name} non ha abbastanza token disponibili per la stagione {season}."
        )

    return True, token_spender_id, token_cost


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
    winner_id: int,
    win_type: str,
    points_a: float,
    points_b: float,
    is_token_match: bool,
    token_spender_id: Optional[int],
    token_cost: int,
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
        points_a=points_a,
        points_b=points_b,
        is_token_match=is_token_match,
        token_spender_id=token_spender_id,
        token_cost=token_cost,
        notes=(notes or "").strip() or None,
    )


def _calculate_score_data(
    athlete_a_id: int,
    athlete_b_id: int,
    winner_id: int,
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
) -> dict:
    _validate_match_inputs(
        athlete_a_id=athlete_a_id,
        athlete_b_id=athlete_b_id,
        raw_score_a=raw_score_a,
        raw_score_b=raw_score_b,
        winner_id=winner_id,
        win_type=win_type,
    )

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
    winner_id: int,
    win_type: str,
    is_token_match: bool = False,
    token_spender_id: Optional[int] = None,
    token_cost: int = TOKEN_SETTINGS["default_token_cost"],
    notes: Optional[str] = None,
) -> Match:
    score_data = _calculate_score_data(
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

        is_token_match, token_spender_id, token_cost = _validate_token_usage(
            session=session,
            athlete_a_id=athlete_a_id,
            athlete_b_id=athlete_b_id,
            season=event.season,
            is_token_match=is_token_match,
            token_spender_id=token_spender_id,
            token_cost=token_cost,
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
            points_a=score_data["total_points_a"],
            points_b=score_data["total_points_b"],
            is_token_match=is_token_match,
            token_spender_id=token_spender_id,
            token_cost=token_cost,
            notes=notes,
        )
        session.add(match)
        session.commit()
        session.refresh(match)
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
    winner_id: int,
    win_type: str,
    is_token_match: bool = False,
    token_spender_id: Optional[int] = None,
    token_cost: int = TOKEN_SETTINGS["default_token_cost"],
    notes: Optional[str] = None,
) -> Match:
    score_data = _calculate_score_data(
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

            is_token_match, token_spender_id, token_cost = _validate_token_usage(
                session=session,
                athlete_a_id=athlete_a_id,
                athlete_b_id=athlete_b_id,
                season=event.season,
                is_token_match=is_token_match,
                token_spender_id=token_spender_id,
                token_cost=token_cost,
                exclude_match_id=match_id,
            )

            session.delete(existing_match)
            session.flush()

            new_match = _build_match(
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
                points_a=score_data["total_points_a"],
                points_b=score_data["total_points_b"],
                is_token_match=is_token_match,
                token_spender_id=token_spender_id,
                token_cost=token_cost,
                notes=notes,
            )
            session.add(new_match)
            session.flush()
            session.refresh(new_match)

        return new_match
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
    finally:
        session.close()


def list_matches() -> list[Match]:
    session = get_session()
    try:
        stmt = select(Match).order_by(Match.id.desc())
        return list(session.scalars(stmt).all())
    finally:
        session.close()