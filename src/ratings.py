from collections.abc import Mapping
from datetime import date

from sqlalchemy import select

from src.database import get_session
from src.models import Athlete, Event, Match
from src.settings import RATINGS_SETTINGS


def get_start_rating(level: int) -> float:
    start_ratings = RATINGS_SETTINGS["level_start_ratings"]
    default_rating = float(RATINGS_SETTINGS["default_start_rating"])
    return float(start_ratings.get(level, default_rating))


def get_logistic_divisor() -> float:
    return float(RATINGS_SETTINGS.get("logistic_divisor", 400.0))


def expected_score(
    rating_a: float,
    rating_b: float,
    logistic_divisor: float | None = None,
) -> float:
    divisor = get_logistic_divisor() if logistic_divisor is None else float(logistic_divisor)
    return 1 / (1 + 10 ** ((rating_b - rating_a) / divisor))


def get_actual_scores(match: Match) -> tuple[float, float]:
    points_a = float(match.points_a or 0.0)
    points_b = float(match.points_b or 0.0)
    total = points_a + points_b

    if total > 0:
        return points_a / total, points_b / total

    if match.winner_id == match.athlete_a_id:
        return 1.0, 0.0
    if match.winner_id == match.athlete_b_id:
        return 0.0, 1.0
    return 0.5, 0.5


def get_match_impact(win_type: str | None) -> float:
    if win_type == "Ritiro":
        return float(RATINGS_SETTINGS["retirement_match_impact"])
    if win_type == "Forfait":
        return float(RATINGS_SETTINGS["forfeit_match_impact"])
    return float(RATINGS_SETTINGS["normal_match_impact"])


def recompute_ratings() -> Mapping[int, float]:
    session = get_session()
    try:
        athletes = list(session.scalars(select(Athlete).order_by(Athlete.id)).all())

        default_rating = float(RATINGS_SETTINGS["default_start_rating"])
        k_factor = float(RATINGS_SETTINGS["k_factor"])

        current_ratings: dict[int, float] = {
            athlete.id: get_start_rating(athlete.level)
            for athlete in athletes
        }

        stmt = (
            select(Match, Event.event_date)
            .join(Event, Match.event_id == Event.id)
            .order_by(Event.event_date.asc(), Match.id.asc())
        )

        rows = session.execute(stmt).all()

        for match, _event_date in rows:
            athlete_a_id = match.athlete_a_id
            athlete_b_id = match.athlete_b_id

            rating_a: float = current_ratings[athlete_a_id]
            rating_b: float = current_ratings[athlete_b_id]

            expected_a = expected_score(rating_a, rating_b)
            expected_b = 1.0 - expected_a

            actual_a, actual_b = get_actual_scores(match)
            impact = get_match_impact(match.win_type)

            k = k_factor * impact

            new_rating_a = rating_a + k * (actual_a - expected_a)
            new_rating_b = rating_b + k * (actual_b - expected_b)

            current_ratings[athlete_a_id] = float(new_rating_a)
            current_ratings[athlete_b_id] = float(new_rating_b)

        for athlete in athletes:
            final_rating: float = current_ratings.get(athlete.id, default_rating)
            athlete.rating = round(final_rating, 2)

        session.commit()

        return {athlete.id: float(athlete.rating or default_rating) for athlete in athletes}
    finally:
        session.close()


def recompute_ratings_from_date(start_date: date) -> Mapping[int, float]:
    """
    Recompute athlete ratings for matches occurring on or after the given date.
    """
    session = get_session()
    try:
        athletes = list(session.scalars(select(Athlete).order_by(Athlete.id)).all())
        current_ratings: dict[int, float] = {
            athlete.id: float(athlete.rating or get_start_rating(athlete.level))
            for athlete in athletes
        }
        default_rating = float(RATINGS_SETTINGS["default_start_rating"])
        k_factor = float(RATINGS_SETTINGS["k_factor"])

        stmt = (
            select(Match, Event.event_date)
            .join(Event, Match.event_id == Event.id)
            .order_by(Event.event_date.asc(), Match.id.asc())
        )
        rows = session.execute(stmt).all()

        for match, event_date in rows:
            athlete_a_id = match.athlete_a_id
            athlete_b_id = match.athlete_b_id
            rating_a: float = current_ratings[athlete_a_id]
            rating_b: float = current_ratings[athlete_b_id]
            expected_a = expected_score(rating_a, rating_b)
            expected_b = 1.0 - expected_a
            actual_a, actual_b = get_actual_scores(match)
            impact = get_match_impact(match.win_type)
            k = k_factor * impact

            new_rating_a = rating_a + k * (actual_a - expected_a)
            new_rating_b = rating_b + k * (actual_b - expected_b)
            current_ratings[athlete_a_id] = float(new_rating_a)
            current_ratings[athlete_b_id] = float(new_rating_b)

            if event_date >= start_date:
                match_rating_a = round(new_rating_a, 2)
                match_rating_b = round(new_rating_b, 2)
                athlete_a = session.get(Athlete, athlete_a_id)
                athlete_b = session.get(Athlete, athlete_b_id)
                if athlete_a:
                    athlete_a.rating = match_rating_a
                if athlete_b:
                    athlete_b.rating = match_rating_b

        session.commit()
        return {athlete.id: float(athlete.rating or default_rating) for athlete in athletes}
    finally:
        session.close()