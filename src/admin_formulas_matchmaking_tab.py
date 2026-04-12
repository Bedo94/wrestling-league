from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd
import streamlit as st

from src.admin_formulas_shared import (
    apply_pending_reset,
    format_athlete_preview_label,
    get_formula_draft_config,
    get_widget_value,
    queue_group_reset,
    reset_formula_group_draft,
    render_flash_message,
    render_group_inputs,
    save_formula_group_draft,
    set_flash_message,
)
from src.athletes import list_athletes
from src.matches import list_matches
from src.matchmaking_probability_ui import render_win_probability_metrics
from src.pairing import calculate_age, generate_candidate_pairs
from src.ratings import build_current_rating_map


@st.fragment
def render_matchmaking_tab() -> None:
    config = get_formula_draft_config()
    matchmaking_config: dict[str, Any] = config.get("matchmaking", {})

    apply_pending_reset("matchmaking", "matchmaking")

    st.subheader("Formula matchmaking (indice di disomogeneita)")

    st.info(
        """
Il matchmaking usa il **mismatch** per valutare quanto una coppia sia adatta ed equilibrata.

In pratica:
- genera le coppie candidate compatibili con i vincoli scelti
- calcola il mismatch per ogni coppia
- privilegia le coppie con mismatch piu basso
"""
    )

    st.markdown(
        r"""
L'indice di disomogeneita tra due atleti A e B e calcolato cosi:

$$
mismatch =
(|peso_A - peso_B| \times weight\_factor)
+
(|livello_A - livello_B| \times level\_factor)
+
\left(\frac{|rating_A - rating_B|}{rating\_divisor}\right)
+
(|eta_A - eta_B| \times age\_factor)
+
(\text{rematch\_count} \times rematch\_penalty)
$$
"""
    )

    matchmaking_order = [
        "max_weight_diff_default",
        "weight_factor",
        "max_level_diff_default",
        "level_factor",
        "use_rating_default",
        "rating_divisor",
        "max_age_diff_default",
        "age_factor",
        "avoid_rematches_default",
        "rematch_penalty",
        "same_sex_only_default",
    ]

    with st.expander("Parametri matchmaking", expanded=False):
        with st.form("matchmaking_form"):
            matchmaking_inputs = render_group_inputs(
                matchmaking_config,
                matchmaking_order,
                "matchmaking",
            )

            st.caption(
                "La componente `level_factor` pesa la differenza tra i livelli assegnati. "
                "Il livello suggerito resta solo un supporto all'operatore. "
                "`use_rating_default` include la differenza rating nel mismatch."
            )

            col1, col2 = st.columns(2)
            save_and_apply_clicked = col1.form_submit_button(
                "Salva e aggiorna mismatch"
            )
            reset_clicked = col2.form_submit_button("Ripristina default matchmaking")

    if save_and_apply_clicked:
        save_formula_group_draft("matchmaking", matchmaking_inputs)
        set_flash_message(
            "success",
            "Parametri matchmaking applicati. Mismatch e anteprima aggiornati.",
            target="matchmaking",
        )
        st.rerun()

    if reset_clicked:
        reset_formula_group_draft("matchmaking")
        queue_group_reset("matchmaking", "matchmaking")
        set_flash_message(
            "warning",
            "Parametri matchmaking della bozza ripristinati ai valori di default.",
            target="matchmaking",
        )
        st.rerun()

    st.divider()
    st.subheader("Anteprima mismatch")

    athletes = list_athletes(include_inactive=False)
    matches = list_matches()

    if len(athletes) < 2:
        st.info("Servono almeno due atleti attivi per mostrare l'anteprima.")
        render_flash_message("matchmaking")
        return

    athlete_options = {
        athlete.id: format_athlete_preview_label(athlete, date.today())
        for athlete in athletes
    }
    athlete_ids = list(athlete_options.keys())
    default_b_index = 1 if len(athlete_ids) > 1 else 0

    col1, col2 = st.columns(2)
    with col1:
        athlete_a_id = st.selectbox(
            "Atleta A",
            options=athlete_ids,
            format_func=lambda athlete_id: athlete_options[athlete_id],
            key="matchmaking_preview_athlete_a",
        )
    with col2:
        athlete_b_id = st.selectbox(
            "Atleta B",
            options=athlete_ids,
            format_func=lambda athlete_id: athlete_options[athlete_id],
            key="matchmaking_preview_athlete_b",
            index=default_b_index,
        )

    if athlete_a_id == athlete_b_id:
        st.warning("Seleziona due atleti diversi per l'anteprima.")
        render_flash_message("matchmaking")
        return

    athlete_by_id = {athlete.id: athlete for athlete in athletes}
    selected_athletes = [athlete_by_id[athlete_a_id], athlete_by_id[athlete_b_id]]
    rating_by_athlete_id = build_current_rating_map()

    max_weight_diff = get_widget_value(
        "matchmaking",
        "max_weight_diff_default",
        matchmaking_config["max_weight_diff_default"],
        float,
    )
    max_level_diff = get_widget_value(
        "matchmaking",
        "max_level_diff_default",
        matchmaking_config["max_level_diff_default"],
        int,
    )
    raw_max_age_diff = st.session_state.get(
        "matchmaking_max_age_diff_default",
        matchmaking_config["max_age_diff_default"],
    )
    max_age_diff = None if raw_max_age_diff is None else int(raw_max_age_diff)

    use_rating = get_widget_value(
        "matchmaking",
        "use_rating_default",
        matchmaking_config["use_rating_default"],
        bool,
    )
    avoid_rematches = get_widget_value(
        "matchmaking",
        "avoid_rematches_default",
        matchmaking_config["avoid_rematches_default"],
        bool,
    )
    same_sex_only = get_widget_value(
        "matchmaking",
        "same_sex_only_default",
        matchmaking_config["same_sex_only_default"],
        bool,
    )

    preview_pairs = generate_candidate_pairs(
        athletes=selected_athletes,
        matches=matches,
        reference_date=date.today(),
        max_weight_diff=max_weight_diff,
        max_level_diff=max_level_diff,
        max_age_diff=max_age_diff,
        use_rating=use_rating,
        avoid_rematches=avoid_rematches,
        same_sex_only=same_sex_only,
        rating_by_athlete_id=rating_by_athlete_id,
        all_matches=matches,
    )

    if not preview_pairs:
        st.info("Con i parametri attuali questa coppia non genera un accoppiamento valido.")
        render_flash_message("matchmaking")
        return

    row = preview_pairs[0]

    athlete_a = row["athlete_a"]
    athlete_b = row["athlete_b"]

    athlete_a_name = f"{athlete_a.first_name} {athlete_a.last_name or ''}".strip()
    athlete_b_name = f"{athlete_b.first_name} {athlete_b.last_name or ''}".strip()

    athlete_info_df = pd.DataFrame(
        [
            {
                "Atleta": athlete_a_name,
                "Stile": athlete_a.style,
                "Sesso": athlete_a.sex,
                "Eta": calculate_age(athlete_a.birth_date, date.today()),
                "Peso": float(athlete_a.default_weight),
                "Level assegnato": row["assigned_level_a"],
                "Level suggerito": row["suggested_level_a"],
                "Match validi": row["valid_match_count_a"],
                "Rating": row["rating_a"],
                "Team": athlete_a.team or "",
            },
            {
                "Atleta": athlete_b_name,
                "Stile": athlete_b.style,
                "Sesso": athlete_b.sex,
                "Eta": calculate_age(athlete_b.birth_date, date.today()),
                "Peso": float(athlete_b.default_weight),
                "Level assegnato": row["assigned_level_b"],
                "Level suggerito": row["suggested_level_b"],
                "Match validi": row["valid_match_count_b"],
                "Rating": row["rating_b"],
                "Team": athlete_b.team or "",
            },
        ]
    )

    st.write("**Atleti selezionati**")
    st.table(athlete_info_df)

    st.caption(
        "La probabilita Elo sotto indica chi e favorito. "
        "L'indice mismatch misura invece quanto la coppia e adatta nel complesso."
    )

    render_win_probability_metrics(
        athlete_a_name=athlete_a_name,
        athlete_b_name=athlete_b_name,
        rating_a=row["rating_a"],
        rating_b=row["rating_b"],
        mismatch_index=row["mismatch_index"],
        previous_matches=row["previous_matches"],
    )

    preview_df = pd.DataFrame(
        [
            {
                "Componente": "Differenza peso",
                "Valore base": f"{row['weight_diff']} kg",
                "Parametro": f"x {matchmaking_config['weight_factor']}",
                "Contributo": row["weight_component"],
            },
            {
                "Componente": "Differenza level",
                "Valore base": str(row["level_diff"]),
                "Parametro": f"x {matchmaking_config['level_factor']}",
                "Contributo": row["level_component"],
            },
            {
                "Componente": "Differenza rating",
                "Valore base": str(row["rating_diff"]),
                "Parametro": (
                    f"/ {matchmaking_config['rating_divisor']}"
                    if use_rating
                    else "Disattivato"
                ),
                "Contributo": row["rating_component"],
            },
            {
                "Componente": "Differenza eta",
                "Valore base": str(row["age_diff"]),
                "Parametro": f"x {matchmaking_config['age_factor']}",
                "Contributo": row["age_component"],
            },
            {
                "Componente": "Rematch penalty",
                "Valore base": str(row["previous_matches"]),
                "Parametro": (
                    f"x {matchmaking_config['rematch_penalty']}"
                    if avoid_rematches
                    else "Disattivato"
                ),
                "Contributo": row["rematch_penalty"],
            },
        ]
    )

    st.write("**Scomposizione mismatch**")
    st.table(preview_df)

    render_flash_message("matchmaking")
