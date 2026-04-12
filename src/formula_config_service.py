import hashlib
import json
import math
import re
import tomllib
from copy import deepcopy
from functools import lru_cache
from typing import Any, Optional

import streamlit as st
from sqlalchemy import select
from sqlalchemy.exc import OperationalError, ProgrammingError

from src.database import get_database_url, get_session
from src.models import FormulaRevision
from src.query_cache import DOMAIN_FORMULAS, bump_cache_version, get_cache_version
from src.settings import (
    ATHLETE_RANKING_SETTINGS,
    LEVEL_EVALUATION_SETTINGS,
    MATCHMAKING_SETTINGS,
    RATINGS_SETTINGS,
    SCORING_SETTINGS,
    TEAM_RANKING_SETTINGS,
)
from src.settings_defaults import (
    ATHLETE_RANKING_SETTINGS_DEFAULTS,
    LEVEL_EVALUATION_SETTINGS_DEFAULTS,
    MATCHMAKING_SETTINGS_DEFAULTS,
    RATINGS_SETTINGS_DEFAULTS,
    SCORING_SETTINGS_DEFAULTS,
    TEAM_RANKING_SETTINGS_DEFAULTS,
)

DEFAULT_FORMULA_ENVIRONMENT = "league_local"
FORMULA_ENVIRONMENT_SESSION_KEY = "db_environment"

_TOML_BARE_KEY_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")
_NUMERIC_STRING_PATTERN = re.compile(r"^-?\d+$")


def _resolve_environment_name(environment_name: str | None = None) -> str:
    if environment_name is not None and str(environment_name).strip():
        return str(environment_name).strip()

    try:
        session_environment = st.session_state.get(FORMULA_ENVIRONMENT_SESSION_KEY)
    except Exception:
        session_environment = None

    if session_environment is not None and str(session_environment).strip():
        return str(session_environment).strip()

    return DEFAULT_FORMULA_ENVIRONMENT


def _normalize_config_value(group: str, key: str, value: Any) -> Any:
    if group == "ratings" and key == "level_start_ratings" and isinstance(value, dict):
        normalized: dict[Any, Any] = {}
        for raw_key, raw_item in value.items():
            normalized_key: Any = raw_key
            if isinstance(raw_key, str) and _NUMERIC_STRING_PATTERN.fullmatch(raw_key):
                normalized_key = int(raw_key)
            normalized[normalized_key] = raw_item
        return normalized
    return value


def _normalize_full_config(config: dict[str, Any]) -> dict[str, Any]:
    normalized = deepcopy(config)
    for group, params in normalized.items():
        if not isinstance(params, dict):
            continue
        for key, value in list(params.items()):
            params[key] = _normalize_config_value(group, key, value)
    return normalized


def _format_toml_key(key: Any) -> str:
    key_text = str(key)
    if _TOML_BARE_KEY_PATTERN.fullmatch(key_text):
        return key_text
    return json.dumps(key_text, ensure_ascii=False)


def _format_toml_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("I valori float non finiti non sono supportati nel TOML.")
        return repr(value)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    raise ValueError(f"Tipo non supportato per serializzazione TOML: {type(value)!r}")


def _iter_toml_sections(
    config: dict[str, Any],
    prefix: tuple[Any, ...] = (),
):
    scalar_items: list[tuple[Any, Any]] = []
    nested_items: list[tuple[Any, dict[str, Any]]] = []

    for key, value in config.items():
        if isinstance(value, dict):
            nested_items.append((key, value))
        else:
            scalar_items.append((key, value))

    yield prefix, scalar_items

    for key, nested_value in nested_items:
        yield from _iter_toml_sections(nested_value, (*prefix, key))


