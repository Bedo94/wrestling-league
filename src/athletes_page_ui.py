from datetime import date
from typing import Any

import pandas as pd
import streamlit as st

from src.athlete_level_service import build_athlete_level_profile_map
from src.athletes import (
    create_athlete,
    delete_athletes_if_unused,
    list_athletes,
    list_teams,
    update_athletes_from_rows,
)
from src.level_evaluation_ui import render_level_assistant
from src.levels import get_level_label, get_level_labels, get_level_from_label
from src.matches import list_matches
from src.ratings import build_current_rating_map, recompute_ratings
from src.reference_data import SEX_OPTIONS, STYLE_OPTIONS
from src.table_component import render_table_component
from src.table_specs import ATHLETES_TABLE_SPEC

ATHLETES_UPDATE_SUCCESS_KEY = "athletes_update_success_message"
ATHLETES_TABLE_NONCE_KEY = "athletes_table_nonce"
ATHLETES_DELETE_CANDIDATE_IDS_KEY = "athletes_delete_candidate_ids"


@st.fragment
def _render_athletes_management_section() -> None:
    st.divider()
    st.subheader("Lista atleti")

    show_inactive = st.checkbox("Mostra anche inattivi", value=True)

    athletes = list_athletes(include_inactive=show_inactive)
    all_matches = list_matches()
    rating_by_athlete_id = build_current_rating_map()
    level_profiles = build_athlete_level_profile_map(
        athletes=athletes,
        matches=all_matches,
        rating_by_athlete_id=rating_by_athlete_id,
    )

    athletes_update_success_message = st.session_state.pop(
        ATHLETES_UPDATE_SUCCESS_KEY,
        None,
    )
    if athletes_update_success_message:
        st.success(athletes_update_success_message)

    if not athletes:
        st.info("Nessun atleta presente.")
        return

    table_nonce = int(st.session_state.get(ATHLETES_TABLE_NONCE_KEY, 0))
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
                "Livello assegnato": get_level_label(a.level),
                "Livello suggerito": get_level_label(
                    level_profiles[a.id]["suggested_level"]
                ),
                "Peso": float(a.default_weight),
                "Rating": (
                    rating_by_athlete_id[a.id]
                    if a.id in rating_by_athlete_id
                    else "N.D."
                ),
                "Attivo": bool(a.active),
            }
            for a in athletes
        ]
    )

    table_result = render_table_component(
        df=df,
        spec=ATHLETES_TABLE_SPEC,
        renderer="aggrid",
        key=f"athletes_table_{table_nonce}",
    )

    selected_athlete_ids: list[int] = []
    if (
        not table_result.selected_rows_df.empty
        and "ID" in table_result.selected_rows_df.columns
    ):
        selected_athlete_ids = [
            int(athlete_id)
            for athlete_id in table_result.selected_rows_df["ID"].tolist()
        ]

    action_col1, action_col2 = st.columns(2)

    if action_col1.button("Salva modifiche", type="primary", use_container_width=True):
        try:
            edited_df = ATHLETES_TABLE_SPEC.normalize_from_view(table_result.edited_df)
            rows: list[dict[str, Any]] = [
                {str(key): value for key, value in row.items()}
                for row in edited_df.to_dict(orient="records")
            ]
            updated_count = update_athletes_from_rows(rows)
            recompute_ratings()
            st.session_state[ATHLETES_TABLE_NONCE_KEY] = table_nonce + 1
            st.session_state[ATHLETES_UPDATE_SUCCESS_KEY] = (
                f"Modifiche salvate correttamente ({updated_count} atleti aggiornati)."
            )
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))
        except Exception as exc:
            st.error(f"Errore durante il salvataggio: {exc}")

    if action_col2.button(
        "Richiedi eliminazione selezionati",
        use_container_width=True,
        disabled=not selected_athlete_ids,
    ):
        st.session_state[ATHLETES_DELETE_CANDIDATE_IDS_KEY] = selected_athlete_ids
        st.rerun()

    pending_delete_ids = st.session_state.get(ATHLETES_DELETE_CANDIDATE_IDS_KEY, [])
    athletes_by_id = {athlete.id: athlete for athlete in athletes}
    pending_athletes = [
        athletes_by_id[athlete_id]
        for athlete_id in pending_delete_ids
        if athlete_id in athletes_by_id
    ]

    if not pending_athletes:
        return

    if len(pending_athletes) == 1:
        st.warning(
            "Stai per eliminare un atleta. L'operazione e consentita solo se non compare in alcun incontro."
        )
    else:
        st.warning(
            f"Stai per eliminare {len(pending_athletes)} atleti. "
            "L'operazione e consentita solo se nessuno di loro compare in incontri."
        )

    for athlete in pending_athletes[:10]:
        athlete_name = f"{athlete.first_name} {athlete.last_name or ''}".strip()
        st.caption(athlete_name or f"ID {athlete.id}")

    if len(pending_athletes) > 10:
        st.caption(f"... e altri {len(pending_athletes) - 10} atleti selezionati.")

    confirm_col, cancel_col = st.columns(2)

    if confirm_col.button(
        "Conferma eliminazione atleti",
        type="primary",
        use_container_width=True,
    ):
        try:
            deleted_names = delete_athletes_if_unused(pending_delete_ids)
            st.session_state[ATHLETES_DELETE_CANDIDATE_IDS_KEY] = []
            st.session_state[ATHLETES_TABLE_NONCE_KEY] = table_nonce + 1
            if len(deleted_names) == 1:
                st.session_state[ATHLETES_UPDATE_SUCCESS_KEY] = (
                    f"Atleta eliminato: {deleted_names[0]}."
                )
            else:
                st.session_state[ATHLETES_UPDATE_SUCCESS_KEY] = (
                    f"Atleti eliminati correttamente ({len(deleted_names)})."
                )
            st.rerun()
        except ValueError as exc:
            st.session_state[ATHLETES_DELETE_CANDIDATE_IDS_KEY] = []
            st.error(str(exc))

    if cancel_col.button(
        "Annulla eliminazione atleti",
        use_container_width=True,
    ):
        st.session_state[ATHLETES_DELETE_CANDIDATE_IDS_KEY] = []
        st.rerun()


