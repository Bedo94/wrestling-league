from __future__ import annotations

from datetime import date
from typing import Optional

import pandas as pd
import streamlit as st

from src.athletes import (
    get_tokens_remaining,
    list_athletes,
)
from src.db_runtime import bootstrap_database_from_state
from src.events import list_events
from src.levels import get_level_label
from src.matches import (
    build_match_points_map,
    create_match,
    delete_match,
    list_matches,
    replace_match,
)
from src.models import Match
from src.ratings import recompute_ratings
from src.reference_data import WIN_TYPE_OPTIONS
from src.scoring import calculate_match_points, validate_weight_difference
from src.table_component import render_table_component
from src.table_specs import MATCHES_TABLE_SPEC
from src.token_usage import (
    TOKEN_USED_BY_ATHLETE_A,
    TOKEN_USED_BY_ATHLETE_B,
    TokenUsedBy,
    get_token_spender_id_from_used_by,
    get_token_used_by_from_spender_id,
)

MATCH_SAVE_FLASH_KEY = "matches_save_flash"
MATCH_DELETE_FLASH_KEY = "matches_delete_flash"
MATCH_EDIT_ID_KEY = "match_editing_id"
MATCH_DELETE_CANDIDATE_ID_KEY = "match_delete_candidate_id"
MATCH_DELETE_CANDIDATE_IDS_KEY = "match_delete_candidate_ids"
MATCH_TABLE_SELECTED_ID_KEY = "match_table_selected_id"
MATCH_IGNORE_TABLE_SYNC_KEY = "match_ignore_table_sync_once"
MATCH_FORM_RESET_PENDING_KEY = "match_form_reset_pending"

MATCH_EVENT_ID_KEY = "match_event_id"
MATCH_ATHLETE_A_ID_KEY = "match_athlete_a_id"
MATCH_ATHLETE_B_ID_KEY = "match_athlete_b_id"
MATCH_WEIGHT_A_KEY = "match_weight_a"
MATCH_WEIGHT_B_KEY = "match_weight_b"
MATCH_RAW_SCORE_A_KEY = "match_raw_score_a"
MATCH_RAW_SCORE_B_KEY = "match_raw_score_b"
MATCH_WINNER_CHOICE_KEY = "match_winner_choice"
MATCH_WIN_TYPE_KEY = "match_win_type"
MATCH_NOTES_KEY = "match_notes"
MATCH_TOKEN_ENABLED_KEY = "match_token_enabled"
MATCH_TOKEN_USED_BY_KEY = "match_token_used_by"


def calculate_age(birth_date: date, reference_date: date) -> int:
    age = reference_date.year - birth_date.year
    if (reference_date.month, reference_date.day) < (birth_date.month, birth_date.day):
        age -= 1
    return age


def athlete_label(athlete, reference_date: date) -> str:
    full_name = f"{athlete.first_name} {athlete.last_name or ''}".strip()
    inactive_suffix = " (inattivo)" if not athlete.active else ""
    age = calculate_age(athlete.birth_date, reference_date)
    team_label = (athlete.team or "").strip() or "Senza team"

    return (
        f"{full_name}{inactive_suffix} — {athlete.style} — "
        f"{athlete.default_weight:.1f} kg — {age} anni — {team_label}"
    )


def event_label(event) -> str:
    return f"{event.name} — {event.event_date}"


def format_athlete_name(athlete) -> str:
    if athlete is None:
        return ""
    return f"{athlete.first_name} {athlete.last_name or ''}".strip()


def format_event_name(event, fallback_event_id: int) -> str:
    if event is None:
        return f"ID {fallback_event_id}"
    return event.name


def format_event_date(event):
    if event is None:
        return ""
    return event.event_date


