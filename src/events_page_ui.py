from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd
import streamlit as st

from src.db_runtime import bootstrap_database_from_state
from src.events import (
    create_event,
    derive_season_from_date,
    list_events,
    update_events_from_rows,
)
from src.table_component import render_table_component
from src.table_specs import EVENTS_TABLE_SPEC

EVENTS_UPDATE_SUCCESS_KEY = "events_update_success_message"
EVENTS_CREATE_SUCCESS_KEY = "events_create_success_message"


def _build_events_dataframe() -> pd.DataFrame:
    events = list_events()

    return pd.DataFrame(
        [
            {
                "ID": event.id,
                "Nome": event.name,
                "Data": event.event_date,
                "Stagione": event.season,
                "Note": event.notes or "",
            }
            for event in events
        ]
    )


def _show_flash_messages() -> None:
    create_success_message = st.session_state.pop(
        EVENTS_CREATE_SUCCESS_KEY,
        None,
    )
    if create_success_message:
        st.success(create_success_message)

    update_success_message = st.session_state.pop(
        EVENTS_UPDATE_SUCCESS_KEY,
        None,
    )
    if update_success_message:
        st.success(update_success_message)


def _render_event_creation_form() -> None:
    st.subheader("Aggiungi evento")

    with st.form("event_form", clear_on_submit=True):
        name = st.text_input("Nome evento *", placeholder="Es. League Day 1")
        event_date = st.date_input("Data *", value=date.today())
        notes = st.text_area(
            "Note",
            placeholder="Informazioni aggiuntive, luogo, ecc.",
        )
        submitted = st.form_submit_button("Salva evento")

    if not submitted:
        return

    if not name.strip():
        st.error("Il nome dell'evento è obbligatorio.")
        return

    try:
        season = derive_season_from_date(event_date)
        event = create_event(
            name=name,
            event_date=event_date,
            season=season,
            notes=notes,
        )
    except ValueError as exc:
        st.error(str(exc))
        return
    except Exception as exc:
        st.error(f"Errore durante il salvataggio dell'evento: {exc}")
        return

    st.session_state[EVENTS_CREATE_SUCCESS_KEY] = (
        f"Evento salvato: {event.name} (id={event.id})"
    )
    st.rerun()


def _render_events_table(df: pd.DataFrame) -> None:
    table_result = render_table_component(
        df=df,
        spec=EVENTS_TABLE_SPEC,
        renderer="aggrid",
        key="events_table",
    )

    if st.button("Salva modifiche eventi", type="primary"):
        try:
            edited_df = EVENTS_TABLE_SPEC.normalize_from_view(table_result.edited_df)

            rows: list[dict[str, Any]] = [
                {str(key): value for key, value in row.items()}
                for row in edited_df.to_dict(orient="records")
            ]

            updated_count = update_events_from_rows(rows)
            st.session_state[EVENTS_UPDATE_SUCCESS_KEY] = (
                f"Modifiche salvate correttamente ({updated_count} eventi aggiornati)."
            )
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))
        except Exception as exc:
            st.error(f"Errore durante il salvataggio: {exc}")


def render_events_page() -> None:
    bootstrap_database_from_state()

    st.title("Eventi / Giornate")
    st.markdown(
        """
        Questa pagina serve per registrare le giornate della league o eventuali eventi speciali.

        """
    )

    _show_flash_messages()
    _render_event_creation_form()

    st.divider()
    st.subheader("Lista eventi")

    df = _build_events_dataframe()
    if df.empty:
        st.info("Nessun evento presente.")
        return

    _render_events_table(df)