from datetime import date
from typing import Any

import pandas as pd
import streamlit as st

from src.db_runtime import bootstrap_database_from_state
from src.events import create_event, list_events, list_seasons, update_events_from_rows

bootstrap_database_from_state()

st.title("Eventi / Giornate")

st.markdown(
    """
Questa pagina serve per registrare le giornate della league o eventuali eventi speciali.

Per ora ogni evento ha:
- nome
- data
- stagione
- note
"""
)

st.subheader("Aggiungi evento")

season_options = list_seasons()
default_season = str(date.today().year)
season_select_options = season_options if season_options else [default_season]

with st.form("event_form", clear_on_submit=True):
    name = st.text_input("Nome evento *", placeholder="Es. League Day 1")
    event_date = st.date_input("Data *")
    season = st.selectbox(
        "Stagione *",
        options=season_select_options,
        index=0,
        accept_new_options=True,
        placeholder="Seleziona o scrivi una stagione",
    )
    notes = st.text_area("Note", placeholder="Informazioni aggiuntive, luogo, ecc.")

    submitted = st.form_submit_button("Salva evento")

    if submitted:
        if not name.strip():
            st.error("Il nome dell'evento è obbligatorio.")
        elif not str(season).strip():
            st.error("La stagione è obbligatoria.")
        else:
            event = create_event(
                name=name,
                event_date=event_date,
                season=str(season),
                notes=notes,
            )
            st.success(f"Evento salvato: {event.name} (id={event.id})")

st.divider()

st.subheader("Lista eventi")

events = list_events()

if not events:
    st.info("Nessun evento presente.")
else:
    df = pd.DataFrame(
        [
            {
                "ID": e.id,
                "Nome": e.name,
                "Data": e.event_date,
                "Stagione": e.season,
                "Note": e.notes or "",
            }
            for e in events
        ]
    )

    edited_df = st.data_editor(
        df,
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        disabled=["ID"],
        column_config={
            "Nome": st.column_config.TextColumn("Nome", required=True),
            "Data": st.column_config.DateColumn(
                "Data",
                format="DD/MM/YYYY",
                min_value=date(2000, 1, 1),
                max_value=date(2100, 12, 31),
                required=True,
            ),
            "Stagione": st.column_config.TextColumn("Stagione", required=True),
            "Note": st.column_config.TextColumn("Note"),
        },
        key="events_editor",
    )

    if st.button("Salva modifiche eventi", type="primary"):
        try:
            rows: list[dict[str, Any]] = [
                {str(key): value for key, value in row.items()}
                for row in edited_df.to_dict(orient="records")
            ]

            updated_count = update_events_from_rows(rows)
            st.success(f"Modifiche salvate correttamente ({updated_count} eventi aggiornati).")
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))
        except Exception as exc:
            st.error(f"Errore durante il salvataggio: {exc}")