def match_label(match: Match, athletes_map, events_map) -> str:
    athlete_a = athletes_map.get(match.athlete_a_id)
    athlete_b = athletes_map.get(match.athlete_b_id)
    event = events_map.get(match.event_id)

    athlete_a_name = format_athlete_name(athlete_a) or f"ID {match.athlete_a_id}"
    athlete_b_name = format_athlete_name(athlete_b) or f"ID {match.athlete_b_id}"
    event_name = format_event_name(event, match.event_id)
    event_date = format_event_date(event)

    return f"#{match.id} — {event_name} {event_date} — {athlete_a_name} vs {athlete_b_name}"


def set_flash(flash_key: str, kind: str, message: str) -> None:
    st.session_state[flash_key] = {"kind": kind, "message": message}


def show_flash(flash_key: str) -> None:
    flash = st.session_state.pop(flash_key, None)
    if flash:
        getattr(st, flash["kind"], st.info)(flash["message"])


def schedule_match_form_reset() -> None:
    st.session_state[MATCH_FORM_RESET_PENDING_KEY] = True


def reset_match_form(event_ids, athlete_ids, athletes_map) -> None:
    default_event_id = event_ids[0]
    default_athlete_a_id = athlete_ids[0]
    default_athlete_b_id = athlete_ids[1] if len(athlete_ids) > 1 else athlete_ids[0]

    st.session_state[MATCH_EDIT_ID_KEY] = None
    st.session_state[MATCH_EVENT_ID_KEY] = default_event_id
    st.session_state[MATCH_ATHLETE_A_ID_KEY] = default_athlete_a_id
    st.session_state[MATCH_ATHLETE_B_ID_KEY] = default_athlete_b_id
    st.session_state[MATCH_WEIGHT_A_KEY] = float(
        athletes_map[default_athlete_a_id].default_weight
    )
    st.session_state[MATCH_WEIGHT_B_KEY] = float(
        athletes_map[default_athlete_b_id].default_weight
    )
    st.session_state[MATCH_RAW_SCORE_A_KEY] = 0.0
    st.session_state[MATCH_RAW_SCORE_B_KEY] = 0.0
    st.session_state[MATCH_WINNER_CHOICE_KEY] = "Atleta A"
    st.session_state[MATCH_WIN_TYPE_KEY] = WIN_TYPE_OPTIONS[0]
    st.session_state[MATCH_NOTES_KEY] = ""
    st.session_state[MATCH_TOKEN_ENABLED_KEY] = False
    st.session_state[MATCH_TOKEN_USED_BY_KEY] = TOKEN_USED_BY_ATHLETE_A


