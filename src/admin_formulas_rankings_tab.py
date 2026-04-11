from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd
import streamlit as st

from src.admin_formulas_shared import (
    apply_pending_reset,
    get_formula_draft_config,
    get_typed_value,
    get_widget_value,
    queue_group_reset,
    reset_formula_group_draft,
    render_flash_message,
    save_formula_group_draft,
    set_flash_message,
)
from src.rankings import build_rankings
from src.rankings_page_ui import (
    render_athlete_rankings_table,
    render_team_rankings_table,
)


def render_athlete_ranking_section() -> None:
    config = get_formula_draft_config()
    athlete_ranking_config: dict[str, Any] = config.get("athlete_ranking", {})

    apply_pending_reset("athlete_ranking", "athlete_ranking")

    method_options = {
        "cumulative": "Cumulativa",
        "average_per_match": "Media punti/incontro",
    }

    current_method = str(
        athlete_ranking_config.get("ranking_method", "cumulative")
    )
    current_min_matches = int(
        athlete_ranking_config.get("min_matches_for_average", 2)
    )

    st.markdown(
        """
La classifica atleti ordina gli atleti in base ai **punti classifica** accumulati nei match.

Puoi scegliere se privilegiare:
- il totale punti accumulato
- la media punti per incontro
"""
    )

    st.markdown(
        r"""
Sono disponibili due metodi alternativi.

#### Metodo 1 — Cumulativa
$$
ranking\_score = class\_points\_total
$$

#### Metodo 2 — Media punti per incontro
$$
ranking\_score = \frac{class\_points\_total}{matches}
$$
"""
    )

    with st.expander("Interpretazione intuitiva dei metodi"):
        st.markdown(
            """
- **Cumulativa**  
  premia chi accumula più punti nel tempo

- **Media punti/incontro**  
  premia l'efficienza media per match disputato

- **Minimo incontri per classifica media**  
  serve a segnalare come **provvisori** gli atleti con pochi incontri,
  così la media non diventa fuorviante
"""
        )

    method_widget_key = "athlete_ranking_ranking_method"
    min_matches_widget_key = "athlete_ranking_min_matches_for_average"

    method_values = list(method_options.keys())
    default_method_index = (
        method_values.index(current_method) if current_method in method_values else 0
    )

    with st.expander("Parametri classifica atleti", expanded=False):
        with st.form("athlete_ranking_form"):
            if method_widget_key in st.session_state:
                ranking_method = st.selectbox(
                    "Metodo classifica atleti",
                    options=method_values,
                    format_func=lambda value: method_options[value],
                    key=method_widget_key,
                )
            else:
                ranking_method = st.selectbox(
                    "Metodo classifica atleti",
                    options=method_values,
                    index=default_method_index,
                    format_func=lambda value: method_options[value],
                    key=method_widget_key,
                )

            if min_matches_widget_key in st.session_state:
                min_matches = st.number_input(
                    "Minimo incontri per classifica media",
                    min_value=1,
                    step=1,
                    format="%d",
                    key=min_matches_widget_key,
                )
            else:
                min_matches = st.number_input(
                    "Minimo incontri per classifica media",
                    min_value=1,
                    value=int(current_min_matches),
                    step=1,
                    format="%d",
                    key=min_matches_widget_key,
                )

            athlete_inputs = {
                "ranking_method": ranking_method,
                "min_matches_for_average": int(min_matches),
            }

            col1, col2 = st.columns(2)
            save_and_apply_clicked = col1.form_submit_button(
                "Salva e aggiorna classifica atleti"
            )
            reset_clicked = col2.form_submit_button(
                "Ripristina default classifica atleti"
            )

    if save_and_apply_clicked:
        save_formula_group_draft("athlete_ranking", athlete_inputs)
        set_flash_message(
            "success",
            "Parametri classifica atleti applicati. Anteprima aggiornata.",
            target="athlete_ranking",
        )
        st.rerun()

    if reset_clicked:
        reset_formula_group_draft("athlete_ranking")
        queue_group_reset("athlete_ranking", "athlete_ranking")
        set_flash_message(
            "warning",
            "Metodo classifica atleti della bozza ripristinato ai valori di default.",
            target="athlete_ranking",
        )
        st.rerun()

    preview_method = get_widget_value(
        "athlete_ranking",
        "ranking_method",
        current_method,
        str,
    )
    preview_min_matches = get_widget_value(
        "athlete_ranking",
        "min_matches_for_average",
        current_min_matches,
        int,
    )

    preview_rows = build_rankings(
        reference_date=date.today(),
        ranking_method=preview_method,
        min_matches_for_average=preview_min_matches,
    )

    if not preview_rows:
        st.info("Non ci sono ancora dati sufficienti per mostrare l'anteprima atleti.")
        render_flash_message("athlete_ranking")
        return

    st.write("**Anteprima classifica atleti**")
    render_athlete_rankings_table(
        rankings_df=pd.DataFrame(preview_rows),
        ranking_method=preview_method,
        min_matches_for_average=preview_min_matches,
        key="admin_athlete_rankings_preview_table",
    )

    render_flash_message("athlete_ranking")


