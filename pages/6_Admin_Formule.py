import streamlit as st

from src.admin_formulas_ui import (
    render_level_evaluation_tab,
    render_matchmaking_tab,
    render_rating_tab,
    render_scoring_tab,
    render_team_ranking_tab,
)
from src.db_runtime import bootstrap_database_from_state
from src.formula_config_service import load_config

bootstrap_database_from_state()
load_config()

st.title("Amministrazione formule")
st.markdown(
    """
    In questa pagina puoi personalizzare i parametri utilizzati per le formule di rating,
    matchmaking, scoring, classifica team e valutazione livello.

    Ogni formula è separata in una tab dedicata, con i suoi parametri, le sue spiegazioni
    e le sue azioni di salvataggio, ricalcolo o ripristino.
    """
)

tab_rating, tab_matchmaking, tab_scoring, tab_team, tab_level = st.tabs(
    ["Rating", "Matchmaking", "Scoring", "Classifica team", "Livello consigliato"]
)

with tab_rating:
    render_rating_tab()

with tab_matchmaking:
    render_matchmaking_tab()

with tab_scoring:
    render_scoring_tab()

with tab_team:
    render_team_ranking_tab()

with tab_level:
    render_level_evaluation_tab()