def ensure_match_form_state(event_ids, athlete_ids, athletes_map) -> None:
    if MATCH_EVENT_ID_KEY not in st.session_state:
        reset_match_form(event_ids, athlete_ids, athletes_map)
        return

    if st.session_state.get(MATCH_EVENT_ID_KEY) not in event_ids:
        st.session_state[MATCH_EVENT_ID_KEY] = event_ids[0]

    if st.session_state.get(MATCH_ATHLETE_A_ID_KEY) not in athlete_ids:
        st.session_state[MATCH_ATHLETE_A_ID_KEY] = athlete_ids[0]

    if st.session_state.get(MATCH_ATHLETE_B_ID_KEY) not in athlete_ids:
        fallback_b = athlete_ids[1] if len(athlete_ids) > 1 else athlete_ids[0]
        st.session_state[MATCH_ATHLETE_B_ID_KEY] = fallback_b

    if st.session_state[MATCH_ATHLETE_A_ID_KEY] == st.session_state[MATCH_ATHLETE_B_ID_KEY]:
        for athlete_id in athlete_ids:
            if athlete_id != st.session_state[MATCH_ATHLETE_A_ID_KEY]:
                st.session_state[MATCH_ATHLETE_B_ID_KEY] = athlete_id
                break

    if MATCH_WEIGHT_A_KEY not in st.session_state:
        st.session_state[MATCH_WEIGHT_A_KEY] = float(
            athletes_map[st.session_state[MATCH_ATHLETE_A_ID_KEY]].default_weight
        )

    if MATCH_WEIGHT_B_KEY not in st.session_state:
        st.session_state[MATCH_WEIGHT_B_KEY] = float(
            athletes_map[st.session_state[MATCH_ATHLETE_B_ID_KEY]].default_weight
        )

    if MATCH_RAW_SCORE_A_KEY not in st.session_state:
        st.session_state[MATCH_RAW_SCORE_A_KEY] = 0.0

    if MATCH_RAW_SCORE_B_KEY not in st.session_state:
        st.session_state[MATCH_RAW_SCORE_B_KEY] = 0.0

    if MATCH_WINNER_CHOICE_KEY not in st.session_state:
        st.session_state[MATCH_WINNER_CHOICE_KEY] = "Atleta A"

    if MATCH_WIN_TYPE_KEY not in st.session_state:
        st.session_state[MATCH_WIN_TYPE_KEY] = WIN_TYPE_OPTIONS[0]

    if MATCH_NOTES_KEY not in st.session_state:
        st.session_state[MATCH_NOTES_KEY] = ""

    if MATCH_TOKEN_ENABLED_KEY not in st.session_state:
        st.session_state[MATCH_TOKEN_ENABLED_KEY] = False

    if MATCH_TOKEN_USED_BY_KEY not in st.session_state:
        st.session_state[MATCH_TOKEN_USED_BY_KEY] = TOKEN_USED_BY_ATHLETE_A

    if MATCH_EDIT_ID_KEY not in st.session_state:
        st.session_state[MATCH_EDIT_ID_KEY] = None

    if MATCH_DELETE_CANDIDATE_ID_KEY not in st.session_state:
        st.session_state[MATCH_DELETE_CANDIDATE_ID_KEY] = None

    if MATCH_DELETE_CANDIDATE_IDS_KEY not in st.session_state:
        st.session_state[MATCH_DELETE_CANDIDATE_IDS_KEY] = []

    if MATCH_TABLE_SELECTED_ID_KEY not in st.session_state:
        st.session_state[MATCH_TABLE_SELECTED_ID_KEY] = None

    if MATCH_IGNORE_TABLE_SYNC_KEY not in st.session_state:
        st.session_state[MATCH_IGNORE_TABLE_SYNC_KEY] = False


def sync_weight_a_from_selected_athlete(athletes_map) -> None:
    athlete_id = st.session_state.get(MATCH_ATHLETE_A_ID_KEY)
    athlete = athletes_map.get(athlete_id)
    if athlete is not None:
        st.session_state[MATCH_WEIGHT_A_KEY] = float(athlete.default_weight)


def sync_weight_b_from_selected_athlete(athletes_map) -> None:
    athlete_id = st.session_state.get(MATCH_ATHLETE_B_ID_KEY)
    athlete = athletes_map.get(athlete_id)
    if athlete is not None:
        st.session_state[MATCH_WEIGHT_B_KEY] = float(athlete.default_weight)


def load_match_into_form(match: Match) -> None:
    st.session_state[MATCH_EDIT_ID_KEY] = match.id
    st.session_state[MATCH_EVENT_ID_KEY] = match.event_id
    st.session_state[MATCH_ATHLETE_A_ID_KEY] = match.athlete_a_id
    st.session_state[MATCH_ATHLETE_B_ID_KEY] = match.athlete_b_id
    st.session_state[MATCH_WEIGHT_A_KEY] = float(match.weight_a)
    st.session_state[MATCH_WEIGHT_B_KEY] = float(match.weight_b)
    st.session_state[MATCH_RAW_SCORE_A_KEY] = float(match.raw_score_a)
    st.session_state[MATCH_RAW_SCORE_B_KEY] = float(match.raw_score_b)
    st.session_state[MATCH_WINNER_CHOICE_KEY] = (
        "Atleta A" if match.winner_id == match.athlete_a_id else "Atleta B"
    )
    st.session_state[MATCH_WIN_TYPE_KEY] = match.win_type
    st.session_state[MATCH_NOTES_KEY] = match.notes or ""
    token_used_by = get_token_used_by_from_spender_id(
        athlete_a_id=match.athlete_a_id,
        athlete_b_id=match.athlete_b_id,
        token_spender_id=match.token_spender_id,
    )
    st.session_state[MATCH_TOKEN_ENABLED_KEY] = token_used_by is not None
    st.session_state[MATCH_TOKEN_USED_BY_KEY] = (
        token_used_by or TOKEN_USED_BY_ATHLETE_A
    )