def render_athletes_page() -> None:
    st.title("Atleti")

    st.markdown(
        """
Il campo **livello assegnato** rappresenta una stima iniziale manuale del livello tecnico.

Il campo **livello suggerito** viene calcolato leggendo il rating corrente
attraverso le soglie livello/rating.

Il campo **rating** rappresenta invece una valutazione dinamica, calcolata in base
ai risultati ottenuti. Tutti gli atleti partono dallo stesso rating iniziale:
il livello assegnato non modifica il rating di partenza.
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
            "Livello assegnato *",
            options=level_labels,
            key="athlete_form_level_label",
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
                )
                recompute_ratings()

                st.session_state["reset_athlete_form_level_label"] = True

                st.success(
                    f"Atleta salvato: {athlete.first_name} "
                    f"(id={athlete.id}, livello assegnato={get_level_label(athlete.level)})"
                )
                st.rerun()

    _render_athletes_management_section()
    return

    st.divider()

    st.subheader("Lista atleti")

    show_inactive = st.checkbox("Mostra anche inattivi", value=True)

    athletes = list_athletes(include_inactive=show_inactive)
    all_matches = list_matches()
    rating_by_athlete_id = build_current_rating_map()
    level_profiles = build_athlete_level_profile_map(
        athletes=athletes,
        matches=all_matches,
        rating_by_athlete_id=rating_by_athlete_id,
    )

    if not athletes:
        st.info("Nessun atleta presente.")
    else:
        table_nonce = int(st.session_state.get(ATHLETES_TABLE_NONCE_KEY, 0))
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
                    "Livello assegnato": get_level_label(a.level),
                    "Livello suggerito": get_level_label(
                        level_profiles[a.id]["suggested_level"]
                    ),
                    "Peso": float(a.default_weight),
                    "Rating": (
                        rating_by_athlete_id[a.id]
                        if a.id in rating_by_athlete_id
                        else "N.D."
                    ),
                    "Attivo": bool(a.active),
                }
                for a in athletes
            ]
        )

        table_result = render_table_component(
            df=df,
            spec=ATHLETES_TABLE_SPEC,
            renderer="aggrid",
            key=f"athletes_table_{table_nonce}",
        )

        selected_athlete_ids: list[int] = []
        if (
            not table_result.selected_rows_df.empty
            and "ID" in table_result.selected_rows_df.columns
        ):
            selected_athlete_ids = [
                int(athlete_id)
                for athlete_id in table_result.selected_rows_df["ID"].tolist()
            ]

        action_col1, action_col2 = st.columns(2)

        if action_col1.button("Salva modifiche", type="primary", use_container_width=True):
            try:
                edited_df = ATHLETES_TABLE_SPEC.normalize_from_view(table_result.edited_df)

                rows: list[dict[str, Any]] = [
                    {str(key): value for key, value in row.items()}
                    for row in edited_df.to_dict(orient="records")
                ]

                updated_count = update_athletes_from_rows(rows)
                recompute_ratings()
                st.session_state[ATHLETES_TABLE_NONCE_KEY] = table_nonce + 1
                st.session_state[ATHLETES_UPDATE_SUCCESS_KEY] = (
                    f"Modifiche salvate correttamente ({updated_count} atleti aggiornati)."
                )
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
            except Exception as exc:
                st.error(f"Errore durante il salvataggio: {exc}")

        if action_col2.button(
            "Richiedi eliminazione selezionati",
            use_container_width=True,
            disabled=not selected_athlete_ids,
        ):
            st.session_state[ATHLETES_DELETE_CANDIDATE_IDS_KEY] = selected_athlete_ids
            st.rerun()

        pending_delete_ids = st.session_state.get(ATHLETES_DELETE_CANDIDATE_IDS_KEY, [])
        athletes_by_id = {athlete.id: athlete for athlete in athletes}
        pending_athletes = [
            athletes_by_id[athlete_id]
            for athlete_id in pending_delete_ids
            if athlete_id in athletes_by_id
        ]

        if pending_athletes:
            if len(pending_athletes) == 1:
                st.warning(
                    "Stai per eliminare un atleta. L'operazione è consentita solo se non compare in alcun incontro."
                )
            else:
                st.warning(
                    f"Stai per eliminare {len(pending_athletes)} atleti. "
                    "L'operazione è consentita solo se nessuno di loro compare in incontri."
                )

            for athlete in pending_athletes[:10]:
                athlete_name = f"{athlete.first_name} {athlete.last_name or ''}".strip()
                st.caption(athlete_name or f"ID {athlete.id}")

            if len(pending_athletes) > 10:
                st.caption(f"... e altri {len(pending_athletes) - 10} atleti selezionati.")

            confirm_col, cancel_col = st.columns(2)

            if confirm_col.button(
                "Conferma eliminazione atleti",
                type="primary",
                use_container_width=True,
            ):
                try:
                    deleted_names = delete_athletes_if_unused(pending_delete_ids)
                    st.session_state[ATHLETES_DELETE_CANDIDATE_IDS_KEY] = []
                    st.session_state[ATHLETES_TABLE_NONCE_KEY] = table_nonce + 1
                    if len(deleted_names) == 1:
                        st.session_state[ATHLETES_UPDATE_SUCCESS_KEY] = (
                            f"Atleta eliminato: {deleted_names[0]}."
                        )
                    else:
                        st.session_state[ATHLETES_UPDATE_SUCCESS_KEY] = (
                            f"Atleti eliminati correttamente ({len(deleted_names)})."
                        )
                    st.rerun()
                except ValueError as exc:
                    st.session_state[ATHLETES_DELETE_CANDIDATE_IDS_KEY] = []
                    st.error(str(exc))

            if cancel_col.button(
                "Annulla eliminazione atleti",
                use_container_width=True,
            ):
                st.session_state[ATHLETES_DELETE_CANDIDATE_IDS_KEY] = []
                st.rerun()

        athletes_update_success_message = st.session_state.pop(
            ATHLETES_UPDATE_SUCCESS_KEY,
            None,
        )
        if athletes_update_success_message:
            st.success(athletes_update_success_message)
