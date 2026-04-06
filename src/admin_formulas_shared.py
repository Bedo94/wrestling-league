from __future__ import annotations

from datetime import date
from typing import Any

import streamlit as st

from src.models import Athlete
from src.pairing import calculate_age

FLASH_MESSAGE_KEY = "admin_formulas_flash_message"
PENDING_RESET_GROUP_KEY = "admin_formulas_pending_reset_group"


def format_label(key: str) -> str:
    return key.replace("_", " ").capitalize()


def get_typed_value(
    source: dict[str, Any],
    key: str,
    fallback: Any,
    expected_type: type,
) -> Any:
    raw_value = source.get(key, fallback)

    if expected_type is bool:
        return bool(raw_value)
    if expected_type is int:
        return int(raw_value)
    if expected_type is float:
        return float(raw_value)

    return raw_value


def get_widget_value(
    prefix: str,
    key: str,
    fallback: Any,
    expected_type: type,
) -> Any:
    widget_key = f"{prefix}_{key}"
    raw_value = st.session_state.get(widget_key, fallback)

    if expected_type is bool:
        return bool(raw_value)
    if expected_type is int:
        return int(raw_value)
    if expected_type is float:
        return float(raw_value)

    return raw_value


def set_flash_message(kind: str, text: str, target: str | None = None) -> None:
    st.session_state[FLASH_MESSAGE_KEY] = {
        "kind": kind,
        "text": text,
        "target": target,
    }


def render_flash_message(target: str | None = None) -> None:
    message = st.session_state.get(FLASH_MESSAGE_KEY)
    if not message:
        return

    message_target = message.get("target")

    if target is not None and message_target != target:
        return

    if target is None and message_target is not None:
        return

    kind = message.get("kind", "info")
    text = message.get("text", "")

    if kind == "success":
        st.success(text)
    elif kind == "warning":
        st.warning(text)
    elif kind == "error":
        st.error(text)
    else:
        st.info(text)

    del st.session_state[FLASH_MESSAGE_KEY]


def sync_widget_state(prefix: str, values: dict[str, Any]) -> None:
    for key, value in values.items():
        if isinstance(value, dict):
            continue
        st.session_state[f"{prefix}_{key}"] = value


def queue_group_reset(group: str, prefix: str) -> None:
    st.session_state[PENDING_RESET_GROUP_KEY] = {
        "group": group,
        "prefix": prefix,
    }


def apply_pending_reset(group: str, prefix: str) -> None:
    from src.formula_config_service import get_group_defaults

    pending = st.session_state.get(PENDING_RESET_GROUP_KEY)

    if not pending:
        return

    if pending.get("group") != group or pending.get("prefix") != prefix:
        return

    defaults = get_group_defaults(group)
    sync_widget_state(prefix, defaults)
    del st.session_state[PENDING_RESET_GROUP_KEY]


def render_group_inputs(
    config: dict[str, Any],
    order: list[str],
    prefix: str,
) -> dict[str, Any]:
    inputs: dict[str, Any] = {}

    for key in order:
        if key not in config:
            continue

        default = config[key]
        label = format_label(key)
        widget_key = f"{prefix}_{key}"
        widget_exists = widget_key in st.session_state

        if isinstance(default, bool):
            if widget_exists:
                inputs[key] = st.checkbox(label, key=widget_key)
            else:
                inputs[key] = st.checkbox(
                    label,
                    value=bool(default),
                    key=widget_key,
                )

        elif isinstance(default, int) and not isinstance(default, bool):
            if widget_exists:
                inputs[key] = st.number_input(
                    label,
                    step=1,
                    format="%d",
                    key=widget_key,
                )
            else:
                inputs[key] = st.number_input(
                    label,
                    value=int(default),
                    step=1,
                    format="%d",
                    key=widget_key,
                )

        else:
            if widget_exists:
                inputs[key] = st.number_input(
                    label,
                    format="%.3f",
                    key=widget_key,
                )
            else:
                inputs[key] = st.number_input(
                    label,
                    value=float(default),
                    format="%.3f",
                    key=widget_key,
                )

    return inputs


def format_athlete_preview_label(
    athlete: Athlete,
    reference_date: date,
) -> str:
    full_name = f"{athlete.first_name} {athlete.last_name or ''}".strip()
    age = calculate_age(athlete.birth_date, reference_date)
    team = athlete.team or "—"

    return (
        f"{full_name} - "
        f"{athlete.style} - "
        f"{float(athlete.default_weight):.1f} kg - "
        f"{age} anni - "
        f"{team}"
    )


def format_winner_fallback_label(value: str | None) -> str:
    if value == "A":
        return "Atleta A"
    if value == "B":
        return "Atleta B"
    return "Nessun vincitore / pareggio"