from datetime import date
from typing import Any

import pandas as pd
import streamlit as st

from src.db_runtime import bootstrap_database_from_state
from src.events import (
    create_event,
    list_events,
    update_events_from_rows,
    derive_season_from_date,
)

bootstrap_database_from_state()

st.title("Eventi / Giornate")
st.markdown(
    """
    Questa pagina serve per registrare le giornate della league o eventuali eventi speciali.

    Per ora ogni evento ha:
    - nome
    - data
    - stagione (dedotta automaticamente dall'anno)
    - note
    """
)

st.subheader("Aggiungi evento")

with st.form("event_form", clear_on_submit=True):
    name = st.text_input("Nome evento *", placeholder="Es. League Day 1")
    event_date = st.date_input("Data *")
    notes = st.text_area("Note", placeholder="Informazioni aggiuntive, luogo, ecc.")
    submitted = st.form_submit_button("Salva evento")
    if submitted:
        if not name.strip():
            st.error("Il nome dell'evento è obbligatorio.")
        else:
            # deduci la stagione dall’anno
            season = derive_season_from_date(event_date)
            event = create_event(
                name=name,
                event_date=event_date,
                season=season,
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
    # Le colonne ID e Stagione non sono modificabili
    edited_df = st.data_editor(
        df,
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        disabled=["ID", "Stagione"],
        column_config={
            "Nome": st.column_config.TextColumn("Nome", required=True),
            "Data": st.column_config.DateColumn(
                "Data",
                format="DD/MM/YYYY",
                min_value=date(2000, 1, 1),
                max_value=date(2100, 12, 31),
                required=True,
            ),
            "Stagione": st.column_config.TextColumn("Stagione", disabled=True),
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