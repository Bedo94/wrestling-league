import pandas as pd
import streamlit as st
from src.ratings import recompute_ratings

from src.athletes import list_athletes
from src.events import list_events
from src.levels import get_level_label
from src.matches import create_match, list_matches
from src.reference_data import WIN_TYPE_OPTIONS
from src.scoring import calculate_match_points, validate_weight_difference

st.title("Incontri")


def athlete_label(athlete) -> str:
    full_name = f"{athlete.first_name} {athlete.last_name or ''}".strip()
    return (
        f"{full_name} — {athlete.style} — {athlete.default_weight:.1f} kg "
        f"— {get_level_label(athlete.level)}"
    )


def event_label(event) -> str:
    return f"{event.name} — {event.event_date}"


events = list_events()
athletes = list_athletes(include_inactive=False)

if not events:
    st.warning("Prima devi creare almeno un evento.")
    st.stop()

if len(athletes) < 2:
    st.warning("Servono almeno due atleti attivi.")
    st.stop()

st.subheader("Aggiungi incontro")

with st.form("match_form", clear_on_submit=True):
    selected_event = st.selectbox("Evento *", options=events, format_func=event_label)

    athlete_a = st.selectbox(
        "Atleta A *",
        options=athletes,
        format_func=athlete_label,
        key="athlete_a",
    )

    athlete_b = st.selectbox(
        "Atleta B *",
        options=athletes,
        format_func=athlete_label,
        key="athlete_b",
    )

    col1, col2 = st.columns(2)

    with col1:
        weight_a = st.number_input(
            "Peso atleta A (kg) *",
            min_value=1.0,
            max_value=300.0,
            value=float(athlete_a.default_weight),
            step=0.5,
        )
        raw_score_a = st.number_input(
            "Punti atleta A *",
            min_value=0.0,
            max_value=200.0,
            value=0.0,
            step=1.0,
        )

    with col2:
        weight_b = st.number_input(
            "Peso atleta B (kg) *",
            min_value=1.0,
            max_value=300.0,
            value=float(athlete_b.default_weight),
            step=0.5,
        )
        raw_score_b = st.number_input(
            "Punti atleta B *",
            min_value=0.0,
            max_value=200.0,
            value=0.0,
            step=1.0,
        )

    st.caption(f"Stile atleta A: {athlete_a.style}")
    st.caption(f"Stile atleta B: {athlete_b.style}")

    winner_choice = st.radio(
        "Vincitore *",
        options=["Atleta A", "Atleta B"],
        horizontal=True,
    )

    win_type = st.selectbox("Modo di vittoria *", options=WIN_TYPE_OPTIONS)

    notes = st.text_area("Note")

    submitted = st.form_submit_button("Salva incontro")

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

            recompute_ratings()

            st.success(
                f"Incontro salvato. "
                f"Punti classifica A = {match.points_a:.2f}, "
                f"Punti classifica B = {match.points_b:.2f}"
            )

            st.info(
                f"Dettaglio calcolo — "
                f"A: base={preview['result_base_a']}, bonus prestazione={preview['performance_bonus_a']}, "
                f"fattore peso={preview['weight_factor_a']}, fattore speciale={preview['special_factor_a']}. "
                f"B: base={preview['result_base_b']}, bonus prestazione={preview['performance_bonus_b']}, "
                f"fattore peso={preview['weight_factor_b']}, fattore speciale={preview['special_factor_b']}."
            )
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