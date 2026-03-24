from datetime import date
from typing import Any

from src.models import Athlete, Match
from src.ratings import get_start_rating


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


def build_pair_explanation(
    weight_diff: float,
    level_diff: int,
    rating_diff: float,
    age_diff: int,
    previous_matches: int,
) -> str:
    return (
        f"Δpeso={weight_diff:.1f} kg, "
        f"Δlevel={level_diff}, "
        f"Δrating={rating_diff:.1f}, "
        f"Δetà={age_diff}, "
        f"precedenti={previous_matches}"
    )


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

            rematch_penalty = previous_matches * 15 if avoid_rematches else 0
            rating_component = (rating_diff / 20.0) if use_rating else 0.0

            # Score più basso = matchup migliore
            score = (
                weight_diff * 3.0
                + level_diff * 8.0
                + rating_component
                + age_diff * 1.0
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
                    "rating_a": round(rating_a, 2),
                    "rating_b": round(rating_b, 2),
                    "rating_diff": round(rating_diff, 2),
                    "age_a": age_a,
                    "age_b": age_b,
                    "age_diff": age_diff,
                    "previous_matches": previous_matches,
                    "score": round(score, 2),
                    "explanation": build_pair_explanation(
                        weight_diff=weight_diff,
                        level_diff=level_diff,
                        rating_diff=rating_diff,
                        age_diff=age_diff,
                        previous_matches=previous_matches,
                    ),
                }
            )

    candidates.sort(key=lambda x: (x["score"], x["weight_diff"], x["level_diff"], x["rating_diff"]))
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