def _overlay_config(
    target: dict[str, dict[str, Any]],
    overrides: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    for group, params in overrides.items():
        if not isinstance(params, dict):
            continue
        target_group = target.setdefault(group, {})
        for key, value in params.items():
            if key not in target_group:
                continue
            target_group[key] = _normalize_config_value(group, key, value)
    return target


def _reset_live_settings_to_defaults() -> None:
    SCORING_SETTINGS.clear()
    SCORING_SETTINGS.update(deepcopy(SCORING_SETTINGS_DEFAULTS))

    MATCHMAKING_SETTINGS.clear()
    MATCHMAKING_SETTINGS.update(deepcopy(MATCHMAKING_SETTINGS_DEFAULTS))

    RATINGS_SETTINGS.clear()
    RATINGS_SETTINGS.update(deepcopy(RATINGS_SETTINGS_DEFAULTS))

    TEAM_RANKING_SETTINGS.clear()
    TEAM_RANKING_SETTINGS.update(deepcopy(TEAM_RANKING_SETTINGS_DEFAULTS))

    LEVEL_EVALUATION_SETTINGS.clear()
    LEVEL_EVALUATION_SETTINGS.update(deepcopy(LEVEL_EVALUATION_SETTINGS_DEFAULTS))

    ATHLETE_RANKING_SETTINGS.clear()
    ATHLETE_RANKING_SETTINGS.update(deepcopy(ATHLETE_RANKING_SETTINGS_DEFAULTS))


def _apply_config_to_live_settings(config: dict[str, dict[str, Any]]) -> None:
    normalized_config = _merge_config_with_defaults(config)
    _reset_live_settings_to_defaults()

    SCORING_SETTINGS.update(deepcopy(normalized_config.get("scoring", {})))
    MATCHMAKING_SETTINGS.update(deepcopy(normalized_config.get("matchmaking", {})))
    RATINGS_SETTINGS.update(deepcopy(normalized_config.get("ratings", {})))
    TEAM_RANKING_SETTINGS.update(deepcopy(normalized_config.get("team_ranking", {})))
    LEVEL_EVALUATION_SETTINGS.update(
        deepcopy(normalized_config.get("level_evaluation", {}))
    )
    ATHLETE_RANKING_SETTINGS.update(
        deepcopy(normalized_config.get("athlete_ranking", {}))
    )


def _merge_config_with_defaults(
    config: dict[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    merged = get_all_defaults()
    if config is None:
        return merged
    return _overlay_config(merged, _normalize_full_config(config))


def get_all_defaults() -> dict[str, dict[str, Any]]:
    return {
        "scoring": deepcopy(SCORING_SETTINGS_DEFAULTS),
        "matchmaking": deepcopy(MATCHMAKING_SETTINGS_DEFAULTS),
        "ratings": deepcopy(RATINGS_SETTINGS_DEFAULTS),
        "team_ranking": deepcopy(TEAM_RANKING_SETTINGS_DEFAULTS),
        "level_evaluation": deepcopy(LEVEL_EVALUATION_SETTINGS_DEFAULTS),
        "athlete_ranking": deepcopy(ATHLETE_RANKING_SETTINGS_DEFAULTS),
    }


def load_config(environment_name: str | None = None) -> None:
    resolved_environment_name = _resolve_environment_name(environment_name)
    config = get_full_config(environment_name=resolved_environment_name)
    _apply_config_to_live_settings(config)


def get_parameter(
    group: str,
    key: str,
    *,
    environment_name: str | None = None,
) -> Any:
    config = get_full_config(environment_name=environment_name)
    return config.get(group, {}).get(key)


def get_group_defaults(group: str) -> dict[str, Any]:
    return deepcopy(get_all_defaults().get(group, {}))


def get_full_config(
    environment_name: str | None = None,
) -> dict[str, dict[str, Any]]:
    resolved_environment_name = _resolve_environment_name(environment_name)
    cached_config = _get_full_config_cached(
        get_database_url(hide_password=False),
        get_cache_version(DOMAIN_FORMULAS),
        resolved_environment_name,
    )
    return deepcopy(cached_config)


def get_current_group_config(
    group: str,
    *,
    environment_name: str | None = None,
) -> dict[str, Any]:
    return deepcopy(get_full_config(environment_name=environment_name).get(group, {}))


def build_formula_config_preview_rows(config: dict[str, Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    for group, params in config.items():
        if not isinstance(params, dict):
            continue

        for key, value in params.items():
            if isinstance(value, dict):
                for nested_key, nested_value in sorted(value.items(), key=lambda item: str(item[0])):
                    rows.append(
                        {
                            "Gruppo": str(group),
                            "Parametro": f"{key}.{nested_key}",
                            "Valore": str(nested_value),
                        }
                    )
            else:
                rows.append(
                    {
                        "Gruppo": str(group),
                        "Parametro": str(key),
                        "Valore": str(value),
                    }
                )

    return rows


def serialize_full_config_to_toml(config: dict[str, Any]) -> str:
    normalized_config = _normalize_full_config(config)
    lines: list[str] = []

    for section_path, scalar_items in _iter_toml_sections(normalized_config):
        if section_path:
            if lines:
                lines.append("")
            lines.append(
                f"[{'.'.join(_format_toml_key(path_item) for path_item in section_path)}]"
            )

        for key, value in scalar_items:
            lines.append(f"{_format_toml_key(key)} = {_format_toml_scalar(value)}")

    if not lines:
        return ""

    return "\n".join(lines) + "\n"


def deserialize_full_config_text(
    raw_value: str,
    *,
    config_format: str = "toml",
) -> dict[str, Any]:
    normalized_format = (config_format or "toml").strip().lower()
    if normalized_format == "json":
        data = json.loads(raw_value)
    elif normalized_format == "toml":
        data = tomllib.loads(raw_value)
    else:
        raise ValueError(f"Formato config non supportato: {config_format}")

    if isinstance(data, dict):
        return _normalize_full_config(data)
    raise ValueError("config_text non contiene un oggetto di configurazione valido.")


def _calculate_config_hash(config_text: str) -> str:
    return hashlib.sha256(config_text.encode("utf-8")).hexdigest()


def get_current_config_text(environment_name: str | None = None) -> str:
    return serialize_full_config_to_toml(get_full_config(environment_name=environment_name))


def get_next_formula_revision_number(environment_name: str) -> int:
    resolved_environment_name = _resolve_environment_name(environment_name)
    session = get_session()
    try:
        try:
            latest = session.scalar(
                select(FormulaRevision)
                .where(FormulaRevision.environment_name == resolved_environment_name)
                .order_by(FormulaRevision.revision_number.desc())
            )
        except (OperationalError, ProgrammingError):
            return 1
        if latest is None:
            return 1
        return int(latest.revision_number) + 1
    finally:
        session.close()


def list_formula_revisions(
    environment_name: Optional[str] = None,
    only_active: Optional[bool] = None,
) -> list[FormulaRevision]:
    resolved_environment_name = (
        _resolve_environment_name(environment_name)
        if environment_name is not None
        else None
    )

    return list(
        _list_formula_revisions_cached(
            get_database_url(hide_password=False),
            get_cache_version(DOMAIN_FORMULAS),
            resolved_environment_name,
            only_active,
        )
    )


def get_formula_revision_by_id(formula_revision_id: int) -> Optional[FormulaRevision]:
    return _get_formula_revision_by_id_cached(
        get_database_url(hide_password=False),
        get_cache_version(DOMAIN_FORMULAS),
        formula_revision_id,
    )


def get_formula_revision_config(formula_revision_id: int) -> dict[str, Any]:
    session = get_session()
    try:
        try:
            formula_revision = session.get(FormulaRevision, formula_revision_id)
        except (OperationalError, ProgrammingError) as exc:
            raise ValueError("La tabella formula_revisions non è ancora disponibile.") from exc
        if formula_revision is None:
            raise ValueError(f"FormulaRevision non trovata: id={formula_revision_id}")
        return _merge_config_with_defaults(
            deserialize_full_config_text(
                formula_revision.config_text,
                config_format=formula_revision.config_format,
            )
        )
    finally:
        session.close()


def get_active_formula_revision(environment_name: str | None = None) -> Optional[FormulaRevision]:
    resolved_environment_name = _resolve_environment_name(environment_name)
    return _get_active_formula_revision_cached(
        get_database_url(hide_password=False),
        get_cache_version(DOMAIN_FORMULAS),
        resolved_environment_name,
    )


@lru_cache(maxsize=32)
def _get_active_formula_revision_cached(
    database_url: str,
    formulas_version: int,
    resolved_environment_name: str,
) -> Optional[FormulaRevision]:
    session = get_session()
    try:
        try:
            return session.scalar(
                select(FormulaRevision)
                .where(
                    FormulaRevision.environment_name == resolved_environment_name,
                    FormulaRevision.is_active.is_(True),
                )
                .order_by(FormulaRevision.revision_number.desc())
            )
        except (OperationalError, ProgrammingError):
            return None
    finally:
        session.close()


@lru_cache(maxsize=64)
def _get_formula_revision_by_id_cached(
    database_url: str,
    formulas_version: int,
    formula_revision_id: int,
) -> Optional[FormulaRevision]:
    session = get_session()
    try:
        try:
            return session.get(FormulaRevision, formula_revision_id)
        except (OperationalError, ProgrammingError):
            return None
    finally:
        session.close()


@lru_cache(maxsize=64)
def _get_formula_revision_config_cached(
    database_url: str,
    formulas_version: int,
    formula_revision_id: int,
) -> dict[str, dict[str, Any]]:
    session = get_session()
    try:
        try:
            formula_revision = session.get(FormulaRevision, formula_revision_id)
        except (OperationalError, ProgrammingError) as exc:
            raise ValueError("La tabella formula_revisions non Ã¨ ancora disponibile.") from exc
        if formula_revision is None:
            raise ValueError(f"FormulaRevision non trovata: id={formula_revision_id}")
        return _merge_config_with_defaults(
            deserialize_full_config_text(
                formula_revision.config_text,
                config_format=formula_revision.config_format,
            )
        )
    finally:
        session.close()


def get_formula_revision_config(formula_revision_id: int) -> dict[str, Any]:
    return deepcopy(
        _get_formula_revision_config_cached(
            get_database_url(hide_password=False),
            get_cache_version(DOMAIN_FORMULAS),
            formula_revision_id,
        )
    )


@lru_cache(maxsize=32)
def _list_formula_revisions_cached(
    database_url: str,
    formulas_version: int,
    resolved_environment_name: str | None,
    only_active: Optional[bool],
) -> tuple[FormulaRevision, ...]:
    session = get_session()
    try:
        stmt = select(FormulaRevision)

        if resolved_environment_name:
            stmt = stmt.where(
                FormulaRevision.environment_name == resolved_environment_name
            )

        if only_active is not None:
            stmt = stmt.where(FormulaRevision.is_active.is_(only_active))

        stmt = stmt.order_by(
            FormulaRevision.environment_name.asc(),
            FormulaRevision.revision_number.desc(),
        )

        try:
            return tuple(session.scalars(stmt).all())
        except (OperationalError, ProgrammingError):
            return ()
    finally:
        session.close()


@lru_cache(maxsize=32)
def _get_full_config_cached(
    database_url: str,
    formulas_version: int,
    resolved_environment_name: str,
) -> dict[str, dict[str, Any]]:
    active_revision = _get_active_formula_revision_cached(
        database_url,
        formulas_version,
        resolved_environment_name,
    )

    if active_revision is None:
        return get_all_defaults()

    config = deserialize_full_config_text(
        active_revision.config_text,
        config_format=active_revision.config_format,
    )
    return _merge_config_with_defaults(config)


def apply_full_config(config: dict[str, dict[str, Any]]) -> None:
    _apply_config_to_live_settings(config)


def create_formula_revision(
    *,
    environment_name: str,
    config: Optional[dict[str, dict[str, Any]]] = None,
    label: Optional[str] = None,
    note: Optional[str] = None,
    source_revision_id: Optional[int] = None,
    created_by: Optional[str] = None,
    activate: bool = False,
) -> FormulaRevision:
    resolved_environment_name = _resolve_environment_name(environment_name)
    created_revision: FormulaRevision | None = None

    session = get_session()
    try:
        revision_number = get_next_formula_revision_number(resolved_environment_name)
        current_active_revision = session.scalar(
            select(FormulaRevision).where(
                FormulaRevision.environment_name == resolved_environment_name,
                FormulaRevision.is_active.is_(True),
            )
        )
        effective_config = _merge_config_with_defaults(
            config
            if config is not None
            else get_full_config(environment_name=resolved_environment_name)
        )
        config_text = serialize_full_config_to_toml(effective_config)
        effective_source_revision_id = source_revision_id

        if effective_source_revision_id is None and current_active_revision is not None:
            effective_source_revision_id = current_active_revision.id

        if activate:
            active_revisions = session.scalars(
                select(FormulaRevision).where(
                    FormulaRevision.environment_name == resolved_environment_name,
                    FormulaRevision.is_active.is_(True),
                )
            ).all()
            for existing in active_revisions:
                existing.is_active = False

        formula_revision = FormulaRevision(
            environment_name=resolved_environment_name,
            revision_number=revision_number,
            is_active=activate,
            label=label or f"{resolved_environment_name} rev {revision_number}",
            note=note,
            source_revision_id=effective_source_revision_id,
            config_format="toml",
            config_text=config_text,
            config_hash=_calculate_config_hash(config_text),
            created_by=created_by,
        )

        session.add(formula_revision)
        session.commit()
        session.refresh(formula_revision)
        created_revision = formula_revision
    finally:
        session.close()

    bump_cache_version(DOMAIN_FORMULAS)

    if activate:
        load_config(environment_name=resolved_environment_name)

    if created_revision is None:
        raise RuntimeError("Impossibile creare la FormulaRevision.")

    return created_revision


def activate_formula_revision(formula_revision_id: int) -> None:
    environment_name: str | None = None

    session = get_session()
    try:
        formula_revision = session.get(FormulaRevision, formula_revision_id)
        if formula_revision is None:
            raise ValueError(f"FormulaRevision non trovata: id={formula_revision_id}")

        environment_name = formula_revision.environment_name

        active_revisions = session.scalars(
            select(FormulaRevision).where(
                FormulaRevision.environment_name == environment_name,
                FormulaRevision.is_active.is_(True),
                FormulaRevision.id != formula_revision.id,
            )
        ).all()
        for existing in active_revisions:
            existing.is_active = False

        formula_revision.is_active = True
        session.commit()
    finally:
        session.close()

    bump_cache_version(DOMAIN_FORMULAS)

    if environment_name is not None:
        load_config(environment_name=environment_name)
