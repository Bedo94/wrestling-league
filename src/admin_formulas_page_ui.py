from __future__ import annotations

import streamlit as st

from src.admin_formulas_level_tab import render_level_evaluation_tab
from src.admin_formulas_matchmaking_tab import render_matchmaking_tab
from src.admin_formulas_rankings_tab import render_classification_tab
from src.admin_formulas_rating_tab import render_rating_tab
from src.admin_formulas_scoring_tab import render_scoring_tab


def render_admin_formulas_page() -> None:
    st.title("Formule")

    tab_rating, tab_matchmaking, tab_scoring, tab_classification, tab_level = st.tabs(
        [
            "Rating",
            "Matchmaking",
            "Scoring",
            "Classifica",
            "Livello consigliato",
        ]
    )

    with tab_rating:
        render_rating_tab()

    with tab_matchmaking:
        render_matchmaking_tab()

    with tab_scoring:
        render_scoring_tab()

    with tab_classification:
        render_classification_tab()

    with tab_level:
        render_level_evaluation_tab()