from datetime import date

MAX_WEIGHT_DIFF_KG = 10.0
WEIGHT_BONUS_PER_KG = 0.05

WINNER_BASE_POINTS = 2.0
LOSER_BASE_POINTS = 1.0

PERFORMANCE_BONUS_MAX = 0.5

MINOR_AGE_THRESHOLD = 18
SPECIAL_BONUS_FACTOR = 1.30


def validate_weight_difference(weight_a: float, weight_b: float) -> None:
    diff = abs(weight_a - weight_b)
    if diff > MAX_WEIGHT_DIFF_KG:
        raise ValueError(
            f"La differenza di peso è {diff:.1f} kg: supera il limite di {MAX_WEIGHT_DIFF_KG:.0f} kg."
        )


def get_weight_factor(own_weight: float, opponent_weight: float) -> float:
    diff = opponent_weight - own_weight
    factor = 1 + (diff * WEIGHT_BONUS_PER_KG)

    if factor < 0.5:
        factor = 0.5
    if factor > 1.5:
        factor = 1.5

    return factor


def get_age_at_event(birth_year: int, event_date: date) -> int:
    return event_date.year - birth_year


def is_minor(birth_year: int, event_date: date) -> bool:
    return get_age_at_event(birth_year, event_date) < MINOR_AGE_THRESHOLD


def is_senior_male(sex: str, birth_year: int, event_date: date) -> bool:
    return sex == "Maschio" and not is_minor(birth_year, event_date)


def gets_special_bonus(
    athlete_sex: str,
    athlete_birth_year: int,
    opponent_sex: str,
    opponent_birth_year: int,
    event_date: date,
) -> bool:
    athlete_is_female = athlete_sex == "Femmina"
    athlete_is_minor = is_minor(athlete_birth_year, event_date)
    opponent_is_senior_male = is_senior_male(opponent_sex, opponent_birth_year, event_date)

    return opponent_is_senior_male and (athlete_is_female or athlete_is_minor)


def get_special_factor(
    athlete_sex: str,
    athlete_birth_year: int,
    opponent_sex: str,
    opponent_birth_year: int,
    event_date: date,
) -> float:
    if gets_special_bonus(
        athlete_sex=athlete_sex,
        athlete_birth_year=athlete_birth_year,
        opponent_sex=opponent_sex,
        opponent_birth_year=opponent_birth_year,
        event_date=event_date,
    ):
        return SPECIAL_BONUS_FACTOR
    return 1.0


def get_performance_bonus(raw_score: float, opponent_raw_score: float) -> float:
    total_raw = raw_score + opponent_raw_score
    if total_raw <= 0:
        return 0.0

    share = raw_score / total_raw
    return share * PERFORMANCE_BONUS_MAX


def calculate_match_points(
    athlete_a_id: int,
    athlete_b_id: int,
    winner_id: int,
    weight_a: float,
    weight_b: float,
    raw_score_a: float,
    raw_score_b: float,
    athlete_a_sex: str,
    athlete_b_sex: str,
    athlete_a_birth_year: int,
    athlete_b_birth_year: int,
    event_date: date,
) -> dict:
    validate_weight_difference(weight_a, weight_b)

    if winner_id not in {athlete_a_id, athlete_b_id}:
        raise ValueError("Il vincitore deve essere uno dei due atleti del match.")

    weight_factor_a = get_weight_factor(weight_a, weight_b)
    weight_factor_b = get_weight_factor(weight_b, weight_a)

    special_factor_a = get_special_factor(
        athlete_sex=athlete_a_sex,
        athlete_birth_year=athlete_a_birth_year,
        opponent_sex=athlete_b_sex,
        opponent_birth_year=athlete_b_birth_year,
        event_date=event_date,
    )
    special_factor_b = get_special_factor(
        athlete_sex=athlete_b_sex,
        athlete_birth_year=athlete_b_birth_year,
        opponent_sex=athlete_a_sex,
        opponent_birth_year=athlete_a_birth_year,
        event_date=event_date,
    )

    result_base_a = WINNER_BASE_POINTS if winner_id == athlete_a_id else LOSER_BASE_POINTS
    result_base_b = WINNER_BASE_POINTS if winner_id == athlete_b_id else LOSER_BASE_POINTS

    performance_bonus_a = get_performance_bonus(raw_score_a, raw_score_b)
    performance_bonus_b = get_performance_bonus(raw_score_b, raw_score_a)

    pre_multiplier_a = result_base_a + performance_bonus_a
    pre_multiplier_b = result_base_b + performance_bonus_b

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
        "pre_multiplier_a": round(pre_multiplier_a, 2),
        "pre_multiplier_b": round(pre_multiplier_b, 2),
        "total_points_a": round(total_points_a, 2),
        "total_points_b": round(total_points_b, 2),
    }