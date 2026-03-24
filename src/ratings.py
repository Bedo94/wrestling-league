from collections.abc import Mapping

from sqlalchemy import select

from src.database import get_session
from src.models import Athlete, Event, Match

LEVEL_START_RATINGS = {
    1: 900.0,
    2: 1000.0,
    3: 1100.0,
    4: 1200.0,
}

DEFAULT_START_RATING = 1000.0
K_FACTOR = 24.0


def get_start_rating(level: int) -> float:
    return LEVEL_START_RATINGS.get(level, DEFAULT_START_RATING)


def expected_score(rating_a: float, rating_b: float) -> float:
    return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))


def get_actual_scores(match: Match) -> tuple[float, float]:
    points_a = float(match.points_a or 0.0)
    points_b = float(match.points_b or 0.0)
    total = points_a + points_b

    if total > 0:
        actual_a = points_a / total
        actual_b = points_b / total
        return actual_a, actual_b

    # fallback di sicurezza
    if match.winner_id == match.athlete_a_id:
        return 1.0, 0.0
    if match.winner_id == match.athlete_b_id:
        return 0.0, 1.0
    return 0.5, 0.5


def recompute_ratings() -> Mapping[int, float]:
    session = get_session()
    try:
        athletes = list(session.scalars(select(Athlete).order_by(Athlete.id)).all())

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

            rating_a = current_ratings.get(athlete_a_id, DEFAULT_START_RATING)
            rating_b = current_ratings.get(athlete_b_id, DEFAULT_START_RATING)

            expected_a = expected_score(rating_a, rating_b)
            expected_b = 1.0 - expected_a

            actual_a, actual_b = get_actual_scores(match)

            new_rating_a = rating_a + K_FACTOR * (actual_a - expected_a)
            new_rating_b = rating_b + K_FACTOR * (actual_b - expected_b)

            current_ratings[athlete_a_id] = new_rating_a
            current_ratings[athlete_b_id] = new_rating_b

        for athlete in athletes:
            athlete.rating = round(current_ratings.get(athlete.id, DEFAULT_START_RATING), 2)

        session.commit()

        return {athlete.id: athlete.rating for athlete in athletes}
    finally:
        session.close()