def get_last_selected_match(
    selected_match_ids: list[int],
    matches: list[Match],
) -> Optional[Match]:
    if not selected_match_ids:
        return None

    last_selected_match_id = selected_match_ids[-1]
    return next((match for match in matches if match.id == last_selected_match_id), None)


def _build_matches_dataframe(
    matches: list[Match],
    athletes_map,
    events_map,
    match_points_by_id,
) -> pd.DataFrame:
    rows = []
    for match in matches:
        athlete_a = athletes_map.get(match.athlete_a_id)
        athlete_b = athletes_map.get(match.athlete_b_id)
        winner = athletes_map.get(match.winner_id) if match.winner_id else None
        token_spender = (
            athletes_map.get(match.token_spender_id) if match.token_spender_id else None
        )
        event = events_map.get(match.event_id)
        match_points = match_points_by_id.get(
            match.id,
            {"points_a": 0.0, "points_b": 0.0},
        )

        rows.append(
            {
                "ID": match.id,
                "Evento": format_event_name(event, match.event_id),
                "Data": format_event_date(event),
                "Stile": match.style,
                "Atleta A": format_athlete_name(athlete_a),
                "Peso A": match.weight_a,
                "Livello A": get_level_label(match.level_a),
                "Punti A": match.raw_score_a,
                "Atleta B": format_athlete_name(athlete_b),
                "Peso B": match.weight_b,
                "Livello B": get_level_label(match.level_b),
                "Punti B": match.raw_score_b,
                "Vincitore": format_athlete_name(winner),
                "Modo vittoria": match.win_type,
                "Token": "Sì" if match.token_spender_id is not None else "",
                "Spende token": format_athlete_name(token_spender),
                "Punti classifica A": match_points["points_a"],
                "Punti classifica B": match_points["points_b"],
                "Note": match.notes or "",
            }
        )

    return pd.DataFrame(rows)


def _render_matches_list(
    *,
    matches: list[Match],
    matches_df: pd.DataFrame,
    athletes_map,
    events_map,
) -> tuple[list[int], Optional[Match]]:
    st.divider()
    st.subheader("Lista incontri")

    selected_match_ids: list[int] = []
    selected_match: Optional[Match] = None

    if matches_df.empty:
        st.info("Nessun incontro presente.")
        return selected_match_ids, selected_match

    matches_table_result = render_table_component(
        df=matches_df,
        spec=MATCHES_TABLE_SPEC,
        renderer="aggrid",
        key="matches_table",
    )

    if (
        not matches_table_result.selected_rows_df.empty
        and "ID" in matches_table_result.selected_rows_df.columns
    ):
        selected_match_ids = [
            int(match_id)
            for match_id in matches_table_result.selected_rows_df["ID"].tolist()
        ]

    selected_match = get_last_selected_match(selected_match_ids, matches)

    if st.session_state.get(MATCH_IGNORE_TABLE_SYNC_KEY):
        st.session_state[MATCH_IGNORE_TABLE_SYNC_KEY] = False
    elif selected_match is not None:
        last_loaded_match_id = st.session_state.get(MATCH_TABLE_SELECTED_ID_KEY)
        if selected_match.id != last_loaded_match_id:
            load_match_into_form(selected_match)
            st.session_state[MATCH_TABLE_SELECTED_ID_KEY] = selected_match.id

    return selected_match_ids, selected_match


