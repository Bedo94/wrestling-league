from datetime import date

import pandas as pd
import streamlit as st

from src.athletes import create_athlete, list_athletes
from src.levels import get_level_label, get_level_labels, get_level_from_label
from src.reference_data import SEX_OPTIONS, STYLE_OPTIONS

st.title("Atleti")

st.markdown(
    """
Il campo **livello** rappresenta una stima iniziale manuale del livello tecnico.

Il campo **rating** rappresenterà invece una valutazione dinamica, calcolata in base
ai risultati ottenuti. Per ora non viene ancora calcolato automaticamente.
"""
)

st.subheader("Aggiungi atleta")

with st.form("athlete_form", clear_on_submit=True):
    first_name = st.text_input("Nome *")
    last_name = st.text_input("Cognome")
    nickname = st.text_input("Nickname")
    team = st.text_input("Team / Corso / Università")

    col1, col2, col3 = st.columns(3)

    with col1:
        birth_date = st.date_input(
            "Data di nascita *",
            value=date(2000, 1, 1),
            min_value=date(1950, 1, 1),
            max_value=date.today(),
            format="DD/MM/YYYY",
        )

    with col2:
        sex = st.selectbox("Sesso *", options=SEX_OPTIONS)

    with col3:
        style = st.selectbox("Stile *", options=STYLE_OPTIONS)

    selected_level_label = st.selectbox(
        "Livello *",
        options=get_level_labels(),
        index=0,
    )

    default_weight = st.number_input(
        "Peso di riferimento (kg) *",
        min_value=1.0,
        max_value=300.0,
        value=70.0,
        step=0.5,
    )

    submitted = st.form_submit_button("Salva atleta")

    if submitted:
        if not first_name.strip():
            st.error("Il nome è obbligatorio.")
        else:
            level = get_level_from_label(selected_level_label)

            athlete = create_athlete(
                first_name=first_name,
                last_name=last_name,
                nickname=nickname,
                team=team,
                birth_date=birth_date,
                sex=sex,
                style=style,
                level=level,
                default_weight=float(default_weight),
                rating=None,
            )
            st.success(
                f"Atleta salvato: {athlete.first_name} "
                f"(id={athlete.id}, livello={get_level_label(athlete.level)})"
            )

st.divider()

st.subheader("Lista atleti")

show_inactive = st.checkbox("Mostra anche inattivi", value=True)

athletes = list_athletes(include_inactive=show_inactive)

if not athletes:
    st.info("Nessun atleta presente.")
else:
    df = pd.DataFrame(
        [
            {
                "ID": a.id,
                "Nome": a.first_name,
                "Cognome": a.last_name,
                "Nickname": a.nickname,
                "Team": a.team,
                "Data nascita": a.birth_date.strftime("%d/%m/%Y"),
                "Sesso": a.sex,
                "Stile": a.style,
                "Livello": get_level_label(a.level),
                "Peso": a.default_weight,
                "Rating": a.rating if a.rating is not None else "N.D.",
                "Attivo": a.active,
            }
            for a in athletes
        ]
    )
    st.dataframe(df, use_container_width=True, hide_index=True)