from collections.abc import Mapping
from datetime import date
from typing import Literal, TypedDict

from sqlalchemy import select

from src.database import get_session
from src.matches import build_match_points_map
from src.models import Athlete, Event, Match
from src.settings import RATINGS_SETTINGS


class RatingPreviewResult(TypedDict):
    rating_a: float
    rating_b: float
    expected_a: float
    expected_b: float
    actual_a: float
    actual_b: float
    points_a: float
    points_b: float
    winner_side: str | None
    win_type: str | None
    impact: float
    k_factor: float
    effective_k: float
    logistic_divisor: float
    delta_a: float
    delta_b: float
    new_rating_a: float
    new_rating_b: float


def get_default_start_rating() -> float:
    return float(RATINGS_SETTINGS["default_start_rating"])

def get_k_factor() -> float:
    return float(RATINGS_SETTINGS["k_factor"])


def get_logistic_divisor() -> float:
    return float(RATINGS_SETTINGS.get("logistic_divisor", 400.0))


def expected_score(
    rating_a: float,
    rating_b: float,
    logistic_divisor: float | None = None,
) -> float:
    divisor = get_logistic_divisor() if logistic_divisor is None else float(logistic_divisor)
    return 1 / (1 + 10 ** ((rating_b - rating_a) / divisor))


def get_actual_scores_from_values(
    *,
    points_a: float | None,
    points_b: float | None,
    winner_side: str | None = None,
) -> tuple[float, float]:
    normalized_points_a = float(points_a or 0.0)
    normalized_points_b = float(points_b or 0.0)
    total = normalized_points_a + normalized_points_b

    normalized_winner_side = winner_side if winner_side in {"A", "B"} else None

    if total > 0:
        return normalized_points_a / total, normalized_points_b / total

    if normalized_winner_side == "A":
        return 1.0, 0.0
    if normalized_winner_side == "B":
        return 0.0, 1.0
    return 0.5, 0.5


def _get_winner_side_from_match(match: Match) -> str | None:
    if match.winner_id == match.athlete_a_id:
        return "A"
    if match.winner_id == match.athlete_b_id:
        return "B"
    return None


def get_actual_scores(match: Match) -> tuple[float, float]:
    return get_actual_scores_from_values(
        points_a=0.0,
        points_b=0.0,
        winner_side=_get_winner_side_from_match(match),
    )


def get_match_impact(
    win_type: str | None,
    *,
    normal_match_impact: float | None = None,
    retirement_match_impact: float | None = None,
    forfeit_match_impact: float | None = None,
) -> float:
    resolved_normal_impact = (
        float(RATINGS_SETTINGS["normal_match_impact"])
        if normal_match_impact is None
        else float(normal_match_impact)
    )
    resolved_retirement_impact = (
        float(RATINGS_SETTINGS["retirement_match_impact"])
        if retirement_match_impact is None
        else float(retirement_match_impact)
    )
    resolved_forfeit_impact = (
        float(RATINGS_SETTINGS["forfeit_match_impact"])
        if forfeit_match_impact is None
        else float(forfeit_match_impact)
    )

    if win_type == "Ritiro":
        return resolved_retirement_impact
    if win_type == "Forfait":
        return resolved_forfeit_impact
    return resolved_normal_impact


def preview_rating_update(
    *,
    rating_a: float,
    rating_b: float,
    points_a: float | None = None,
    points_b: float | None = None,
    winner_side: str | None = None,
    win_type: str | None = None,
    k_factor: float | None = None,
    logistic_divisor: float | None = None,
    normal_match_impact: float | None = None,
    retirement_match_impact: float | None = None,
    forfeit_match_impact: float | None = None,
) -> RatingPreviewResult:
    """
    Simula l'aggiornamento rating tra due atleti senza leggere/scrivere il DB.

    Regole:
    - se points_a + points_b > 0, il punteggio effettivo S deriva dalla quota punti
    - altrimenti si usa il winner_side come fallback (1/0 oppure 0.5/0.5 se assente)
    - l'impact dipende dal win_type
    """
    effective_k_factor = get_k_factor() if k_factor is None else float(k_factor)
    effective_logistic_divisor = (
        get_logistic_divisor() if logistic_divisor is None else float(logistic_divisor)
    )

    expected_a = expected_score(
        float(rating_a),
        float(rating_b),
        logistic_divisor=effective_logistic_divisor,
    )
    expected_b = 1.0 - expected_a

    actual_a, actual_b = get_actual_scores_from_values(
        points_a=points_a,
        points_b=points_b,
        winner_side=winner_side,
    )

    impact = get_match_impact(
        win_type,
        normal_match_impact=normal_match_impact,
        retirement_match_impact=retirement_match_impact,
        forfeit_match_impact=forfeit_match_impact,
    )
    effective_k = effective_k_factor * impact

    delta_a = effective_k * (actual_a - expected_a)
    delta_b = effective_k * (actual_b - expected_b)

    new_rating_a = float(rating_a) + delta_a
    new_rating_b = float(rating_b) + delta_b

    return {
        "rating_a": float(rating_a),
        "rating_b": float(rating_b),
        "expected_a": float(expected_a),
        "expected_b": float(expected_b),
        "actual_a": float(actual_a),
        "actual_b": float(actual_b),
        "points_a": float(points_a or 0.0),
        "points_b": float(points_b or 0.0),
        "winner_side": winner_side,
        "win_type": win_type,
        "impact": float(impact),
        "k_factor": float(effective_k_factor),
        "effective_k": float(effective_k),
        "logistic_divisor": float(effective_logistic_divisor),
        "delta_a": float(delta_a),
        "delta_b": float(delta_b),
        "new_rating_a": float(new_rating_a),
        "new_rating_b": float(new_rating_b),
    }


