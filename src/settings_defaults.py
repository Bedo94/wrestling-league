"""
Single source of truth for pristine default formula settings.

These values must never be mutated at runtime.
Live mutable settings are exposed from src.settings as deep copies.
"""

SCORING_SETTINGS_DEFAULTS = {
    "max_weight_diff_kg": 20.0,
    "weight_bonus_per_kg": 0.05,
    "winner_base_points": 2.0,
    "loser_base_points": 1.0,
    "performance_bonus_max": 0.5,
    "minor_age_threshold": 18,
    "special_bonus_factor": 1.30,
    "retirement_winner_base_points": 1.2,
    "retirement_loser_base_points": 0.3,
    "forfeit_winner_base_points": 0.5,
    "forfeit_loser_base_points": 0.0,
    "points_finish_bonus": 0.0,
    "pinfall_finish_bonus": 0.4,
    "retirement_finish_bonus": 0.0,
    "forfeit_finish_bonus": 0.0,
}

MATCHMAKING_SETTINGS_DEFAULTS = {
    "max_weight_diff_default": 20.0,
    "weight_factor": 3.0,
    "level_factor": 8.0,
    "rating_divisor": 20.0,
    "age_factor": 1.0,
    "rematch_penalty": 15.0,
    "max_level_diff_default": 2,
    "max_age_diff_default": 8,
    "use_rating_default": True,
    "avoid_rematches_default": True,
    "same_sex_only_default": False,
}

RATINGS_SETTINGS_DEFAULTS = {
    "level_start_ratings": {
        1: 900.0,
        2: 1000.0,
        3: 1100.0,
        4: 1200.0,
    },
    "default_start_rating": 1000.0,
    "k_factor": 24.0,
    "logistic_divisor": 400.0,
    "normal_match_impact": 1.0,
    "retirement_match_impact": 0.35,
    "forfeit_match_impact": 0.05,
}

TEAM_RANKING_SETTINGS_DEFAULTS = {
    "participation_bonus_per_athlete": 2.0,
    "ranking_method": "sum_with_bonus",
}

TOKEN_SETTINGS_DEFAULTS = {
    "default_token_budget_per_season": 4,
    "default_token_cost": 1,
}

LEVEL_EVALUATION_SETTINGS_DEFAULTS = {
    "years_weight": 25.0,
    "matches_weight": 25.0,
    "medals_weight": 50.0,
    "years_cap": 10,
    "matches_cap": 80,
    "medals_cap": 20.0,
    "gold_weight": 1.0,
    "silver_weight": 0.6,
    "bronze_weight": 0.35,
    "regional_weight": 1.0,
    "interregional_weight": 1.4,
    "national_open_weight": 1.8,
    "coppa_italia_weight": 2.4,
    "campionato_italiano_weight": 3.0,
    "international_weight": 3.5,
    "threshold_level_2": 20.0,
    "threshold_level_3": 45.0,
    "threshold_level_4": 70.0,
}

ATHLETE_RANKING_SETTINGS_DEFAULTS = {
    "ranking_method": "cumulative",
    "min_matches_for_average": 2,
}

TOKEN_SETTINGS_DEFAULTS = {
    "default_token_budget_per_season": 4,
    "default_token_cost": 1,
    "reset_scope": "event",
}