def render_team_ranking_section() -> None:
    config = get_formula_draft_config()
    team_config: dict[str, Any] = config.get("team_ranking", {})

    apply_pending_reset("team_ranking", "team_ranking")

    ranking_method_options = {
        "sum_with_bonus": "Somma punti atleti + bonus partecipazione",
        "average_per_participating_athlete": "Media punti per atleta partecipante",
    }

    current_ranking_method = get_typed_value(
        team_config,
        "ranking_method",
        "sum_with_bonus",
        str,
    )
    current_bonus = get_typed_value(
        team_config,
        "participation_bonus_per_athlete",
        2.0,
        float,
    )

    st.markdown(
        """
La classifica team aggrega i **punti classifica** ottenuti dagli atleti per confrontare le squadre.

Puoi scegliere se privilegiare:
- il contributo totale del team
- la resa media per atleta partecipante
"""
    )

    st.markdown(
        r"""
Sono disponibili due metodi alternativi.

#### Metodo 1 — Somma punti atleti + bonus partecipazione
$$
team\_score = class\_points\_total + (participating\_athletes \times participation\_bonus\_per\_athlete)
$$

#### Metodo 2 — Media punti per atleta partecipante
$$
team\_score = \frac{class\_points\_total}{participating\_athletes}
$$
"""
    )

    with st.expander("Interpretazione intuitiva dei metodi"):
        st.markdown(
            """
- **Somma punti atleti + bonus partecipazione**  
  premia sia il rendimento sia la presenza numerosa del team

- **Media punti per atleta partecipante**  
  misura l'efficienza media del team, indipendentemente dalla dimensione

Nel secondo metodo il bonus partecipazione non entra nel punteggio finale.
"""
        )

    method_widget_key = "team_ranking_ranking_method"
    bonus_widget_key = "team_ranking_participation_bonus_per_athlete"
    method_values = list(ranking_method_options.keys())
    default_method_index = (
        method_values.index(current_ranking_method)
        if current_ranking_method in method_values
        else 0
    )

    with st.expander("Parametri classifica team", expanded=False):
        with st.form("team_ranking_form"):
            if method_widget_key in st.session_state:
                ranking_method = st.selectbox(
                    "Metodo classifica team",
                    options=method_values,
                    format_func=lambda value: ranking_method_options[value],
                    key=method_widget_key,
                )
            else:
                ranking_method = st.selectbox(
                    "Metodo classifica team",
                    options=method_values,
                    index=default_method_index,
                    format_func=lambda value: ranking_method_options[value],
                    key=method_widget_key,
                )

            if bonus_widget_key in st.session_state:
                participation_bonus = st.number_input(
                    "Bonus partecipazione per atleta",
                    format="%.3f",
                    key=bonus_widget_key,
                )
            else:
                participation_bonus = st.number_input(
                    "Bonus partecipazione per atleta",
                    value=float(current_bonus),
                    format="%.3f",
                    key=bonus_widget_key,
                )

            if ranking_method == "average_per_participating_athlete":
                st.caption(
                    "In modalità media il bonus partecipazione viene ignorato nel punteggio finale."
                )

            team_inputs = {
                "ranking_method": ranking_method,
                "participation_bonus_per_athlete": float(participation_bonus),
            }

            col1, col2 = st.columns(2)
            save_and_apply_clicked = col1.form_submit_button(
                "Salva e aggiorna classifica team"
            )
            reset_clicked = col2.form_submit_button("Ripristina default team")

    if save_and_apply_clicked:
        save_formula_group_draft("team_ranking", team_inputs)
        set_flash_message(
            "success",
            "Parametri classifica team applicati. Anteprima aggiornata.",
            target="team_ranking",
        )
        st.rerun()

    if reset_clicked:
        reset_formula_group_draft("team_ranking")
        queue_group_reset("team_ranking", "team_ranking")
        set_flash_message(
            "warning",
            "Parametri classifica team della bozza ripristinati ai valori di default.",
            target="team_ranking",
        )
        st.rerun()

    preview_ranking_method = get_widget_value(
        "team_ranking",
        "ranking_method",
        current_ranking_method,
        str,
    )
    preview_participation_bonus = get_widget_value(
        "team_ranking",
        "participation_bonus_per_athlete",
        current_bonus,
        float,
    )

    ranking_rows = build_rankings(
        reference_date=date.today(),
        ranking_method="cumulative",
    )

    rankings_df = pd.DataFrame(ranking_rows)

    if rankings_df.empty:
        st.info("Non ci sono ancora dati sufficienti per mostrare l'anteprima team.")
        render_flash_message("team_ranking")
        return

    st.write("**Anteprima classifica team**")
    rendered = render_team_rankings_table(
        rankings_df=rankings_df,
        ranking_method=str(preview_ranking_method),
        participation_bonus_per_athlete=float(preview_participation_bonus),
        key="admin_team_rankings_preview_table",
    )

    if not rendered:
        st.info("Non ci sono ancora dati sufficienti per mostrare l'anteprima team.")

    render_flash_message("team_ranking")


def render_classification_tab() -> None:
    st.subheader("Formula classifica")

    st.info(
        """
La classifica si basa sui **punti classifica** accumulati dagli atleti nelle gare,
cioè sui punteggi prodotti dalla formula di scoring dopo ogni match.

In questa sezione puoi decidere come ordinare e aggregare questi punti:
- nella classifica atleti
- nella classifica team
"""
    )

    tab_athletes, tab_team = st.tabs(["Classifica atleti", "Classifica team"])

    with tab_athletes:
        render_athlete_ranking_section()

    with tab_team:
        render_team_ranking_section()
