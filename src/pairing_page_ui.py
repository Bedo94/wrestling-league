from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from src.athletes import list_athletes
from src.db_runtime import bootstrap_database_from_state
from src.events import list_events
from src.levels import get_level_label
from src.matches import list_matches
from src.matchmaking_probability_ui import build_win_probability_columns
from src.pairing import (
    calculate_age,
    generate_candidate_pairs,
    select_greedy_pairings,
)
from src.table_component import render_table_component
from src.table_specs import (
    build_candidate_pairings_table_spec,
    build_pairing_leftovers_table_spec,
    build_selected_pairings_table_spec,
)


def athlete_label(athlete, reference_date: date) -> str:
    full_name = f"{athlete.first_name} {athlete.last_name or ''}".strip()
    age = calculate_age(athlete.birth_date, reference_date)
    rating_value = athlete.rating if athlete.rating is not None else "N.D."
    return (
        f"{full_name} — {athlete.style} — {athlete.sex} — "
        f"{athlete.default_weight:.1f} kg — "
        f"{get_level_label(athlete.level)} — "
        f"{age} anni — rating {rating_value}"
    )


def event_label(event) -> str:
    return f"{event.name} — {event.event_date}"


def prepare_event_selection_state(event_options: list[int]) -> str:
    event_ids_key = "pairing_event_ids"
    signature_key = "pairing_event_options_signature"

    event_options_signature = tuple(event_options)
    current_selection = st.session_state.get(event_ids_key, [])
    valid_selection = [event_id for event_id in current_selection if event_id in event_options]
    previous_signature = st.session_state.get(signature_key)

    if previous_signature != event_options_signature:
        st.session_state[event_ids_key] = valid_selection
        st.session_state[signature_key] = event_options_signature

    if event_ids_key not in st.session_state:
        st.session_state[event_ids_key] = []

    return event_ids_key


def _build_selected_pairings_dataframe(selected_pairs: list[dict]) -> pd.DataFrame:
    selected_rows = []
    for pair in selected_pairs:
        athlete_a = pair["athlete_a"]
        athlete_b = pair["athlete_b"]

        selected_rows.append(
            {
                "Atleta A": f"{athlete_a.first_name} {athlete_a.last_name or ''}".strip(),
                "Atleta B": f"{athlete_b.first_name} {athlete_b.last_name or ''}".strip(),
                "Stile": pair["style"],
                "Δ peso": pair["weight_diff"],
                "Δ level": pair["level_gap_label"],
                "Δ rating": pair["rating_diff"],
                "Δ età": pair["age_diff"],
                "Storico": pair["previous_matches_label"],
                "Indice mismatch": pair["mismatch_index"],
                "rating_a": pair["rating_a"],
                "rating_b": pair["rating_b"],
            }
        )

    selected_df = pd.DataFrame(selected_rows)
    selected_df = build_win_probability_columns(selected_df)

    return selected_df[
        [
            "Atleta A",
            "Atleta B",
            "Stile",
            "Δ peso",
            "Δ level",
            "Δ rating",
            "Δ età",
            "Storico",
            "Prob. A (%)",
            "Prob. B (%)",
            "Indice mismatch",
        ]
    ].copy()


