from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd
import streamlit as st
from sqlalchemy import select

from src.admin_formulas_shared import (
    apply_pending_reset,
    format_athlete_preview_label,
    get_widget_value,
    queue_group_reset,
    render_flash_message,
    render_group_inputs,
    set_flash_message,
)
from src.database import get_session
from src.formula_config_service import (
    get_full_config,
    reset_group_to_defaults,
    save_group_parameters,
)
from src.matchmaking_probability_ui import render_win_probability_metrics
from src.models import Athlete, Match
from src.pairing import calculate_age, generate_candidate_pairs


def render_matchmaking_tab() -> None:
    config = get_full_config()
    matchmaking_config: dict[str, Any] = config.get("matchmaking", {})
    ratings_config: dict[str, Any] = config.get("ratings", {})

    apply_pending_reset("matchmaking", "matchmaking")

    st.subheader("Formula matchmaking (indice di disomogeneità)")

    st.info(
        """
Il matchmaking usa il **mismatch** per valutare quanto una coppia sia adatta ed equilibrata.

In pratica:
- genera le coppie candidate compatibili con i vincoli scelti
- calcola il mismatch per ogni coppia
- privilegia le coppie con mismatch più basso

Quindi il mismatch è il vero criterio con cui il sistema confronta la qualità degli accoppiamenti.
"""
    )

    st.markdown(
        r"""
L'indice di disomogeneità tra due atleti A e B è calcolato così:

$$
mismatch =
(|peso_A - peso_B| \times weight\_factor)
+
(|livello_A - livello_B| \times level\_factor)
+
\left(\frac{|rating_A - rating_B|}{rating\_divisor}\right)
+
(|età_A - età_B| \times age\_factor)
+
(\text{rematch\_count} \times rematch\_penalty)
$$
"""
    )

    with st.expander("Cosa cambia tra mismatch e rating"):
        st.markdown(
            """
- la **probabilità Elo / rating** dice chi è favorito in base alla forza competitiva stimata
- il **mismatch** dice quanto l'accoppiamento è appropriato nel complesso

Quindi:
- il rating è un **indicatore di pronostico**
- il mismatch è un **criterio di qualità dell'accoppiamento**

Il rating da solo non basta per costruire match equilibrati, perché non considera direttamente:
- differenza di peso
- differenza di level
- differenza di età
- rematch già avvenuti
- vincoli logici del sistema

Per questo due atleti possono avere probabilità Elo vicine al 50/50, ma restare comunque un cattivo accoppiamento.
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
                """
**Significato dei parametri logici**
- `use_rating_default`: decide se includere la differenza rating nel mismatch
- `avoid_rematches_default`: decide se penalizzare gli atleti che si sono già affrontati
- `same_sex_only_default`: decide se consentire solo accoppiamenti tra atleti dello stesso sesso
"""
            )

            col1, col2, col3 = st.columns(3)
            save_clicked = col1.form_submit_button("Salva parametri matchmaking")
            save_and_recalc_clicked = col2.form_submit_button("Salva e ricalcola mismatch")
            reset_clicked = col3.form_submit_button("Ripristina default matchmaking")

    if save_clicked:
        save_group_parameters("matchmaking", matchmaking_inputs)
        set_flash_message(
            "success",
            "Parametri matchmaking salvati correttamente.",
            target="matchmaking",
        )
        st.rerun()

    if save_and_recalc_clicked:
        save_group_parameters("matchmaking", matchmaking_inputs)
        set_flash_message(
            "success",
            "Parametri matchmaking salvati e mismatch aggiornato.",
            target="matchmaking",
        )
        st.rerun()

    if reset_clicked:
        reset_group_to_defaults("matchmaking")
        queue_group_reset("matchmaking", "matchmaking")
        set_flash_message(
            "warning",
            "Parametri matchmaking ripristinati ai valori di default.",
            target="matchmaking",
        )
        st.rerun()

    st.divider()
    st.subheader("Anteprima mismatch")

    session = get_session()
    try:
        athletes: list[Athlete] = list(
            session.scalars(select(Athlete).where(Athlete.active == True)).all()
        )
        matches: list[Match] = list(session.scalars(select(Match)).all())
    finally:
        session.close()

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
                "Età": calculate_age(athlete_a.birth_date, date.today()),
                "Peso": float(athlete_a.default_weight),
                "Level": int(athlete_a.level),
                "Rating": row["rating_a"],
                "Team": athlete_a.team or "",
            },
            {
                "Atleta": athlete_b_name,
                "Stile": athlete_b.style,
                "Sesso": athlete_b.sex,
                "Età": calculate_age(athlete_b.birth_date, date.today()),
                "Peso": float(athlete_b.default_weight),
                "Level": int(athlete_b.level),
                "Rating": row["rating_b"],
                "Team": athlete_b.team or "",
            },
        ]
    )

    st.write("**Atleti selezionati**")
    st.table(athlete_info_df)

    st.caption(
        "La probabilità Elo sotto indica chi è favorito. "
        "L'indice mismatch invece misura quanto la coppia è adatta nel complesso."
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
                "Parametro": f"× {matchmaking_config['weight_factor']}",
                "Contributo": row["weight_component"],
            },
            {
                "Componente": "Differenza level",
                "Valore base": row["level_diff"],
                "Parametro": f"× {matchmaking_config['level_factor']}",
                "Contributo": row["level_component"],
            },
            {
                "Componente": "Differenza rating",
                "Valore base": row["rating_diff"],
                "Parametro": (
                    f"÷ {matchmaking_config['rating_divisor']}"
                    if use_rating else "Disattivato"
                ),
                "Contributo": row["rating_component"],
            },
            {
                "Componente": "Differenza età",
                "Valore base": row["age_diff"],
                "Parametro": f"× {matchmaking_config['age_factor']}",
                "Contributo": row["age_component"],
            },
            {
                "Componente": "Rematch penalty",
                "Valore base": row["previous_matches"],
                "Parametro": (
                    f"× {matchmaking_config['rematch_penalty']}"
                    if avoid_rematches else "Disattivato"
                ),
                "Contributo": row["rematch_penalty"],
            },
        ]
    )

    st.write("**Scomposizione mismatch**")
    st.table(preview_df)

    render_flash_message("matchmaking")