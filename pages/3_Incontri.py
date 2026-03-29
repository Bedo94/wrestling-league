from typing import Optional

import pandas as pd
import streamlit as st

from src.ratings import recompute_ratings
from src.athletes import get_tokens_remaining_for_season, list_athletes
from src.events import list_events
from src.levels import get_level_label
from src.matches import create_match, delete_match, list_matches, replace_match
from src.reference_data import WIN_TYPE_OPTIONS
from src.scoring import calculate_match_points, validate_weight_difference
from src.db_runtime import bootstrap_database_from_state
from src.models import Match
from src.settings import TOKEN_SETTINGS

bootstrap_database_from_state()
st.title("Incontri")

MATCH_FLASH_KEY = "matches_flash"
MATCH_EDIT_ID_KEY = "match_editing_id"
MATCH_DELETE_CANDIDATE_ID_KEY = "match_delete_candidate_id"
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
MATCH_IS_TOKEN_MATCH_KEY = "match_is_token_match"
MATCH_TOKEN_SPENDER_CHOICE_KEY = "match_token_spender_choice"


def athlete_label(athlete) -> str:
    full_name = f"{athlete.first_name} {athlete.last_name or ''}".strip()
    inactive_suffix = " (inattivo)" if not athlete.active else ""
    return (
        f"{full_name}{inactive_suffix} — {athlete.style} — "
        f"{athlete.default_weight:.1f} kg — {get_level_label(athlete.level)}"
    )


def event_label(event) -> str:
    return f"{event.name} — {event.event_date} — Stagione {event.season}"


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


def set_flash(kind: str, message: str) -> None:
    st.session_state[MATCH_FLASH_KEY] = {"kind": kind, "message": message}


def show_flash() -> None:
    flash = st.session_state.pop(MATCH_FLASH_KEY, None)
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
    st.session_state[MATCH_WEIGHT_A_KEY] = float(athletes_map[default_athlete_a_id].default_weight)
    st.session_state[MATCH_WEIGHT_B_KEY] = float(athletes_map[default_athlete_b_id].default_weight)
    st.session_state[MATCH_RAW_SCORE_A_KEY] = 0.0
    st.session_state[MATCH_RAW_SCORE_B_KEY] = 0.0
    st.session_state[MATCH_WINNER_CHOICE_KEY] = "Atleta A"
    st.session_state[MATCH_WIN_TYPE_KEY] = WIN_TYPE_OPTIONS[0]
    st.session_state[MATCH_NOTES_KEY] = ""
    st.session_state[MATCH_IS_TOKEN_MATCH_KEY] = False
    st.session_state[MATCH_TOKEN_SPENDER_CHOICE_KEY] = "Atleta A"


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

    if MATCH_IS_TOKEN_MATCH_KEY not in st.session_state:
        st.session_state[MATCH_IS_TOKEN_MATCH_KEY] = False

    if MATCH_TOKEN_SPENDER_CHOICE_KEY not in st.session_state:
        st.session_state[MATCH_TOKEN_SPENDER_CHOICE_KEY] = "Atleta A"

    if MATCH_EDIT_ID_KEY not in st.session_state:
        st.session_state[MATCH_EDIT_ID_KEY] = None

    if MATCH_DELETE_CANDIDATE_ID_KEY not in st.session_state:
        st.session_state[MATCH_DELETE_CANDIDATE_ID_KEY] = None

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
    st.session_state[MATCH_IS_TOKEN_MATCH_KEY] = bool(match.is_token_match)

    if match.token_spender_id == match.athlete_b_id:
        st.session_state[MATCH_TOKEN_SPENDER_CHOICE_KEY] = "Atleta B"
    else:
        st.session_state[MATCH_TOKEN_SPENDER_CHOICE_KEY] = "Atleta A"


def get_selected_match_from_table(df: pd.DataFrame, matches: list[Match]) -> Optional[Match]:
    table_state = st.session_state.get("matches_table")
    selected_rows: list[int] = []

    try:
        if table_state is not None:
            selected_rows = table_state["selection"]["rows"]
    except Exception:
        selected_rows = []

    if not selected_rows or df.empty:
        return None

    selected_row_idx = selected_rows[-1]

    if selected_row_idx < 0 or selected_row_idx >= len(df):
        return None

    selected_match_id = int(df.iloc[selected_row_idx]["ID"])
    return next((match for match in matches if match.id == selected_match_id), None)


