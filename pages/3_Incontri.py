import pandas as pd
import streamlit as st

from src.ratings import recompute_ratings
from src.athletes import list_athletes
from src.events import list_events
from src.levels import get_level_label
from src.matches import create_match, delete_match, list_matches, replace_match
from src.reference_data import WIN_TYPE_OPTIONS
from src.scoring import calculate_match_points, validate_weight_difference
from src.db_runtime import bootstrap_database_from_state

bootstrap_database_from_state()
st.title("Incontri")

MATCH_FLASH_KEY = "matches_flash"
MATCH_EDIT_ID_KEY = "match_editing_id"
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


def athlete_label(athlete) -> str:
    full_name = f"{athlete.first_name} {athlete.last_name or ''}".strip()
    inactive_suffix = " (inattivo)" if not athlete.active else ""
    return (
        f"{full_name}{inactive_suffix} — {athlete.style} — "
        f"{athlete.default_weight:.1f} kg — {get_level_label(athlete.level)}"
    )


def event_label(event) -> str:
    return f"{event.name} — {event.event_date}"


def match_label(match, athletes_map, events_map) -> str:
    athlete_a = athletes_map.get(match.athlete_a_id)
    athlete_b = athletes_map.get(match.athlete_b_id)
    event = events_map.get(match.event_id)

    athlete_a_name = (
        f"{athlete_a.first_name} {athlete_a.last_name or ''}".strip()
        if athlete_a
        else f"ID {match.athlete_a_id}"
    )
    athlete_b_name = (
        f"{athlete_b.first_name} {athlete_b.last_name or ''}".strip()
        if athlete_b
        else f"ID {match.athlete_b_id}"
    )
    event_name = event.name if event else f"ID {match.event_id}"
    event_date = event.event_date if event else ""

    return f"#{match.id} — {event_name} {event_date} — {athlete_a_name} vs {athlete_b_name}"


def set_flash(kind: str, message: str) -> None:
    st.session_state[MATCH_FLASH_KEY] = {"kind": kind, "message": message}


def show_flash() -> None:
    flash = st.session_state.pop(MATCH_FLASH_KEY, None)
    if flash:
        getattr(st, flash["kind"], st.info)(flash["message"])


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

    if MATCH_EDIT_ID_KEY not in st.session_state:
        st.session_state[MATCH_EDIT_ID_KEY] = None


def load_match_into_form(match) -> None:
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


show_flash()

events = list_events()
all_athletes = list_athletes(include_inactive=True)
active_athletes = [athlete for athlete in all_athletes if athlete.active]
matches = list_matches()

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

ensure_match_form_state(event_ids, athlete_ids, athletes_map)

st.subheader("Correggi o elimina incontro")

if not matches:
    st.info("Nessun incontro presente.")
else:
    match_ids = [match.id for match in matches]

    selected_existing_match_id = st.selectbox(
        "Incontro esistente",
        options=[None] + match_ids,
        format_func=lambda match_id: (
            "Seleziona un incontro"
            if match_id is None
            else match_label(
                next(match for match in matches if match.id == match_id),
                athletes_map,
                events_map,
            )
        ),
        key="selected_existing_match_id",
    )

    col_action_1, col_action_2 = st.columns(2)

    with col_action_1:
        if st.button("Carica nel form", use_container_width=True):
            if selected_existing_match_id is None:
                st.warning("Seleziona prima un incontro.")
            else:
                selected_match = next(
                    (match for match in matches if match.id == selected_existing_match_id),
                    None,
                )
                if selected_match is None:
                    st.error("Incontro non trovato.")
                else:
                    load_match_into_form(selected_match)
                    st.rerun()

    with col_action_2:
        if st.button("Elimina incontro", use_container_width=True):
            if selected_existing_match_id is None:
                st.warning("Seleziona prima un incontro.")
            else:
                try:
                    delete_match(selected_existing_match_id)
                    recompute_ratings()

                    if st.session_state.get(MATCH_EDIT_ID_KEY) == selected_existing_match_id:
                        reset_match_form(event_ids, athlete_ids, athletes_map)

                    set_flash("success", f"Incontro #{selected_existing_match_id} eliminato.")
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))

st.divider()

editing_match_id = st.session_state.get(MATCH_EDIT_ID_KEY)

if editing_match_id is not None:
    st.info(f"Stai correggendo l'incontro #{editing_match_id}.")
    if st.button("Annulla correzione"):
        reset_match_form(event_ids, athlete_ids, athletes_map)
        st.rerun()

st.subheader("Aggiungi incontro")

with st.form("match_form"):
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
    )

    selected_athlete_b_id = st.selectbox(
        "Atleta B *",
        options=athlete_ids,
        format_func=lambda athlete_id: athlete_label(athletes_map[athlete_id]),
        key=MATCH_ATHLETE_B_ID_KEY,
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

    notes = st.text_area("Note", key=MATCH_NOTES_KEY)

    submitted = st.form_submit_button(
        "Salva correzione" if editing_match_id is not None else "Salva incontro"
    )

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
                    notes=notes,
                )
                action_label = "corretto"

            recompute_ratings()
            reset_match_form(event_ids, athlete_ids, athletes_map)

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

matches = list_matches()
athletes_map = {a.id: a for a in list_athletes(include_inactive=True)}
events_map = {e.id: e for e in list_events()}

if not matches:
    st.info("Nessun incontro presente.")
else:
    rows = []
    for match in matches:
        athlete_a = athletes_map.get(match.athlete_a_id)
        athlete_b = athletes_map.get(match.athlete_b_id)
        winner = athletes_map.get(match.winner_id) if match.winner_id else None
        event = events_map.get(match.event_id)

        rows.append(
            {
                "ID": match.id,
                "Evento": event.name if event else f"ID {match.event_id}",
                "Data": event.event_date if event else "",
                "Stile": match.style,
                "Atleta A": f"{athlete_a.first_name} {athlete_a.last_name or ''}".strip() if athlete_a else "",
                "Peso A": match.weight_a,
                "Livello A": get_level_label(match.level_a),
                "Punti A": match.raw_score_a,
                "Atleta B": f"{athlete_b.first_name} {athlete_b.last_name or ''}".strip() if athlete_b else "",
                "Peso B": match.weight_b,
                "Livello B": get_level_label(match.level_b),
                "Punti B": match.raw_score_b,
                "Vincitore": f"{winner.first_name} {winner.last_name or ''}".strip() if winner else "",
                "Modo vittoria": match.win_type,
                "Punti classifica A": match.points_a if match.points_a is not None else "N.D.",
                "Punti classifica B": match.points_b if match.points_b is not None else "N.D.",
                "Note": match.notes or "",
            }
        )

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)