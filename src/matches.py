from datetime import date
from typing import Optional

from sqlalchemy import select

from src.database import get_session
from src.models import Match
from src.reference_data import WIN_TYPE_OPTIONS
from src.scoring import calculate_match_points


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