from datetime import date
from typing import Any, Dict

from sqlalchemy import select

from src.database import get_session
from src.models import FormulaParameter
from src.settings import (
    SCORING_SETTINGS,
    MATCHMAKING_SETTINGS,
    RATINGS_SETTINGS,
    TEAM_RANKING_SETTINGS,
)


def parse_value(raw_value: str, value_type: str | None = None) -> Any:
    """
    Parse a raw string value from the database into the appropriate Python type.

    Supported types are: 'float', 'int', 'bool', 'str'.
    Defaults to float if no type is provided.
    """
    t = (value_type or "float").lower()
    if t == "bool":
        return raw_value.lower() in {"1", "true", "yes", "y"}
    if t == "int":
        return int(raw_value)
    if t == "str":
        return raw_value
    # default to float
    return float(raw_value)


def get_all_defaults() -> Dict[str, Dict[str, Any]]:
    """
    Return a nested dict containing the default configuration values for all sections.
    """
    return {
        "scoring": dict(SCORING_SETTINGS),
        "matchmaking": dict(MATCHMAKING_SETTINGS),
        "ratings": dict(RATINGS_SETTINGS),
        "team_ranking": dict(TEAM_RANKING_SETTINGS),
    }


def load_config() -> None:
    """
    Load configuration values from the database and override the default dictionaries
    defined in src.settings. This function should be called after the database
    has been initialised to ensure custom parameters are applied.
    """
    session = get_session()
    try:
        params = session.scalars(select(FormulaParameter)).all()
        for param in params:
            value = parse_value(param.value, param.value_type)
            group = param.group_name
            key = param.key
            if group == "scoring" and key in SCORING_SETTINGS:
                SCORING_SETTINGS[key] = value
            elif group == "matchmaking" and key in MATCHMAKING_SETTINGS:
                MATCHMAKING_SETTINGS[key] = value
            elif group == "ratings" and key in RATINGS_SETTINGS:
                RATINGS_SETTINGS[key] = value
            elif group == "team_ranking" and key in TEAM_RANKING_SETTINGS:
                TEAM_RANKING_SETTINGS[key] = value
    finally:
        session.close()


def get_parameter(group: str, key: str) -> Any:
    """
    Return the current value for a parameter, falling back to its default.

    Parameters are organised by section (group). If a custom value is stored
    in the database it will be returned; otherwise the default is used.
    """
    defaults = get_all_defaults()
    session = get_session()
    try:
        param: FormulaParameter | None = session.scalar(
            select(FormulaParameter).where(
                FormulaParameter.group_name == group,
                FormulaParameter.key == key,
            )
        )
        if param:
            return parse_value(param.value, param.value_type)
        return defaults.get(group, {}).get(key)
    finally:
        session.close()


def get_full_config() -> Dict[str, Dict[str, Any]]:
    """
    Return the complete configuration, merging defaults with any custom values.
    """
    config = get_all_defaults()
    session = get_session()
    try:
        params = session.scalars(select(FormulaParameter)).all()
        for param in params:
            value = parse_value(param.value, param.value_type)
            group = param.group_name
            key = param.key
            section = config.setdefault(group, {})
            section[key] = value
        return config
    finally:
        session.close()


def save_parameters(values: Dict[str, Dict[str, Any]]) -> None:
    """
    Persist a set of configuration values to the database. Values should be
    provided as a nested dict of the form {group: {key: value}}.

    Existing rows are updated, and new rows are inserted as needed.
    """
    session = get_session()
    try:
        for group, params in values.items():
            for key, value in params.items():
                # infer type based on value instance
                if isinstance(value, bool):
                    value_type = "bool"
                elif isinstance(value, int) and not isinstance(value, bool):
                    value_type = "int"
                elif isinstance(value, float):
                    value_type = "float"
                else:
                    value_type = "str"
                value_str = str(value)
                existing: FormulaParameter | None = session.scalar(
                    select(FormulaParameter).where(
                        FormulaParameter.group_name == group,
                        FormulaParameter.key == key,
                    )
                )
                if existing:
                    existing.value = value_str
                    existing.value_type = value_type
                else:
                    session.add(
                        FormulaParameter(
                            group_name=group,
                            key=key,
                            value=value_str,
                            value_type=value_type,
                        )
                    )
        session.commit()
    finally:
        session.close()
    # reload dictionaries in src.settings so that live values are applied
    load_config()


def reset_to_defaults() -> None:
    """
    Clear all custom configuration values from the database and revert to
    the defaults defined in src.settings.
    """
    session = get_session()
    try:
        session.query(FormulaParameter).delete()
        session.commit()
    finally:
        session.close()
    # reload default dictionaries
    load_config()