show_flash()

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
events_map = {event.id: event for event in list_events()}
athletes_map = {athlete.id: athlete for athlete in list_athletes(include_inactive=True)}

rows = []
for match in matches:
    athlete_a = athletes_map.get(match.athlete_a_id)
    athlete_b = athletes_map.get(match.athlete_b_id)
    winner = athletes_map.get(match.winner_id) if match.winner_id else None
    token_spender = athletes_map.get(match.token_spender_id) if match.token_spender_id else None
    event = events_map.get(match.event_id)

    rows.append(
        {
            "ID": match.id,
            "Evento": format_event_name(event, match.event_id),
            "Data": format_event_date(event),
            "Stagione": event.season if event is not None else "",
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
            "Token": "Sì" if match.is_token_match else "",
            "Spende token": format_athlete_name(token_spender),
            "Punti classifica A": match.points_a if match.points_a is not None else "N.D.",
            "Punti classifica B": match.points_b if match.points_b is not None else "N.D.",
            "Note": match.notes or "",
        }
    )

matches_df = pd.DataFrame(rows)

selected_match = None
if not matches_df.empty:
    selected_match = get_selected_match_from_table(matches_df, matches)

    if st.session_state.get(MATCH_IGNORE_TABLE_SYNC_KEY):
        st.session_state[MATCH_IGNORE_TABLE_SYNC_KEY] = False
    elif selected_match is not None:
        last_loaded_match_id = st.session_state.get(MATCH_TABLE_SELECTED_ID_KEY)
        if selected_match.id != last_loaded_match_id:
            load_match_into_form(selected_match)
            st.session_state[MATCH_TABLE_SELECTED_ID_KEY] = selected_match.id

st.subheader("Aggiungi incontro")

selected_event_id = st.selectbox(
    "Evento *",
    options=event_ids,
    format_func=lambda event_id: event_label(events_map[event_id]),
    key=MATCH_EVENT_ID_KEY,
)

selected_athlete_a_id = st.selectbox(
    "Atleta A *",
    options=athlete_ids,
    format_func=lambda athlete_id: athlete_label(athletes_map[athlete_id]),
    key=MATCH_ATHLETE_A_ID_KEY,
    on_change=sync_weight_a_from_selected_athlete,
    args=(athletes_map,),
)

selected_athlete_b_id = st.selectbox(
    "Atleta B *",
    options=athlete_ids,
    format_func=lambda athlete_id: athlete_label(athletes_map[athlete_id]),
    key=MATCH_ATHLETE_B_ID_KEY,
    on_change=sync_weight_b_from_selected_athlete,
    args=(athletes_map,),
)

selected_event = events_map[selected_event_id]
athlete_a = athletes_map[selected_athlete_a_id]
athlete_b = athletes_map[selected_athlete_b_id]

col1, col2 = st.columns(2)

with col1:
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

with col2:
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

st.caption(f"Stile atleta A: {athlete_a.style}")
st.caption(f"Stile atleta B: {athlete_b.style}")
st.caption(f"Stagione evento: {selected_event.season}")

winner_choice = st.radio(
    "Vincitore *",
    options=["Atleta A", "Atleta B"],
    horizontal=True,
    key=MATCH_WINNER_CHOICE_KEY,
)

win_type = st.selectbox(
    "Modo di vittoria *",
    options=WIN_TYPE_OPTIONS,
    key=MATCH_WIN_TYPE_KEY,
)

is_token_match = st.checkbox(
    "Match a token",
    key=MATCH_IS_TOKEN_MATCH_KEY,
)

token_spender_id: Optional[int] = None
token_cost = int(TOKEN_SETTINGS["default_token_cost"])

