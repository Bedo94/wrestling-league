from copy import deepcopy
from datetime import datetime
import json
from typing import Any, Dict, Optional

from sqlalchemy import select

from src.database import get_session
from src.models import CalculationRun, FormulaParameter, FormulaVersion
from src.settings import (
    LEVEL_EVALUATION_SETTINGS,
    MATCHMAKING_SETTINGS,
    RATINGS_SETTINGS,
    SCORING_SETTINGS,
    TEAM_RANKING_SETTINGS,
)
from src.settings_defaults import (
    LEVEL_EVALUATION_SETTINGS_DEFAULTS,
    MATCHMAKING_SETTINGS_DEFAULTS,
    RATINGS_SETTINGS_DEFAULTS,
    SCORING_SETTINGS_DEFAULTS,
    TEAM_RANKING_SETTINGS_DEFAULTS,
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
    return float(raw_value)


def _replace_live_group(target: dict[str, Any], defaults: dict[str, Any]) -> None:
    target.clear()
    target.update(deepcopy(defaults))


def _reset_live_settings_to_defaults() -> None:
    _replace_live_group(SCORING_SETTINGS, SCORING_SETTINGS_DEFAULTS)
    _replace_live_group(MATCHMAKING_SETTINGS, MATCHMAKING_SETTINGS_DEFAULTS)
    _replace_live_group(RATINGS_SETTINGS, RATINGS_SETTINGS_DEFAULTS)
    _replace_live_group(TEAM_RANKING_SETTINGS, TEAM_RANKING_SETTINGS_DEFAULTS)
    _replace_live_group(LEVEL_EVALUATION_SETTINGS, LEVEL_EVALUATION_SETTINGS_DEFAULTS)


def get_all_defaults() -> Dict[str, Dict[str, Any]]:
    return {
        "scoring": deepcopy(SCORING_SETTINGS_DEFAULTS),
        "matchmaking": deepcopy(MATCHMAKING_SETTINGS_DEFAULTS),
        "ratings": deepcopy(RATINGS_SETTINGS_DEFAULTS),
        "team_ranking": deepcopy(TEAM_RANKING_SETTINGS_DEFAULTS),
        "level_evaluation": deepcopy(LEVEL_EVALUATION_SETTINGS_DEFAULTS),
    }


def load_config() -> None:
    """
    Reset live settings to pristine defaults, then override them with values
    stored in FormulaParameter.
    """
    _reset_live_settings_to_defaults()

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
            elif group == "level_evaluation" and key in LEVEL_EVALUATION_SETTINGS:
                LEVEL_EVALUATION_SETTINGS[key] = value
    finally:
        session.close()


def get_parameter(group: str, key: str) -> Any:
    """
    Return the current value for a parameter, falling back to its default.
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
    Persist a set of configuration values to the database.
    """
    session = get_session()
    try:
        for group, params in values.items():
            for key, value in params.items():
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

    load_config()


def reset_to_defaults() -> None:
    """
    Clear all custom configuration values from the database and revert to defaults.
    """
    session = get_session()
    try:
        session.query(FormulaParameter).delete()
        session.commit()
    finally:
        session.close()

    load_config()


def get_group_defaults(group: str) -> dict[str, Any]:
    return deepcopy(get_all_defaults().get(group, {}))


def save_group_parameters(group: str, values: dict[str, Any]) -> None:
    save_parameters({group: values})


def reset_group_to_defaults(group: str) -> None:
    session = get_session()
    try:
        session.query(FormulaParameter).filter(
            FormulaParameter.group_name == group
        ).delete()
        session.commit()
    finally:
        session.close()

    load_config()


# -------------------------------------------------------------------
# Formula versioning helpers
# -------------------------------------------------------------------

def _serialize_config(config: dict[str, Any]) -> str:
    return json.dumps(config, ensure_ascii=False, sort_keys=True)


def _deserialize_config(raw_value: str) -> dict[str, Any]:
    data = json.loads(raw_value)
    if isinstance(data, dict):
        return data
    raise ValueError("config_json non contiene un oggetto JSON valido.")


def get_current_group_config(group: str) -> dict[str, Any]:
    return deepcopy(get_full_config().get(group, {}))


def get_next_formula_version_number(group: str) -> int:
    session = get_session()
    try:
        latest = session.scalar(
            select(FormulaVersion)
            .where(FormulaVersion.group_name == group)
            .order_by(FormulaVersion.version_number.desc())
        )
        if latest is None:
            return 1
        return int(latest.version_number) + 1
    finally:
        session.close()


def list_formula_versions(
    group: Optional[str] = None,
    status: Optional[str] = None,
) -> list[FormulaVersion]:
    session = get_session()
    try:
        stmt = select(FormulaVersion)

        if group:
            stmt = stmt.where(FormulaVersion.group_name == group)

        if status:
            stmt = stmt.where(FormulaVersion.status == status)

        stmt = stmt.order_by(
            FormulaVersion.group_name.asc(),
            FormulaVersion.version_number.desc(),
        )

        return list(session.scalars(stmt).all())
    finally:
        session.close()


def get_formula_version_by_id(formula_version_id: int) -> Optional[FormulaVersion]:
    session = get_session()
    try:
        return session.get(FormulaVersion, formula_version_id)
    finally:
        session.close()


def get_formula_version_config(formula_version_id: int) -> dict[str, Any]:
    session = get_session()
    try:
        formula_version = session.get(FormulaVersion, formula_version_id)
        if formula_version is None:
            raise ValueError(f"FormulaVersion non trovata: id={formula_version_id}")
        return _deserialize_config(formula_version.config_json)
    finally:
        session.close()


def get_latest_published_formula_version(group: str) -> Optional[FormulaVersion]:
    session = get_session()
    try:
        return session.scalar(
            select(FormulaVersion)
            .where(
                FormulaVersion.group_name == group,
                FormulaVersion.status == "published",
            )
            .order_by(FormulaVersion.version_number.desc())
        )
    finally:
        session.close()


def create_formula_version(
    *,
    group: str,
    config: Optional[dict[str, Any]] = None,
    label: Optional[str] = None,
    publish: bool = False,
) -> FormulaVersion:
    """
    Create a new version of a formula group using either the provided config
    or the current live config loaded from FormulaParameter.
    """
    session = get_session()
    try:
        version_number = get_next_formula_version_number(group)
        effective_config = config if config is not None else get_current_group_config(group)

        if publish:
            published_versions = session.scalars(
                select(FormulaVersion).where(
                    FormulaVersion.group_name == group,
                    FormulaVersion.status == "published",
                )
            ).all()
            for existing in published_versions:
                existing.status = "archived"

        formula_version = FormulaVersion(
            group_name=group,
            version_number=version_number,
            label=label or f"{group} v{version_number}",
            config_json=_serialize_config(effective_config),
            status="published" if publish else "draft",
            published_at=datetime.utcnow() if publish else None,
        )

        session.add(formula_version)
        session.commit()
        session.refresh(formula_version)
        return formula_version
    finally:
        session.close()


# -------------------------------------------------------------------
# Calculation run helpers
# -------------------------------------------------------------------

def start_calculation_run(
    *,
    formula_version_id: int,
    environment_name: str,
    scope_type: str = "all",
    scope_reference: Optional[str] = None,
    started_by: Optional[str] = None,
    notes: Optional[str] = None,
) -> CalculationRun:
    session = get_session()
    try:
        calculation_run = CalculationRun(
            formula_version_id=formula_version_id,
            environment_name=environment_name,
            scope_type=scope_type,
            scope_reference=scope_reference,
            status="running",
            started_by=started_by,
            notes=notes,
        )
        session.add(calculation_run)
        session.commit()
        session.refresh(calculation_run)
        return calculation_run
    finally:
        session.close()


def finish_calculation_run(
    run_id: int,
    *,
    status: str = "completed",
    notes: Optional[str] = None,
) -> None:
    session = get_session()
    try:
        calculation_run = session.get(CalculationRun, run_id)
        if calculation_run is None:
            raise ValueError(f"CalculationRun non trovata: id={run_id}")

        calculation_run.status = status
        calculation_run.finished_at = datetime.utcnow()

        if notes is not None:
            calculation_run.notes = notes

        session.commit()
    finally:
        session.close()