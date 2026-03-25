from datetime import date
from typing import Any

from src.models import Athlete, Match
from src.ratings import get_start_rating
from src.settings import MATCHMAKING_SETTINGS


def calculate_age(birth_date: date, reference_date: date) -> int:
    age = reference_date.year - birth_date.year
    if (reference_date.month, reference_date.day) < (birth_date.month, birth_date.day):
        age -= 1
    return age


def get_effective_rating(athlete: Athlete) -> float:
    if athlete.rating is not None:
        return float(athlete.rating)
    return float(get_start_rating(athlete.level))


def count_previous_matches(matches: list[Match], athlete_a_id: int, athlete_b_id: int) -> int:
    count = 0
    for match in matches:
        pair = {match.athlete_a_id, match.athlete_b_id}
        if pair == {athlete_a_id, athlete_b_id}:
            count += 1
    return count


def describe_level_gap(level_diff: int) -> str:
    if level_diff == 0:
        return "Stesso livello"
    if level_diff == 1:
        return "1 fascia di differenza"
    return f"{level_diff} fasce di differenza"


def describe_previous_matches(previous_matches: int) -> str:
    if previous_matches == 0:
        return "Mai affrontati"
    if previous_matches == 1:
        return "1 precedente"
    return f"{previous_matches} precedenti"


def generate_candidate_pairs(
    athletes: list[Athlete],
    matches: list[Match],
    reference_date: date,
    max_weight_diff: float = 10.0,
    max_level_diff: int = 2,
    max_age_diff: int | None = None,
    use_rating: bool = True,
    avoid_rematches: bool = True,
    same_sex_only: bool = False,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []

    for i in range(len(athletes)):
        athlete_a = athletes[i]

        for j in range(i + 1, len(athletes)):
            athlete_b = athletes[j]

            if athlete_a.id == athlete_b.id:
                continue

            if athlete_a.style != athlete_b.style:
                continue

            if same_sex_only and athlete_a.sex != athlete_b.sex:
                continue

            weight_diff = abs(float(athlete_a.default_weight) - float(athlete_b.default_weight))
            if weight_diff > max_weight_diff:
                continue

            level_diff = abs(int(athlete_a.level) - int(athlete_b.level))
            if level_diff > max_level_diff:
                continue

            age_a = calculate_age(athlete_a.birth_date, reference_date)
            age_b = calculate_age(athlete_b.birth_date, reference_date)
            age_diff = abs(age_a - age_b)

            if max_age_diff is not None and age_diff > max_age_diff:
                continue

            rating_a = get_effective_rating(athlete_a)
            rating_b = get_effective_rating(athlete_b)
            rating_diff = abs(rating_a - rating_b)

            previous_matches = count_previous_matches(matches, athlete_a.id, athlete_b.id)

            rematch_penalty = (
                previous_matches * MATCHMAKING_SETTINGS["rematch_penalty"]
                if avoid_rematches
                else 0
            )
            rating_component = (
                rating_diff / MATCHMAKING_SETTINGS["rating_divisor"]
                if use_rating
                else 0.0
            )
            weight_component = weight_diff * MATCHMAKING_SETTINGS["weight_factor"]
            level_component = level_diff * MATCHMAKING_SETTINGS["level_factor"]
            age_component = age_diff * MATCHMAKING_SETTINGS["age_factor"]

            mismatch_index = (
                weight_component
                + level_component
                + rating_component
                + age_component
                + rematch_penalty
            )

            candidates.append(
                {
                    "athlete_a_id": athlete_a.id,
                    "athlete_b_id": athlete_b.id,
                    "athlete_a": athlete_a,
                    "athlete_b": athlete_b,
                    "style": athlete_a.style,
                    "weight_diff": round(weight_diff, 2),
                    "level_diff": level_diff,
                    "level_gap_label": describe_level_gap(level_diff),
                    "rating_a": round(rating_a, 2),
                    "rating_b": round(rating_b, 2),
                    "rating_diff": round(rating_diff, 2),
                    "age_a": age_a,
                    "age_b": age_b,
                    "age_diff": age_diff,
                    "previous_matches": previous_matches,
                    "previous_matches_label": describe_previous_matches(previous_matches),
                    "weight_component": round(weight_component, 2),
                    "level_component": round(level_component, 2),
                    "rating_component": round(rating_component, 2),
                    "age_component": round(age_component, 2),
                    "rematch_penalty": round(rematch_penalty, 2),
                    "mismatch_index": round(mismatch_index, 2),
                }
            )

    candidates.sort(
        key=lambda x: (
            x["mismatch_index"],
            x["weight_diff"],
            x["level_diff"],
            x["rating_diff"],
        )
    )
    return candidates


def select_greedy_pairings(
    candidates: list[dict[str, Any]],
    athletes: list[Athlete],
) -> tuple[list[dict[str, Any]], list[Athlete]]:
    used_ids: set[int] = set()
    selected_pairs: list[dict[str, Any]] = []

    for candidate in candidates:
        athlete_a_id = candidate["athlete_a_id"]
        athlete_b_id = candidate["athlete_b_id"]

        if athlete_a_id in used_ids or athlete_b_id in used_ids:
            continue

        selected_pairs.append(candidate)
        used_ids.add(athlete_a_id)
        used_ids.add(athlete_b_id)

    leftovers = [athlete for athlete in athletes if athlete.id not in used_ids]
    return selected_pairs, leftovers