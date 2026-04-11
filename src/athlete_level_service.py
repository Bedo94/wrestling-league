from __future__ import annotations

from collections.abc import Mapping
from typing import TypedDict

from src.models import Athlete, Match
from src.ratings import get_default_start_rating
from src.settings import RATINGS_SETTINGS


class AthleteLevelProfile(TypedDict):
    assigned_level: int
    suggested_level: int
    valid_match_count: int
    rating: float | None


def is_valid_competitive_match(match: Match) -> bool:
    return match.winner_id is not None and str(match.win_type or "").strip() != "Forfait"


def build_valid_match_count_map(matches: list[Match]) -> dict[int, int]:
    counts: dict[int, int] = {}

    for match in matches:
        if not is_valid_competitive_match(match):
            continue

        counts[match.athlete_a_id] = counts.get(match.athlete_a_id, 0) + 1
        counts[match.athlete_b_id] = counts.get(match.athlete_b_id, 0) + 1

    return counts


def get_raw_suggested_level_from_rating(rating: float | None) -> int:
    effective_rating = float(get_default_start_rating() if rating is None else rating)

    start_ratings = {
        int(level): float(value)
        for level, value in RATINGS_SETTINGS["level_start_ratings"].items()
    }

    suggested_level = min(start_ratings) if start_ratings else 1
    for level, start_rating in sorted(start_ratings.items()):
        if effective_rating >= start_rating:
            suggested_level = int(level)

    return suggested_level


def build_athlete_level_profile_map(
    *,
    athletes: list[Athlete],
    matches: list[Match],
    rating_by_athlete_id: Mapping[int, float] | None = None,
) -> dict[int, AthleteLevelProfile]:
    valid_match_count_by_id = build_valid_match_count_map(matches)
    profiles: dict[int, AthleteLevelProfile] = {}

    for athlete in athletes:
        assigned_level = int(athlete.level)
        rating = (
            float(rating_by_athlete_id[athlete.id])
            if rating_by_athlete_id is not None and athlete.id in rating_by_athlete_id
            else None
        )
        valid_match_count = int(valid_match_count_by_id.get(athlete.id, 0))
        suggested_level = get_raw_suggested_level_from_rating(rating)

        profiles[athlete.id] = {
            "assigned_level": assigned_level,
            "suggested_level": suggested_level,
            "valid_match_count": valid_match_count,
            "rating": rating,
        }

    return profiles
