"""
Configuration defaults for the wrestling league formulas.

This module defines the default parameters used for scoring, matchmaking,
ratings, and team ranking formulas. The values mirror those currently
in use in the project and can be overridden at runtime by values stored
in the database via the formula configuration service.
"""

# Default scoring parameters
SCORING_SETTINGS = {
    "max_weight_diff_kg": 10.0,
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
}

# Default matchmaking parameters
MATCHMAKING_SETTINGS = {
    "max_weight_diff_default": 10.0,
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

# Default ratings parameters
RATINGS_SETTINGS = {
    "level_start_ratings": {
        1: 900.0,
        2: 1000.0,
        3: 1100.0,
        4: 1200.0,
    },
    "default_start_rating": 1000.0,
    "k_factor": 24.0,
    "normal_match_impact": 1.0,
    "retirement_match_impact": 0.35,
    "forfeit_match_impact": 0.05,
}

# Default team ranking parameters
TEAM_RANKING_SETTINGS = {
    "participation_bonus_per_athlete": 2.0,
}