if is_token_match:
    token_spender_choice = st.radio(
        "Chi spende il token?",
        options=["Atleta A", "Atleta B"],
        horizontal=True,
        key=MATCH_TOKEN_SPENDER_CHOICE_KEY,
    )

    token_spender = athlete_a if token_spender_choice == "Atleta A" else athlete_b
    editing_match_id = st.session_state.get(MATCH_EDIT_ID_KEY)

    remaining_tokens = get_tokens_remaining_for_season(
        athlete_id=token_spender.id,
        season=selected_event.season,
        exclude_match_id=editing_match_id,
    )

    st.caption(
        f"{format_athlete_name(token_spender)} ha {remaining_tokens} token disponibili "
        f"nella stagione {selected_event.season}."
    )

    token_spender_id = token_spender.id

notes = st.text_area("Note", key=MATCH_NOTES_KEY)

submitted = st.button("Salva", type="primary", use_container_width=True)

if submitted:
    if athlete_a.id == athlete_b.id:
        st.error("Atleta A e Atleta B devono essere diversi.")
    elif athlete_a.style != athlete_b.style:
        st.error("Gli atleti devono avere lo stesso stile di lotta.")
    else:
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
                    is_token_match=bool(is_token_match),
                    token_spender_id=token_spender_id,
                    token_cost=token_cost,
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
                    is_token_match=bool(is_token_match),
                    token_spender_id=token_spender_id,
                    token_cost=token_cost,
                    notes=notes,
                )
                action_label = "corretto"

            recompute_ratings()
            schedule_match_form_reset()
            st.session_state[MATCH_DELETE_CANDIDATE_ID_KEY] = None
            st.session_state[MATCH_IGNORE_TABLE_SYNC_KEY] = True
            st.session_state[MATCH_TABLE_SELECTED_ID_KEY] = match.id

            set_flash(
                "success",
                (
                    f"Incontro {action_label}. "
                    f"Punti classifica A = {match.points_a:.2f}, "
                    f"Punti classifica B = {match.points_b:.2f}. "
                    f"Dettaglio: A(base={preview['result_base_a']}, bonus={preview['performance_bonus_a']}), "
                    f"B(base={preview['result_base_b']}, bonus={preview['performance_bonus_b']})."
                ),
            )
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))

st.divider()

st.subheader("Lista incontri")

if matches_df.empty:
    st.info("Nessun incontro presente.")
else:
    st.dataframe(
        matches_df,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="multi-row",
        key="matches_table",
    )

st.subheader("Correggi o elimina incontro")

if not matches:
    st.info("Nessun incontro presente.")
else:
    if selected_match is None:
        st.info("Seleziona una o più righe dalla tabella qui sopra. Il form caricherà automaticamente l'ultima selezionata.")
    else:
        st.caption(match_label(selected_match, athletes_map, events_map))

        if st.button("Richiedi eliminazione", use_container_width=True):
            st.session_state[MATCH_DELETE_CANDIDATE_ID_KEY] = selected_match.id
            st.rerun()

pending_delete_id = st.session_state.get(MATCH_DELETE_CANDIDATE_ID_KEY)

if pending_delete_id is not None:
    pending_match = next((match for match in matches if match.id == pending_delete_id), None)

    if pending_match is None:
        st.session_state[MATCH_DELETE_CANDIDATE_ID_KEY] = None
    else:
        st.warning("Stai per eliminare un incontro. L'operazione non può essere annullata.")
        st.caption(match_label(pending_match, athletes_map, events_map))

        col_confirm, col_cancel = st.columns(2)

        with col_confirm:
            if st.button("Conferma eliminazione", type="primary", use_container_width=True):
                try:
                    delete_match(pending_delete_id)
                    recompute_ratings()

                    if st.session_state.get(MATCH_EDIT_ID_KEY) == pending_delete_id:
                        schedule_match_form_reset()

                    st.session_state[MATCH_DELETE_CANDIDATE_ID_KEY] = None
                    st.session_state[MATCH_IGNORE_TABLE_SYNC_KEY] = True
                    st.session_state[MATCH_TABLE_SELECTED_ID_KEY] = None
                    set_flash("success", f"Incontro #{pending_delete_id} eliminato.")
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))

        with col_cancel:
            if st.button("Annulla eliminazione", use_container_width=True):
                st.session_state[MATCH_DELETE_CANDIDATE_ID_KEY] = None
                st.rerun()