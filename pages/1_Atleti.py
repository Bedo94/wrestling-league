from datetime import date
from typing import Any

import pandas as pd
import streamlit as st

from src.athletes import (
    create_athlete,
    list_athletes,
    list_teams,
    update_athletes_from_rows,
)
from src.db_runtime import bootstrap_database_from_state
from src.level_evaluation_ui import render_level_assistant
from src.levels import get_level_label, get_level_labels, get_level_from_label
from src.ratings import recompute_ratings
from src.reference_data import SEX_OPTIONS, STYLE_OPTIONS
from src.settings import TOKEN_SETTINGS

bootstrap_database_from_state()

st.title("Atleti")

st.markdown(
    """
Il campo **livello** rappresenta una stima iniziale manuale del livello tecnico.

Il campo **rating** rappresenta invece una valutazione dinamica, calcolata in base
ai risultati ottenuti.

Il campo **token budget** rappresenta quanti token l'atleta può spendere per stagione.
"""
)

level_labels = get_level_labels()

if "athlete_form_level_label" not in st.session_state:
    st.session_state["athlete_form_level_label"] = level_labels[0]

if st.session_state.pop("reset_athlete_form_level_label", False):
    st.session_state["athlete_form_level_label"] = level_labels[0]

st.subheader("Aggiungi atleta")

with st.expander("Assistente livello consigliato (opzionale)", expanded=False):
    render_level_assistant(
        state_prefix="athlete_level_assistant",
        show_apply_button=True,
        apply_target_session_key="athlete_form_level_label",
        apply_button_label="Usa livello consigliato nel form",
    )

team_options = list_teams()

with st.form("athlete_form", clear_on_submit=True):
    first_name = st.text_input("Nome *")
    last_name = st.text_input("Cognome")
    nickname = st.text_input("Nickname")
    team = st.selectbox(
        "Team / Corso / Università",
        options=team_options,
        index=None,
        placeholder="Seleziona o scrivi un team",
        accept_new_options=True,
    )

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
        options=level_labels,
        key="athlete_form_level_label",
    )

    col4, col5 = st.columns(2)

    with col4:
        default_weight = st.number_input(
            "Peso di riferimento (kg) *",
            min_value=1.0,
            max_value=300.0,
            value=70.0,
            step=0.5,
        )

    with col5:
        token_budget = st.number_input(
            "Token budget *",
            min_value=0,
            max_value=100,
            value=int(TOKEN_SETTINGS["default_token_budget_per_season"]),
            step=1,
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
                token_budget=int(token_budget),
                rating=None,
            )
            recompute_ratings()

            st.session_state["reset_athlete_form_level_label"] = True

            st.success(
                f"Atleta salvato: {athlete.first_name} "
                f"(id={athlete.id}, livello={get_level_label(athlete.level)})"
            )
            st.rerun()

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
                "Cognome": a.last_name or "",
                "Nickname": a.nickname or "",
                "Team": a.team or "",
                "Data nascita": a.birth_date,
                "Sesso": a.sex,
                "Stile": a.style,
                "Livello": get_level_label(a.level),
                "Peso": float(a.default_weight),
                "Token budget": int(a.token_budget),
                "Rating": a.rating if a.rating is not None else "N.D.",
                "Attivo": bool(a.active),
            }
            for a in athletes
        ]
    )

    edited_df = st.data_editor(
        df,
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        disabled=["ID", "Rating"],
        column_config={
            "Nome": st.column_config.TextColumn("Nome", required=True),
            "Cognome": st.column_config.TextColumn("Cognome"),
            "Nickname": st.column_config.TextColumn("Nickname"),
            "Team": st.column_config.TextColumn("Team"),
            "Data nascita": st.column_config.DateColumn(
                "Data nascita",
                format="DD/MM/YYYY",
                min_value=date(1950, 1, 1),
                max_value=date.today(),
                required=True,
            ),
            "Sesso": st.column_config.SelectboxColumn(
                "Sesso",
                options=SEX_OPTIONS,
                required=True,
            ),
            "Stile": st.column_config.SelectboxColumn(
                "Stile",
                options=STYLE_OPTIONS,
                required=True,
            ),
            "Livello": st.column_config.SelectboxColumn(
                "Livello",
                options=get_level_labels(),
                required=True,
            ),
            "Peso": st.column_config.NumberColumn(
                "Peso",
                min_value=1.0,
                max_value=300.0,
                step=0.5,
                required=True,
            ),
            "Token budget": st.column_config.NumberColumn(
                "Token budget",
                min_value=0,
                max_value=100,
                step=1,
                required=True,
            ),
            "Attivo": st.column_config.CheckboxColumn("Attivo"),
        },
        key="athletes_editor",
    )

    if st.button("Salva modifiche", type="primary"):
        try:
            rows: list[dict[str, Any]] = [
                {str(key): value for key, value in row.items()}
                for row in edited_df.to_dict(orient="records")
            ]

            updated_count = update_athletes_from_rows(rows)
            recompute_ratings()
            st.success(f"Modifiche salvate correttamente ({updated_count} atleti aggiornati).")
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))
        except Exception as exc:
            st.error(f"Errore durante il salvataggio: {exc}")