def _build_candidate_pairings_dataframe(candidates: list[dict]) -> pd.DataFrame:
    candidate_rows = []
    for pair in candidates:
        athlete_a = pair["athlete_a"]
        athlete_b = pair["athlete_b"]

        candidate_rows.append(
            {
                "Atleta A": f"{athlete_a.first_name} {athlete_a.last_name or ''}".strip(),
                "Atleta B": f"{athlete_b.first_name} {athlete_b.last_name or ''}".strip(),
                "Stile": pair["style"],
                "Peso A": float(athlete_a.default_weight),
                "Peso B": float(athlete_b.default_weight),
                "Level A": get_level_label(athlete_a.level),
                "Level B": get_level_label(athlete_b.level),
                "Rating A": pair["rating_a"],
                "Rating B": pair["rating_b"],
                "Età A": pair["age_a"],
                "Età B": pair["age_b"],
                "Δ peso": pair["weight_diff"],
                "Δ level": pair["level_gap_label"],
                "Δ rating": pair["rating_diff"],
                "Δ età": pair["age_diff"],
                "Storico": pair["previous_matches_label"],
                "Comp. peso": pair["weight_component"],
                "Comp. level": pair["level_component"],
                "Comp. rating": pair["rating_component"],
                "Comp. età": pair["age_component"],
                "Pen. rematch": pair["rematch_penalty"],
                "Indice mismatch": pair["mismatch_index"],
                "rating_a": pair["rating_a"],
                "rating_b": pair["rating_b"],
            }
        )

    candidate_df = pd.DataFrame(candidate_rows)
    candidate_df = build_win_probability_columns(candidate_df)

    return candidate_df[
        [
            "Atleta A",
            "Atleta B",
            "Stile",
            "Peso A",
            "Peso B",
            "Level A",
            "Level B",
            "Rating A",
            "Rating B",
            "Età A",
            "Età B",
            "Δ peso",
            "Δ level",
            "Δ rating",
            "Δ età",
            "Storico",
            "Prob. A (%)",
            "Prob. B (%)",
            "Comp. peso",
            "Comp. level",
            "Comp. rating",
            "Comp. età",
            "Pen. rematch",
            "Indice mismatch",
        ]
    ].copy()


def _build_leftovers_dataframe(leftovers, reference_date: date) -> pd.DataFrame:
    leftover_rows = []
    for athlete in leftovers:
        leftover_rows.append(
            {
                "Atleta": f"{athlete.first_name} {athlete.last_name or ''}".strip(),
                "Sesso": athlete.sex,
                "Stile": athlete.style,
                "Peso": float(athlete.default_weight),
                "Level": get_level_label(athlete.level),
                "Rating": athlete.rating if athlete.rating is not None else "N.D.",
                "Età": calculate_age(athlete.birth_date, reference_date),
            }
        )

    return pd.DataFrame(leftover_rows)


