from dataclasses import dataclass

from src.settings import LEVEL_EVALUATION_SETTINGS


@dataclass
class LevelEvaluationInput:
    years_practice: int
    matches_count: int

    regional_gold: int = 0
    regional_silver: int = 0
    regional_bronze: int = 0

    interregional_gold: int = 0
    interregional_silver: int = 0
    interregional_bronze: int = 0

    national_open_gold: int = 0
    national_open_silver: int = 0
    national_open_bronze: int = 0

    coppa_italia_gold: int = 0
    coppa_italia_silver: int = 0
    coppa_italia_bronze: int = 0

    campionato_italiano_gold: int = 0
    campionato_italiano_silver: int = 0
    campionato_italiano_bronze: int = 0

    international_gold: int = 0
    international_silver: int = 0
    international_bronze: int = 0


def _nn(value: int) -> int:
    return max(0, int(value))


def calculate_level_evaluation(data: LevelEvaluationInput) -> dict:
    s = LEVEL_EVALUATION_SETTINGS

    years_component = (
        min(_nn(data.years_practice), int(s["years_cap"])) / float(s["years_cap"])
    ) * float(s["years_weight"])

    matches_component = (
        min(_nn(data.matches_count), int(s["matches_cap"])) / float(s["matches_cap"])
    ) * float(s["matches_weight"])

    gold_weight = float(s["gold_weight"])
    silver_weight = float(s["silver_weight"])
    bronze_weight = float(s["bronze_weight"])

    def medals_block(prefix_weight: str, gold: int, silver: int, bronze: int) -> float:
        competition_weight = float(s[prefix_weight])
        return competition_weight * (
            _nn(gold) * gold_weight
            + _nn(silver) * silver_weight
            + _nn(bronze) * bronze_weight
        )

    medals_points = (
        medals_block("regional_weight", data.regional_gold, data.regional_silver, data.regional_bronze)
        + medals_block("interregional_weight", data.interregional_gold, data.interregional_silver, data.interregional_bronze)
        + medals_block("national_open_weight", data.national_open_gold, data.national_open_silver, data.national_open_bronze)
        + medals_block("coppa_italia_weight", data.coppa_italia_gold, data.coppa_italia_silver, data.coppa_italia_bronze)
        + medals_block(
            "campionato_italiano_weight",
            data.campionato_italiano_gold,
            data.campionato_italiano_silver,
            data.campionato_italiano_bronze,
        )
        + medals_block("international_weight", data.international_gold, data.international_silver, data.international_bronze)
    )

    medals_component = (
        min(medals_points, float(s["medals_cap"])) / float(s["medals_cap"])
    ) * float(s["medals_weight"])

    experience_index = years_component + matches_component + medals_component

    if experience_index < float(s["threshold_level_2"]):
        suggested_level = 1
    elif experience_index < float(s["threshold_level_3"]):
        suggested_level = 2
    elif experience_index < float(s["threshold_level_4"]):
        suggested_level = 3
    else:
        suggested_level = 4

    return {
        "years_component": round(years_component, 2),
        "matches_component": round(matches_component, 2),
        "medals_points": round(medals_points, 2),
        "medals_component": round(medals_component, 2),
        "experience_index": round(experience_index, 2),
        "suggested_level": suggested_level,
    }