def _load_rating_replay_rows(session) -> list[tuple[Match, date]]:
    stmt = (
        select(Match, Event.event_date)
        .join(Event, Match.event_id == Event.id)
        .order_by(Event.event_date.asc(), Match.id.asc())
    )
    return list(session.execute(stmt).all())


def _build_rating_map_from_rows(
    athletes: list[Athlete],
    rows: list[tuple[Match, date]],
    match_points_by_id: Mapping[int, dict[str, float]] | None = None,
) -> dict[int, float]:
    default_rating = get_default_start_rating()
    current_ratings: dict[int, float] = {
        athlete.id: default_rating
        for athlete in athletes
    }

    for match, _event_date in rows:
        athlete_a_id = match.athlete_a_id
        athlete_b_id = match.athlete_b_id
        match_points = (
            match_points_by_id.get(match.id)
            if match_points_by_id is not None
            else None
        )

        preview = preview_rating_update(
            rating_a=current_ratings[athlete_a_id],
            rating_b=current_ratings[athlete_b_id],
            points_a=match_points["points_a"] if match_points is not None else 0.0,
            points_b=match_points["points_b"] if match_points is not None else 0.0,
            winner_side=_get_winner_side_from_match(match),
            win_type=match.win_type,
            k_factor=get_k_factor(),
            logistic_divisor=get_logistic_divisor(),
        )

        current_ratings[athlete_a_id] = preview["new_rating_a"]
        current_ratings[athlete_b_id] = preview["new_rating_b"]

    return {
        athlete_id: round(float(rating_value), 2)
        for athlete_id, rating_value in current_ratings.items()
    }


def build_current_rating_map_from_loaded(
    *,
    athletes: list[Athlete],
    matches: list[Match],
    events_by_id: Mapping[int, Event],
    match_points_by_id: Mapping[int, dict[str, float]],
) -> dict[int, float]:
    rows = sorted(
        [
        (match, event.event_date)
        for match in matches
        if (event := events_by_id.get(match.event_id)) is not None
        ],
        key=lambda row: (row[1], row[0].id),
    )
    return _build_rating_map_from_rows(
        athletes,
        rows,
        match_points_by_id=match_points_by_id,
    )


def build_current_rating_map() -> dict[int, float]:
    """
    Calcola i rating correnti a partire dai match registrati senza scrivere nel DB.
    """
    session = get_session()
    try:
        athletes = list(session.scalars(select(Athlete).order_by(Athlete.id)).all())
        rows = _load_rating_replay_rows(session)
        match_points_by_id = build_match_points_map()
        return _build_rating_map_from_rows(
            athletes,
            rows,
            match_points_by_id=match_points_by_id,
        )
    finally:
        session.close()


def recompute_ratings() -> Mapping[int, float]:
    return build_current_rating_map()


def recompute_ratings_from_date(start_date: date) -> Mapping[int, float]:
    """
    Recompute athlete ratings for matches occurring on or after the given date.
    """
    session = get_session()
    try:
        athletes = list(session.scalars(select(Athlete).order_by(Athlete.id)).all())
        default_rating = get_default_start_rating()
        rows = _load_rating_replay_rows(session)
        historical_rows = [
            (match, event_date)
            for match, event_date in rows
            if event_date < start_date
        ]
        match_points_by_id = build_match_points_map()
        current_ratings = _build_rating_map_from_rows(
            athletes,
            historical_rows,
            match_points_by_id=match_points_by_id,
        )

        for match, event_date in rows:
            if event_date < start_date:
                continue

            athlete_a_id = match.athlete_a_id
            athlete_b_id = match.athlete_b_id
            rating_a = current_ratings[athlete_a_id]
            rating_b = current_ratings[athlete_b_id]
            match_points = match_points_by_id.get(
                match.id,
                {"points_a": 0.0, "points_b": 0.0},
            )

            preview = preview_rating_update(
                rating_a=rating_a,
                rating_b=rating_b,
                points_a=match_points["points_a"],
                points_b=match_points["points_b"],
                winner_side=_get_winner_side_from_match(match),
                win_type=match.win_type,
                k_factor=get_k_factor(),
                logistic_divisor=get_logistic_divisor(),
            )

            new_rating_a = preview["new_rating_a"]
            new_rating_b = preview["new_rating_b"]

            current_ratings[athlete_a_id] = new_rating_a
            current_ratings[athlete_b_id] = new_rating_b

        return {
            athlete.id: float(current_ratings.get(athlete.id, default_rating))
            for athlete in athletes
        }
    finally:
        session.close()
