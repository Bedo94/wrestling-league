import pandas as pd
import streamlit as st

from src.events import create_event, list_events
from src.db_runtime import bootstrap_database_from_state

bootstrap_database_from_state()
st.title("Eventi / Giornate")

st.markdown(
    """
Questa pagina serve per registrare le giornate della league o eventuali eventi speciali.

Per ora ogni evento ha:
- nome
- data
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
            event = create_event(
                name=name,
                event_date=event_date,
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
                "Note": e.notes or "",
            }
            for e in events
        ]
    )
    st.dataframe(df, use_container_width=True, hide_index=True)