def _render_match_form(
    *,
    events_map,
    athletes_map,
    event_ids,
    athlete_ids,
) -> None:
    st.subheader("Aggiungi incontro")

    selected_event_id = st.selectbox(
        "Evento *",
        options=event_ids,
        format_func=lambda event_id: event_label(events_map[event_id]),
        key=MATCH_EVENT_ID_KEY,
    )

    selected_event = events_map[selected_event_id]
    reference_date_for_labels = selected_event.event_date

    athlete_col1, athlete_col2 = st.columns(2)

    with athlete_col1:
        st.markdown("#### Atleta A")

        selected_athlete_a_id = st.selectbox(
            "Seleziona atleta A *",
            options=athlete_ids,
            format_func=lambda athlete_id: athlete_label(
                athletes_map[athlete_id],
                reference_date=reference_date_for_labels,
            ),
            key=MATCH_ATHLETE_A_ID_KEY,
            on_change=sync_weight_a_from_selected_athlete,
            args=(athletes_map,),
        )

        athlete_a = athletes_map[selected_athlete_a_id]

        weight_a = st.number_input(
            "Peso atleta A (kg) *",
            min_value=1.0,
            max_value=300.0,
            step=0.5,
            key=MATCH_WEIGHT_A_KEY,
        )

        raw_score_a = st.number_input(
            "Punti atleta A *",
            min_value=0.0,
            max_value=200.0,
            step=1.0,
            key=MATCH_RAW_SCORE_A_KEY,
        )

    with athlete_col2:
        st.markdown("#### Atleta B")

        selected_athlete_b_id = st.selectbox(
            "Seleziona atleta B *",
            options=athlete_ids,
            format_func=lambda athlete_id: athlete_label(
                athletes_map[athlete_id],
                reference_date=reference_date_for_labels,
            ),
            key=MATCH_ATHLETE_B_ID_KEY,
            on_change=sync_weight_b_from_selected_athlete,
            args=(athletes_map,),
        )

        athlete_b = athletes_map[selected_athlete_b_id]

        weight_b = st.number_input(
            "Peso atleta B (kg) *",
            min_value=1.0,
            max_value=300.0,
            step=0.5,
            key=MATCH_WEIGHT_B_KEY,
        )

        raw_score_b = st.number_input(
            "Punti atleta B *",
            min_value=0.0,
            max_value=200.0,
            step=1.0,
            key=MATCH_RAW_SCORE_B_KEY,
        )

    winner_col1, winner_col2 = st.columns(2)
    current_winner_choice = st.session_state.get(MATCH_WINNER_CHOICE_KEY, "Atleta A")

    with winner_col1:
        st.markdown("#### Esito atleta A")
        if st.button(
            f"Vince {format_athlete_name(athlete_a)}",
            type="primary" if current_winner_choice == "Atleta A" else "secondary",
            use_container_width=True,
            key="winner_button_a",
        ):
            if st.session_state.get(MATCH_WINNER_CHOICE_KEY) != "Atleta A":
                st.session_state[MATCH_WINNER_CHOICE_KEY] = "Atleta A"
                st.rerun()

    with winner_col2:
        st.markdown("#### Esito atleta B")
        if st.button(
            f"Vince {format_athlete_name(athlete_b)}",
            type="primary" if current_winner_choice == "Atleta B" else "secondary",
            use_container_width=True,
            key="winner_button_b",
        ):
            if st.session_state.get(MATCH_WINNER_CHOICE_KEY) != "Atleta B":
                st.session_state[MATCH_WINNER_CHOICE_KEY] = "Atleta B"
                st.rerun()

    winner_choice = st.session_state.get(MATCH_WINNER_CHOICE_KEY, "Atleta A")

    win_type = st.selectbox(
        "Modo di vittoria *",
        options=WIN_TYPE_OPTIONS,
        key=MATCH_WIN_TYPE_KEY,
    )

    token_enabled = st.checkbox(
        "Usa token in questo incontro",
        key=MATCH_TOKEN_ENABLED_KEY,
        help=(
            "Attivalo se uno dei due atleti decide di usare un token in questo match. "
            "Il costo è sempre 1 token. "
            "I token disponibili si azzerano a ogni nuovo evento."
        ),
    )

    token_spender_id: Optional[int] = None

    if token_enabled:
        st.markdown("#### Chi spende il token?")
        current_token_used_by: TokenUsedBy = st.session_state.get(
            MATCH_TOKEN_USED_BY_KEY,
            TOKEN_USED_BY_ATHLETE_A,
        )

        token_col1, token_col2 = st.columns(2)

        with token_col1:
            if st.button(
                format_athlete_name(athlete_a),
                type=(
                    "primary"
                    if current_token_used_by == TOKEN_USED_BY_ATHLETE_A
                    else "secondary"
                ),
                use_container_width=True,
                key="token_spender_button_a",
            ):
                if st.session_state.get(MATCH_TOKEN_USED_BY_KEY) != TOKEN_USED_BY_ATHLETE_A:
                    st.session_state[MATCH_TOKEN_USED_BY_KEY] = TOKEN_USED_BY_ATHLETE_A
                    st.rerun()

        with token_col2:
            if st.button(
                format_athlete_name(athlete_b),
                type=(
                    "primary"
                    if current_token_used_by == TOKEN_USED_BY_ATHLETE_B
                    else "secondary"
                ),
                use_container_width=True,
                key="token_spender_button_b",
            ):
                if st.session_state.get(MATCH_TOKEN_USED_BY_KEY) != TOKEN_USED_BY_ATHLETE_B:
                    st.session_state[MATCH_TOKEN_USED_BY_KEY] = TOKEN_USED_BY_ATHLETE_B
                    st.rerun()

        token_used_by: TokenUsedBy = st.session_state.get(
            MATCH_TOKEN_USED_BY_KEY,
            TOKEN_USED_BY_ATHLETE_A,
        )
        token_spender = (
            athlete_a
            if token_used_by == TOKEN_USED_BY_ATHLETE_A
            else athlete_b
        )
        editing_match_id = st.session_state.get(MATCH_EDIT_ID_KEY)

        remaining_tokens = get_tokens_remaining(
            athlete_id=token_spender.id,
            event_id=selected_event.id,
            exclude_match_id=editing_match_id,
        )
        st.caption(
            f"{format_athlete_name(token_spender)} ha {remaining_tokens} token disponibili "
            f"per questo evento."
        )

        token_spender_id = get_token_spender_id_from_used_by(
            athlete_a_id=athlete_a.id,
            athlete_b_id=athlete_b.id,
            token_used_by=token_used_by,
        )

    notes = st.text_area("Note", key=MATCH_NOTES_KEY)

    submitted = st.button("Salva", type="primary", use_container_width=True)

    if not submitted:
        return

    if athlete_a.id == athlete_b.id:
        st.error("Atleta A e Atleta B devono essere diversi.")
        return

    if athlete_a.style != athlete_b.style:
        st.error("Gli atleti devono avere lo stesso stile di lotta.")
        return

    winner_id = athlete_a.id if winner_choice == "Atleta A" else athlete_b.id

    try:
        validate_weight_difference(float(weight_a), float(weight_b))

        preview = calculate_match_points(
            athlete_a_id=athlete_a.id,
            athlete_b_id=athlete_b.id,
            winner_id=winner_id,
            win_type=win_type,
            weight_a=float(weight_a),
            weight_b=float(weight_b),
            raw_score_a=float(raw_score_a),
            raw_score_b=float(raw_score_b),
            athlete_a_sex=athlete_a.sex,
            athlete_b_sex=athlete_b.sex,
            athlete_a_birth_date=athlete_a.birth_date,
            athlete_b_birth_date=athlete_b.birth_date,
            event_date=selected_event.event_date,
        )

        editing_match_id = st.session_state.get(MATCH_EDIT_ID_KEY)

        if editing_match_id is None:
            match = create_match(
                event_id=selected_event.id,
                athlete_a_id=athlete_a.id,
                athlete_b_id=athlete_b.id,
                style=athlete_a.style,
                weight_a=float(weight_a),
                weight_b=float(weight_b),
                level_a=int(athlete_a.level),
                level_b=int(athlete_b.level),
                raw_score_a=float(raw_score_a),
                raw_score_b=float(raw_score_b),
                athlete_a_sex=athlete_a.sex,
                athlete_b_sex=athlete_b.sex,
                athlete_a_birth_date=athlete_a.birth_date,
                athlete_b_birth_date=athlete_b.birth_date,
                event_date=selected_event.event_date,
                winner_id=winner_id,
                win_type=win_type,
                token_spender_id=token_spender_id,
                notes=notes,
            )
            action_label = "salvato"
        else:
            match = replace_match(
                match_id=editing_match_id,
                event_id=selected_event.id,
                athlete_a_id=athlete_a.id,
                athlete_b_id=athlete_b.id,
                style=athlete_a.style,
                weight_a=float(weight_a),
                weight_b=float(weight_b),
                level_a=int(athlete_a.level),
                level_b=int(athlete_b.level),
                raw_score_a=float(raw_score_a),
                raw_score_b=float(raw_score_b),
                athlete_a_sex=athlete_a.sex,
                athlete_b_sex=athlete_b.sex,
                athlete_a_birth_date=athlete_a.birth_date,
                athlete_b_birth_date=athlete_b.birth_date,
                event_date=selected_event.event_date,
                winner_id=winner_id,
                win_type=win_type,
                token_spender_id=token_spender_id,
                notes=notes,
            )
            action_label = "corretto"

        recompute_ratings()

        st.session_state[MATCH_DELETE_CANDIDATE_ID_KEY] = None
        st.session_state[MATCH_DELETE_CANDIDATE_IDS_KEY] = []
        st.session_state[MATCH_IGNORE_TABLE_SYNC_KEY] = True

        if editing_match_id is not None:
            st.session_state[MATCH_TABLE_SELECTED_ID_KEY] = match.id

        set_flash(
            MATCH_SAVE_FLASH_KEY,
            "success",
            (
                f"Incontro {action_label}. "
                f"Punti classifica A = {preview['total_points_a']:.2f}, "
                f"Punti classifica B = {preview['total_points_b']:.2f}. "
                f"Dettaglio: A(base={preview['result_base_a']}, bonus={preview['performance_bonus_a']}), "
                f"B(base={preview['result_base_b']}, bonus={preview['performance_bonus_b']})."
            ),
        )
        st.rerun()
    except ValueError as exc:
        st.error(str(exc))


