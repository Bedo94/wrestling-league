from datetime import date
from typing import Any

from src.athletes import list_athletes
from src.matches import list_matches
from src.levels import get_level_label


def calculate_age(birth_date: date, reference_date: date) -> int:
    age = reference_date.year - birth_date.year
    if (reference_date.month, reference_date.day) < (birth_date.month, birth_date.day):
        age -= 1
    return age


def build_rankings(reference_date: date | None = None) -> list[dict[str, Any]]:
    if reference_date is None:
        reference_date = date.today()

    athletes = list_athletes(include_inactive=True)
    matches = list_matches()

    rankings: dict[int, dict[str, Any]] = {}

    for athlete in athletes:
        full_name = f"{athlete.first_name} {athlete.last_name or ''}".strip()

        rankings[athlete.id] = {
            "athlete_id": athlete.id,
            "name": full_name,
            "nickname": athlete.nickname or "",
            "team": athlete.team or "",
            "birth_date": athlete.birth_date,
            "age": calculate_age(athlete.birth_date, reference_date),
            "sex": athlete.sex,
            "style": athlete.style,
            "level": athlete.level,
            "level_label": get_level_label(athlete.level),
            "default_weight": float(athlete.default_weight),
            "rating": athlete.rating,
            "active": athlete.active,
            "matches": 0,
            "wins": 0,
            "losses": 0,
            "class_points_total": 0.0,
            "technical_points_for": 0.0,
            "technical_points_against": 0.0,
            "technical_diff": 0.0,
            "avg_class_points": 0.0,
        }

    for match in matches:
        athlete_a = rankings.get(match.athlete_a_id)
        athlete_b = rankings.get(match.athlete_b_id)

        if athlete_a is None or athlete_b is None:
            continue

        # atleta A
        athlete_a["matches"] += 1
        athlete_a["class_points_total"] += float(match.points_a or 0.0)
        athlete_a["technical_points_for"] += float(match.raw_score_a or 0.0)
        athlete_a["technical_points_against"] += float(match.raw_score_b or 0.0)

        if match.winner_id == match.athlete_a_id:
            athlete_a["wins"] += 1
        elif match.winner_id == match.athlete_b_id:
            athlete_a["losses"] += 1

        # atleta B
        athlete_b["matches"] += 1
        athlete_b["class_points_total"] += float(match.points_b or 0.0)
        athlete_b["technical_points_for"] += float(match.raw_score_b or 0.0)
        athlete_b["technical_points_against"] += float(match.raw_score_a or 0.0)

        if match.winner_id == match.athlete_b_id:
            athlete_b["wins"] += 1
        elif match.winner_id == match.athlete_a_id:
            athlete_b["losses"] += 1

    results = []
    for athlete_id, row in rankings.items():
        row["technical_diff"] = row["technical_points_for"] - row["technical_points_against"]
        row["class_points_total"] = round(row["class_points_total"], 2)

        if row["matches"] > 0:
            row["avg_class_points"] = round(row["class_points_total"] / row["matches"], 2)
        else:
            row["avg_class_points"] = 0.0

        row["technical_points_for"] = round(row["technical_points_for"], 2)
        row["technical_points_against"] = round(row["technical_points_against"], 2)
        row["technical_diff"] = round(row["technical_diff"], 2)

        results.append(row)

    results.sort(
        key=lambda x: (
            -x["class_points_total"],
            -x["wins"],
            -x["technical_diff"],
            -x["technical_points_for"],
            x["name"].lower(),
        )
    )

    for index, row in enumerate(results, start=1):
        row["rank"] = index

    return results