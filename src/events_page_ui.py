from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd
import streamlit as st

from src.db_runtime import bootstrap_database_from_state
from src.events import (
    create_event,
    delete_events_if_unused,
    list_events,
    update_events_from_rows,
)
from src.table_component import render_table_component
from src.table_specs import EVENTS_TABLE_SPEC

EVENTS_UPDATE_SUCCESS_KEY = "events_update_success_message"
EVENTS_CREATE_SUCCESS_KEY = "events_create_success_message"
EVENTS_DELETE_CANDIDATE_IDS_KEY = "events_delete_candidate_ids"


def _build_events_dataframe() -> pd.DataFrame:
    events = list_events()

    return pd.DataFrame(
        [
            {
                "ID": event.id,
                "Nome": event.name,
                "Data": event.event_date,
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
        event = create_event(
            name=name,
            event_date=event_date,
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


@st.fragment
def _render_events_table(df: pd.DataFrame) -> None:
    update_success_message = st.session_state.pop(
        EVENTS_UPDATE_SUCCESS_KEY,
        None,
    )
    if update_success_message:
        st.success(update_success_message)

    table_result = render_table_component(
        df=df,
        spec=EVENTS_TABLE_SPEC,
        renderer="aggrid",
        key="events_table",
    )

    selected_event_ids: list[int] = []
    if (
        not table_result.selected_rows_df.empty
        and "ID" in table_result.selected_rows_df.columns
    ):
        selected_event_ids = [
            int(event_id) for event_id in table_result.selected_rows_df["ID"].tolist()
        ]

    action_col1, action_col2 = st.columns(2)

    if action_col1.button(
        "Salva modifiche eventi",
        type="primary",
        use_container_width=True,
    ):
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

    if action_col2.button(
        "Richiedi eliminazione selezionati",
        use_container_width=True,
        disabled=not selected_event_ids,
    ):
        st.session_state[EVENTS_DELETE_CANDIDATE_IDS_KEY] = selected_event_ids
        st.rerun()

    events = list_events()
    events_by_id = {event.id: event for event in events}
    pending_delete_ids = st.session_state.get(EVENTS_DELETE_CANDIDATE_IDS_KEY, [])
    pending_events = [
        events_by_id[event_id]
        for event_id in pending_delete_ids
        if event_id in events_by_id
    ]

    if pending_events:
        if len(pending_events) == 1:
            st.warning(
                "Stai per eliminare un evento. L'operazione è consentita solo se non ha incontri associati."
            )
        else:
            st.warning(
                f"Stai per eliminare {len(pending_events)} eventi. "
                "L'operazione è consentita solo se nessuno ha incontri associati."
            )

        for event in pending_events[:10]:
            st.caption(f"{event.name} - {event.event_date}")

        if len(pending_events) > 10:
            st.caption(f"... e altri {len(pending_events) - 10} eventi selezionati.")

        confirm_col, cancel_col = st.columns(2)

        if confirm_col.button(
            "Conferma eliminazione eventi",
            type="primary",
            use_container_width=True,
        ):
            try:
                deleted_names = delete_events_if_unused(pending_delete_ids)
                st.session_state[EVENTS_DELETE_CANDIDATE_IDS_KEY] = []
                if len(deleted_names) == 1:
                    st.session_state[EVENTS_UPDATE_SUCCESS_KEY] = (
                        f"Evento eliminato: {deleted_names[0]}."
                    )
                else:
                    st.session_state[EVENTS_UPDATE_SUCCESS_KEY] = (
                        f"Eventi eliminati correttamente ({len(deleted_names)})."
                    )
                st.rerun()
            except ValueError as exc:
                st.session_state[EVENTS_DELETE_CANDIDATE_IDS_KEY] = []
                st.error(str(exc))

        if cancel_col.button(
            "Annulla eliminazione eventi",
            use_container_width=True,
        ):
            st.session_state[EVENTS_DELETE_CANDIDATE_IDS_KEY] = []
            st.rerun()


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