def _render_manage_section(
    *,
    matches: list[Match],
    selected_match_ids: list[int],
    selected_match: Optional[Match],
    athletes_map,
    events_map,
) -> None:
    st.subheader("Correggi o elimina incontro")

    if not matches:
        st.info("Nessun incontro presente.")
    else:
        if not selected_match_ids:
            st.info(
                "Seleziona una o più righe dalla tabella qui sopra. "
                "Il form caricherà automaticamente l'ultima selezionata."
            )
        else:
            if selected_match is not None:
                st.caption(match_label(selected_match, athletes_map, events_map))

            delete_label = "Richiedi eliminazione"
            if len(selected_match_ids) > 1:
                delete_label = f"Richiedi eliminazione ({len(selected_match_ids)} incontri)"

            if st.button(delete_label, use_container_width=True):
                st.session_state[MATCH_DELETE_CANDIDATE_IDS_KEY] = selected_match_ids
                st.rerun()

    pending_delete_ids = st.session_state.get(MATCH_DELETE_CANDIDATE_IDS_KEY, [])

    if pending_delete_ids:
        matches_by_id = {match.id: match for match in matches}
        pending_matches = [
            matches_by_id[match_id]
            for match_id in pending_delete_ids
            if match_id in matches_by_id
        ]

        if not pending_matches:
            st.session_state[MATCH_DELETE_CANDIDATE_IDS_KEY] = []
        else:
            if len(pending_matches) == 1:
                st.warning("Stai per eliminare un incontro. L'operazione non può essere annullata.")
            else:
                st.warning(
                    f"Stai per eliminare {len(pending_matches)} incontri. "
                    "L'operazione non può essere annullata."
                )

            for pending_match in pending_matches[:10]:
                st.caption(match_label(pending_match, athletes_map, events_map))

            if len(pending_matches) > 10:
                st.caption(f"... e altri {len(pending_matches) - 10} incontri selezionati.")

            col_confirm, col_cancel = st.columns(2)

            with col_confirm:
                if st.button("Conferma eliminazione", type="primary", use_container_width=True):
                    try:
                        editing_match_id = st.session_state.get(MATCH_EDIT_ID_KEY)

                        for pending_match_id in pending_delete_ids:
                            delete_match(pending_match_id)

                        recompute_ratings()

                        if editing_match_id in pending_delete_ids:
                            schedule_match_form_reset()

                        st.session_state[MATCH_DELETE_CANDIDATE_ID_KEY] = None
                        st.session_state[MATCH_DELETE_CANDIDATE_IDS_KEY] = []
                        st.session_state[MATCH_IGNORE_TABLE_SYNC_KEY] = True
                        st.session_state[MATCH_TABLE_SELECTED_ID_KEY] = None

                        if len(pending_delete_ids) == 1:
                            set_flash(
                                MATCH_DELETE_FLASH_KEY,
                                "success",
                                f"Incontro #{pending_delete_ids[0]} eliminato.",
                            )
                        else:
                            set_flash(
                                MATCH_DELETE_FLASH_KEY,
                                "success",
                                f"{len(pending_delete_ids)} incontri eliminati correttamente.",
                            )

                        st.rerun()
                    except ValueError as exc:
                        st.error(str(exc))

            with col_cancel:
                if st.button("Annulla eliminazione", use_container_width=True):
                    st.session_state[MATCH_DELETE_CANDIDATE_ID_KEY] = None
                    st.session_state[MATCH_DELETE_CANDIDATE_IDS_KEY] = []
                    st.rerun()

    show_flash(MATCH_DELETE_FLASH_KEY)


