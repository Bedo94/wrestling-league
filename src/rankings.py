from datetime import date
from typing import Any

from src.athletes import list_athletes
from src.events import list_events
from src.levels import get_level_label
from src.matches import build_match_points_map_from_loaded, list_matches
from src.ratings import build_current_rating_map_from_loaded
from src.settings import ATHLETE_RANKING_SETTINGS, TEAM_RANKING_SETTINGS


def calculate_age(birth_date: date, reference_date: date) -> int:
    age = reference_date.year - birth_date.year
    if (reference_date.month, reference_date.day) < (birth_date.month, birth_date.day):
        age -= 1
    return age


def sort_ranking_rows(
    ranking_rows: list[dict[str, Any]],
    ranking_method: str = "cumulative",
    min_matches_for_average: int = 2,
) -> list[dict[str, Any]]:
    rows = [{**row} for row in ranking_rows]

    if ranking_method == "average_per_match":
        rows.sort(
            key=lambda x: (
                x["matches"] < min_matches_for_average,
                -float(x.get("avg_class_points", 0.0)),
                -int(x.get("wins", 0)),
                -float(x.get("technical_diff", 0.0)),
                -float(x.get("technical_points_for", 0.0)),
                -float(x.get("class_points_total", 0.0)),
                x.get("name", "").lower(),
            )
        )
    else:
        rows.sort(
            key=lambda x: (
                -float(x.get("class_points_total", 0.0)),
                -int(x.get("wins", 0)),
                -float(x.get("technical_diff", 0.0)),
                -float(x.get("technical_points_for", 0.0)),
                x.get("name", "").lower(),
            )
        )

    for index, row in enumerate(rows, start=1):
        row["rank"] = index

    return rows


def build_rankings(
    reference_date: date | None = None,
    years: list[int] | None = None,
    event_ids: list[int] | None = None,
    ranking_method: str | None = None,
    min_matches_for_average: int | None = None,
) -> list[dict[str, Any]]:
    if reference_date is None:
        reference_date = date.today()

    if ranking_method is None:
        ranking_method = str(
            ATHLETE_RANKING_SETTINGS.get("ranking_method", "cumulative")
        )

    if min_matches_for_average is None:
        min_matches_for_average = int(
            ATHLETE_RANKING_SETTINGS.get("min_matches_for_average", 2)
        )

    athletes = list_athletes(include_inactive=True)
    matches = list_matches()
    events = list_events()
    events_map = {event.id: event for event in events}
    athletes_map = {athlete.id: athlete for athlete in athletes}
    match_points_by_id = build_match_points_map_from_loaded(
        matches=matches,
        events_by_id=events_map,
        athletes_by_id=athletes_map,
    )
    rating_by_athlete_id = build_current_rating_map_from_loaded(
        athletes=athletes,
        matches=matches,
        events_by_id=events_map,
        match_points_by_id=match_points_by_id,
    )

    selected_years = set(years) if years else None
    selected_event_ids = set(event_ids) if event_ids else None

    if selected_years or selected_event_ids:
        filtered_matches = []

        for match in matches:
            event = events_map.get(match.event_id)
            if event is None:
                continue

            if selected_years and event.event_date.year not in selected_years:
                continue

            if selected_event_ids and match.event_id not in selected_event_ids:
                continue

            filtered_matches.append(match)

        matches = filtered_matches

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
            "rating": rating_by_athlete_id.get(athlete.id),
            "active": athlete.active,
            "matches": 0,
            "wins": 0,
            "losses": 0,
            "class_points_total": 0.0,
            "technical_points_for": 0.0,
            "technical_points_against": 0.0,
            "technical_diff": 0.0,
            "avg_class_points": 0.0,
            "ranking_method": ranking_method,
            "ranking_score": 0.0,
            "is_provisional": False,
        }

    for match in matches:
        athlete_a = rankings.get(match.athlete_a_id)
        athlete_b = rankings.get(match.athlete_b_id)
        match_points = match_points_by_id.get(
            match.id,
            {"points_a": 0.0, "points_b": 0.0},
        )

        if athlete_a is None or athlete_b is None:
            continue

        athlete_a["matches"] += 1
        athlete_a["class_points_total"] += float(match_points["points_a"])
        athlete_a["technical_points_for"] += float(match.raw_score_a or 0.0)
        athlete_a["technical_points_against"] += float(match.raw_score_b or 0.0)

        if match.winner_id == match.athlete_a_id:
            athlete_a["wins"] += 1
        elif match.winner_id == match.athlete_b_id:
            athlete_a["losses"] += 1

        athlete_b["matches"] += 1
        athlete_b["class_points_total"] += float(match_points["points_b"])
        athlete_b["technical_points_for"] += float(match.raw_score_b or 0.0)
        athlete_b["technical_points_against"] += float(match.raw_score_a or 0.0)

        if match.winner_id == match.athlete_b_id:
            athlete_b["wins"] += 1
        elif match.winner_id == match.athlete_a_id:
            athlete_b["losses"] += 1

    results = []
    for _, row in rankings.items():
        row["technical_diff"] = row["technical_points_for"] - row["technical_points_against"]
        row["class_points_total"] = round(row["class_points_total"], 2)

        if row["matches"] > 0:
            row["avg_class_points"] = round(row["class_points_total"] / row["matches"], 2)
        else:
            row["avg_class_points"] = 0.0

        if ranking_method == "average_per_match":
            row["ranking_score"] = float(row["avg_class_points"])
            row["is_provisional"] = row["matches"] < min_matches_for_average
        else:
            row["ranking_score"] = float(row["class_points_total"])
            row["is_provisional"] = False

        row["technical_points_for"] = round(row["technical_points_for"], 2)
        row["technical_points_against"] = round(row["technical_points_against"], 2)
        row["technical_diff"] = round(row["technical_diff"], 2)
        row["ranking_score"] = round(row["ranking_score"], 2)

        results.append(row)

    return sort_ranking_rows(
        results,
        ranking_method=ranking_method,
        min_matches_for_average=min_matches_for_average,
    )