def render_pairing_page() -> None:
    bootstrap_database_from_state()

    st.title("Accoppiamenti / Matchmaking")
    st.caption("Più basso è l’indice mismatch, più l’accoppiamento è equilibrato.")

    events = list_events()
    all_athletes = list_athletes(include_inactive=False)
    all_matches = list_matches()

    if not events:
        st.warning("Prima devi creare almeno un evento.")
        st.stop()

    if len(all_athletes) < 2:
        st.warning("Servono almeno due atleti attivi.")
        st.stop()

    events_map = {event.id: event for event in events}
    available_years = sorted({event.event_date.year for event in events})

    selected_event_ids: list[int] = []
    selected_years: list[int] = []

    st.subheader("Configurazione")

    with st.expander("Filtri matchmaking", expanded=False):
        tab_periodo, tab_profilo, tab_limiti, tab_vincoli = st.tabs(
            [
                "Periodo ed evento",
                "Profilo atleti",
                "Limiti differenze",
                "Vincoli e penalità",
            ]
        )

        with tab_periodo:
            period_col1, period_col2 = st.columns(2)

            with period_col1:
                if len(available_years) == 1:
                    st.caption(f"Anno disponibile: {available_years[0]}")
                    selected_year_range = (available_years[0], available_years[0])
                else:
                    selected_year_range = st.slider(
                        "Intervallo anni",
                        min_value=available_years[0],
                        max_value=available_years[-1],
                        value=(available_years[0], available_years[-1]),
                        step=1,
                    )

                selected_years = list(
                    range(selected_year_range[0], selected_year_range[1] + 1)
                )

            with period_col2:
                period_events = [
                    event
                    for event in events
                    if event.event_date.year in selected_years
                ]

                event_options = [event.id for event in period_events]
                event_ids_key = prepare_event_selection_state(event_options)

                if not event_options:
                    st.caption("Nessun evento disponibile per gli anni selezionati.")
                    selected_event_ids = []
                else:
                    selected_event_ids = st.multiselect(
                        "Evento/i di riferimento",
                        options=event_options,
                        key=event_ids_key,
                        format_func=lambda event_id: event_label(events_map[event_id]),
                        placeholder="Se vuoto, considera tutti gli eventi del periodo",
                    )

            st.caption(
                "Se il filtro evento è vuoto, il matchmaking considera tutti gli eventi inclusi nell’intervallo anni selezionato."
            )

        period_events = [
            event
            for event in events
            if event.event_date.year in selected_years
        ]

        selected_scope_events = [
            event
            for event in period_events
            if not selected_event_ids or event.id in selected_event_ids
        ]

        if not selected_scope_events:
            st.warning("Nessun evento disponibile nel periodo selezionato.")
            st.stop()

        reference_date = max(event.event_date for event in selected_scope_events)
        selected_scope_event_ids = {event.id for event in selected_scope_events}

        relevant_matches = [
            match
            for match in all_matches
            if match.event_id in selected_scope_event_ids
        ]

        styles = sorted({athlete.style for athlete in all_athletes})

        with tab_profilo:
            selected_styles = st.multiselect(
                "Stili",
                options=styles,
                default=styles,
                placeholder="Seleziona uno o più stili",
            )

            if not selected_styles:
                st.warning("Seleziona almeno uno stile.")
                st.stop()

            style_athletes = [
                athlete for athlete in all_athletes if athlete.style in selected_styles
            ]

            if len(style_athletes) < 2:
                st.warning("Non ci sono abbastanza atleti attivi per gli stili selezionati.")
                st.stop()

            sex_options = sorted({athlete.sex for athlete in style_athletes})
            level_options = sorted(
                {get_level_label(athlete.level) for athlete in style_athletes}
            )

            profile_col1, profile_col2 = st.columns(2)

            with profile_col1:
                selected_sexes = st.multiselect(
                    "Sesso",
                    options=sex_options,
                    default=sex_options,
                )

            with profile_col2:
                selected_levels = st.multiselect(
                    "Level",
                    options=level_options,
                    default=level_options,
                )

            filtered_pool = [
                athlete
                for athlete in style_athletes
                if athlete.sex in selected_sexes
                and get_level_label(athlete.level) in selected_levels
            ]

            if len(filtered_pool) < 2:
                st.warning("I filtri correnti lasciano meno di due atleti.")
                st.stop()

            min_age = min(calculate_age(a.birth_date, reference_date) for a in filtered_pool)
            max_age = max(calculate_age(a.birth_date, reference_date) for a in filtered_pool)

            min_weight = min(float(a.default_weight) for a in filtered_pool)
            max_weight = max(float(a.default_weight) for a in filtered_pool)

            profile_col3, profile_col4 = st.columns(2)

            with profile_col3:
                if min_age == max_age:
                    st.caption(f"Età disponibile: {min_age}")
                    selected_age_range = (min_age, max_age)
                else:
                    selected_age_range = st.slider(
                        "Fascia età",
                        min_value=min_age,
                        max_value=max_age,
                        value=(min_age, max_age),
                        step=1,
                    )

            with profile_col4:
                if min_weight == max_weight:
                    st.caption(f"Peso disponibile: {min_weight:.1f} kg")
                    selected_weight_range = (min_weight, max_weight)
                else:
                    selected_weight_range = st.slider(
                        "Fascia peso di riferimento (kg)",
                        min_value=float(min_weight),
                        max_value=float(max_weight),
                        value=(float(min_weight), float(max_weight)),
                        step=0.5,
                    )

        with tab_limiti:
            limits_col1, limits_col2 = st.columns(2)

            level_diff_labels = {
                "Solo stesso livello": 0,
                "Max 1 fascia di differenza": 1,
                "Max 2 fasce di differenza": 2,
                "Max 3 fasce di differenza": 3,
            }

            with limits_col1:
                selected_level_diff_label = st.selectbox(
                    "Differenza level massima per coppia",
                    options=list(level_diff_labels.keys()),
                    index=2,
                )
                max_pair_level_diff = level_diff_labels[selected_level_diff_label]

                max_pair_age_diff = st.number_input(
                    "Differenza età massima per coppia",
                    min_value=0,
                    max_value=100,
                    value=8,
                    step=1,
                )

            with limits_col2:
                max_pair_weight_diff = st.number_input(
                    "Differenza peso massima per coppia (kg)",
                    min_value=0.0,
                    max_value=100.0,
                    value=10.0,
                    step=0.5,
                )

        with tab_vincoli:
            constraints_col1, constraints_col2 = st.columns(2)

            with constraints_col1:
                use_rating = st.checkbox(
                    "Usa rating nella compatibilità",
                    value=True,
                )

                avoid_rematches = st.checkbox(
                    "Penalizza rematch",
                    value=True,
                )

            with constraints_col2:
                same_sex_only = st.checkbox(
                    "Accoppia solo atleti dello stesso sesso",
                    value=False,
                )

                exclude_same_team = st.checkbox(
                    "Escludi incontri tra membri dello stesso team",
                    value=False,
                )

    age_min, age_max = selected_age_range
    weight_min, weight_max = selected_weight_range

    filtered_pool = [
        athlete
        for athlete in filtered_pool
        if age_min <= calculate_age(athlete.birth_date, reference_date) <= age_max
        and weight_min <= float(athlete.default_weight) <= weight_max
    ]

    if len(filtered_pool) < 2:
        st.warning("Dopo i filtri rimangono meno di due atleti.")
        st.stop()

    excluded_athletes = st.multiselect(
        "Escludi atleti dal pool",
        options=filtered_pool,
        default=[],
        format_func=lambda athlete: athlete_label(athlete, reference_date),
        placeholder="Cerca e seleziona gli atleti da escludere",
    )

    excluded_ids = {athlete.id for athlete in excluded_athletes}

    selected_athletes = [
        athlete
        for athlete in filtered_pool
        if athlete.id not in excluded_ids
    ]

    if len(selected_athletes) < 2:
        st.warning("Dopo l’esclusione rimangono meno di due atleti.")
        st.stop()

    candidates = generate_candidate_pairs(
        athletes=selected_athletes,
        matches=relevant_matches,
        reference_date=reference_date,
        max_weight_diff=float(max_pair_weight_diff),
        max_level_diff=int(max_pair_level_diff),
        max_age_diff=int(max_pair_age_diff),
        use_rating=use_rating,
        avoid_rematches=avoid_rematches,
        same_sex_only=same_sex_only,
        exclude_same_team=exclude_same_team,
    )

    if not candidates:
        st.warning("Nessuna coppia valida trovata con i vincoli selezionati.")
        st.stop()

    selected_pairs, leftovers = select_greedy_pairings(candidates, selected_athletes)

    show_all_pairs = st.checkbox(
        "Mostra tutti gli accoppiamenti",
        value=False,
    )

    st.subheader("Migliori accoppiamenti suggeriti")
    st.caption(
        "Le colonne 'Prob. A (%)' e 'Prob. B (%)' derivano dal rating Elo e indicano chi è favorito; "
        "l’indice mismatch invece misura quanto l’accoppiamento è equilibrato."
    )

    if not selected_pairs:
        st.info("Nessun accoppiamento selezionabile.")
    else:
        display_selected_df = _build_selected_pairings_dataframe(selected_pairs)
        selected_pairings_spec = build_selected_pairings_table_spec(
            display_df=display_selected_df
        )

        render_table_component(
            df=display_selected_df,
            spec=selected_pairings_spec,
            renderer="aggrid",
            key="selected_pairings_table",
        )

    if show_all_pairs:
        st.subheader("Tutti gli accoppiamenti")

        display_candidate_df = _build_candidate_pairings_dataframe(candidates)
        candidate_pairings_spec = build_candidate_pairings_table_spec(
            display_df=display_candidate_df
        )

        render_table_component(
            df=display_candidate_df,
            spec=candidate_pairings_spec,
            renderer="aggrid",
            key="candidate_pairings_table",
        )

        st.subheader("Atleti senza accoppiamento")

        if not leftovers:
            st.success("Tutti gli atleti selezionati hanno ricevuto un accoppiamento.")
        else:
            leftovers_df = _build_leftovers_dataframe(
                leftovers=leftovers,
                reference_date=reference_date,
            )
            leftovers_spec = build_pairing_leftovers_table_spec(
                display_df=leftovers_df
            )

            render_table_component(
                df=leftovers_df,
                spec=leftovers_spec,
                renderer="aggrid",
                key="pairing_leftovers_table",
            )