def render_matches_page() -> None:
    bootstrap_database_from_state()

    st.title("Incontri")

    events = list_events()
    all_athletes = list_athletes(include_inactive=True)
    active_athletes = [athlete for athlete in all_athletes if athlete.active]

    if not events:
        st.warning("Prima devi creare almeno un evento.")
        st.stop()

    if len(active_athletes) < 2:
        st.warning("Servono almeno due atleti attivi.")
        st.stop()

    events_map = {event.id: event for event in events}
    athletes_map = {athlete.id: athlete for athlete in all_athletes}

    event_ids = [event.id for event in events]
    athlete_ids = [athlete.id for athlete in all_athletes]

    if st.session_state.pop(MATCH_FORM_RESET_PENDING_KEY, False):
        reset_match_form(event_ids, athlete_ids, athletes_map)

    ensure_match_form_state(event_ids, athlete_ids, athletes_map)

    matches = list_matches()
    match_points_by_id = build_match_points_map()
    matches_df = _build_matches_dataframe(
        matches=matches,
        athletes_map=athletes_map,
        events_map=events_map,
        match_points_by_id=match_points_by_id,
    )

    form_container = st.container()
    save_flash_container = st.container()
    list_container = st.container()
    manage_container = st.container()

    selected_match_ids: list[int] = []
    selected_match: Optional[Match] = None

    with list_container:
        selected_match_ids, selected_match = _render_matches_list(
            matches=matches,
            matches_df=matches_df,
            athletes_map=athletes_map,
            events_map=events_map,
        )

    with form_container:
        _render_match_form(
            events_map=events_map,
            athletes_map=athletes_map,
            event_ids=event_ids,
            athlete_ids=athlete_ids,
        )

    with save_flash_container:
        show_flash(MATCH_SAVE_FLASH_KEY)

    with manage_container:
        _render_manage_section(
            matches=matches,
            selected_match_ids=selected_match_ids,
            selected_match=selected_match,
            athletes_map=athletes_map,
            events_map=events_map,
        )