def build_team_rankings(
    ranking_rows: list[dict[str, Any]],
    participation_bonus_per_athlete: float | None = None,
    ranking_method: str | None = None,
) -> list[dict[str, Any]]:
    if participation_bonus_per_athlete is None:
        participation_bonus_per_athlete = float(
            TEAM_RANKING_SETTINGS["participation_bonus_per_athlete"]
        )

    if ranking_method is None:
        ranking_method = str(
            TEAM_RANKING_SETTINGS.get("ranking_method", "sum_with_bonus")
        )

    teams: dict[str, dict[str, Any]] = {}

    for row in ranking_rows:
        team_name = (row.get("team") or "").strip() or "Senza team"

        if team_name not in teams:
            teams[team_name] = {
                "team": team_name,
                "athletes_count": 0,
                "participating_athletes": 0,
                "matches": 0,
                "wins": 0,
                "losses": 0,
                "class_points_total": 0.0,
                "technical_points_for": 0.0,
                "technical_points_against": 0.0,
                "technical_diff": 0.0,
                "participation_bonus": 0.0,
                "team_score": 0.0,
                "avg_points_per_participating_athlete": 0.0,
                "ranking_method": ranking_method,
            }

        team_row = teams[team_name]
        matches = int(row.get("matches", 0))
        class_points_total = float(row.get("class_points_total", 0.0))
        technical_points_for = float(row.get("technical_points_for", 0.0))
        technical_points_against = float(row.get("technical_points_against", 0.0))

        team_row["athletes_count"] += 1
        if matches > 0:
            team_row["participating_athletes"] += 1

        team_row["matches"] += matches
        team_row["wins"] += int(row.get("wins", 0))
        team_row["losses"] += int(row.get("losses", 0))
        team_row["class_points_total"] += class_points_total
        team_row["technical_points_for"] += technical_points_for
        team_row["technical_points_against"] += technical_points_against

    results = []
    for team_row in teams.values():
        team_row["technical_diff"] = (
            team_row["technical_points_for"] - team_row["technical_points_against"]
        )

        if team_row["participating_athletes"] > 0:
            team_row["avg_points_per_participating_athlete"] = (
                team_row["class_points_total"] / team_row["participating_athletes"]
            )
        else:
            team_row["avg_points_per_participating_athlete"] = 0.0

        if ranking_method == "average_per_participating_athlete":
            team_row["participation_bonus"] = 0.0
            team_row["team_score"] = team_row["avg_points_per_participating_athlete"]
        else:
            team_row["participation_bonus"] = (
                team_row["participating_athletes"] * participation_bonus_per_athlete
            )
            team_row["team_score"] = (
                team_row["class_points_total"] + team_row["participation_bonus"]
            )

        team_row["class_points_total"] = round(team_row["class_points_total"], 2)
        team_row["technical_points_for"] = round(team_row["technical_points_for"], 2)
        team_row["technical_points_against"] = round(team_row["technical_points_against"], 2)
        team_row["technical_diff"] = round(team_row["technical_diff"], 2)
        team_row["participation_bonus"] = round(team_row["participation_bonus"], 2)
        team_row["team_score"] = round(team_row["team_score"], 2)
        team_row["avg_points_per_participating_athlete"] = round(
            team_row["avg_points_per_participating_athlete"],
            2,
        )

        results.append(team_row)

    results.sort(
        key=lambda x: (
            -x["team_score"],
            -x["class_points_total"],
            -x["wins"],
            -x["technical_diff"],
            x["team"].lower(),
        )
    )

    for index, row in enumerate(results, start=1):
        row["rank"] = index

    return results
