from datetime import date
from typing import TypedDict

from src.settings import SCORING_SETTINGS


class MatchPointsPreview(TypedDict):
    weight_factor_a: float
    weight_factor_b: float
    special_factor_a: float
    special_factor_b: float
    result_base_a: float
    result_base_b: float
    performance_bonus_a: float
    performance_bonus_b: float
    finish_bonus_a: float
    finish_bonus_b: float
    pre_multiplier_a: float
    pre_multiplier_b: float
    total_points_a: float
    total_points_b: float


def validate_weight_difference(weight_a: float, weight_b: float) -> None:
    diff = abs(weight_a - weight_b)
    if diff > SCORING_SETTINGS["max_weight_diff_kg"]:
        raise ValueError(
            f"La differenza di peso è {diff:.1f} kg: supera il limite di "
            f"{SCORING_SETTINGS['max_weight_diff_kg']:.0f} kg."
        )


def get_weight_factor(own_weight: float, opponent_weight: float) -> float:
    diff = opponent_weight - own_weight
    factor = 1 + (diff * SCORING_SETTINGS["weight_bonus_per_kg"])

    if factor < 0.5:
        factor = 0.5
    if factor > 1.5:
        factor = 1.5

    return factor


def get_age_at_event(birth_date: date, event_date: date) -> int:
    age = event_date.year - birth_date.year
    if (event_date.month, event_date.day) < (birth_date.month, birth_date.day):
        age -= 1
    return age


def is_minor(birth_date: date, event_date: date) -> bool:
    return get_age_at_event(birth_date, event_date) < SCORING_SETTINGS["minor_age_threshold"]


def is_senior_male(sex: str, birth_date: date, event_date: date) -> bool:
    return sex == "Maschio" and not is_minor(birth_date, event_date)


def gets_special_bonus(
    athlete_sex: str,
    athlete_birth_date: date,
    opponent_sex: str,
    opponent_birth_date: date,
    event_date: date,
) -> bool:
    athlete_is_female = athlete_sex == "Femmina"
    athlete_is_minor = is_minor(athlete_birth_date, event_date)
    opponent_is_senior_male = is_senior_male(opponent_sex, opponent_birth_date, event_date)

    return opponent_is_senior_male and (athlete_is_female or athlete_is_minor)


def get_special_factor(
    athlete_sex: str,
    athlete_birth_date: date,
    opponent_sex: str,
    opponent_birth_date: date,
    event_date: date,
) -> float:
    if gets_special_bonus(
        athlete_sex=athlete_sex,
        athlete_birth_date=athlete_birth_date,
        opponent_sex=opponent_sex,
        opponent_birth_date=opponent_birth_date,
        event_date=event_date,
    ):
        return SCORING_SETTINGS["special_bonus_factor"]
    return 1.0


def get_performance_bonus(raw_score: float, opponent_raw_score: float) -> float:
    total_raw = raw_score + opponent_raw_score
    if total_raw <= 0:
        return 0.0

    share = raw_score / total_raw
    return share * SCORING_SETTINGS["performance_bonus_max"]


def get_result_base_points(win_type: str, is_winner: bool) -> float:
    if win_type == "Ritiro":
        return (
            SCORING_SETTINGS["retirement_winner_base_points"]
            if is_winner
            else SCORING_SETTINGS["retirement_loser_base_points"]
        )

    if win_type == "Forfait":
        return (
            SCORING_SETTINGS["forfeit_winner_base_points"]
            if is_winner
            else SCORING_SETTINGS["forfeit_loser_base_points"]
        )

    return (
        SCORING_SETTINGS["winner_base_points"]
        if is_winner
        else SCORING_SETTINGS["loser_base_points"]
    )


def calculate_match_points(
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
) -> MatchPointsPreview:
    validate_weight_difference(weight_a, weight_b)

    if winner_id not in {athlete_a_id, athlete_b_id}:
        raise ValueError("Il vincitore deve essere uno dei due atleti del match.")

    weight_factor_a = get_weight_factor(weight_a, weight_b)
    weight_factor_b = get_weight_factor(weight_b, weight_a)

    special_factor_a = get_special_factor(
        athlete_sex=athlete_a_sex,
        athlete_birth_date=athlete_a_birth_date,
        opponent_sex=athlete_b_sex,
        opponent_birth_date=athlete_b_birth_date,
        event_date=event_date,
    )
    special_factor_b = get_special_factor(
        athlete_sex=athlete_b_sex,
        athlete_birth_date=athlete_b_birth_date,
        opponent_sex=athlete_a_sex,
        opponent_birth_date=athlete_a_birth_date,
        event_date=event_date,
    )

    is_winner_a = winner_id == athlete_a_id
    is_winner_b = winner_id == athlete_b_id

    result_base_a = get_result_base_points(win_type, is_winner_a)
    result_base_b = get_result_base_points(win_type, is_winner_b)

    if win_type == "Forfait":
        performance_bonus_a = 0.0
        performance_bonus_b = 0.0
    else:
        performance_bonus_a = get_performance_bonus(raw_score_a, raw_score_b)
        performance_bonus_b = get_performance_bonus(raw_score_b, raw_score_a)

    finish_bonus_a = get_finish_bonus(win_type, is_winner_a)
    finish_bonus_b = get_finish_bonus(win_type, is_winner_b)

    pre_multiplier_a = result_base_a + performance_bonus_a + finish_bonus_a
    pre_multiplier_b = result_base_b + performance_bonus_b + finish_bonus_b

    total_points_a = pre_multiplier_a * weight_factor_a * special_factor_a
    total_points_b = pre_multiplier_b * weight_factor_b * special_factor_b

    return {
        "weight_factor_a": round(weight_factor_a, 4),
        "weight_factor_b": round(weight_factor_b, 4),
        "special_factor_a": round(special_factor_a, 4),
        "special_factor_b": round(special_factor_b, 4),
        "result_base_a": round(result_base_a, 2),
        "result_base_b": round(result_base_b, 2),
        "performance_bonus_a": round(performance_bonus_a, 2),
        "performance_bonus_b": round(performance_bonus_b, 2),
        "finish_bonus_a": round(finish_bonus_a, 2),
        "finish_bonus_b": round(finish_bonus_b, 2),
        "pre_multiplier_a": round(pre_multiplier_a, 2),
        "pre_multiplier_b": round(pre_multiplier_b, 2),
        "total_points_a": round(total_points_a, 2),
        "total_points_b": round(total_points_b, 2),
    }

def get_finish_bonus(win_type: str, is_winner: bool) -> float:
    if not is_winner:
        return 0.0

    if win_type == "Schienamento":
        return float(SCORING_SETTINGS["pinfall_finish_bonus"])

    if win_type == "Ritiro":
        return float(SCORING_SETTINGS["retirement_finish_bonus"])

    if win_type == "Forfait":
        return float(SCORING_SETTINGS["forfeit_finish_bonus"])

    return float(SCORING_SETTINGS["points_finish_bonus"])
