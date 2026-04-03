import streamlit as st

from src.admin_formulas_ui import (
    render_classification_tab,
    render_level_evaluation_tab,
    render_matchmaking_tab,
    render_rating_tab,
    render_scoring_tab,
)
from src.db_runtime import bootstrap_database_from_state
from src.formula_config_service import load_config

bootstrap_database_from_state()
load_config()

st.title("Amministrazione formule")
st.markdown(
    """
    In questa pagina puoi personalizzare i parametri utilizzati per le formule di rating,
    matchmaking, scoring, classifica e valutazione livello.

    Ogni formula è separata in una tab dedicata, con spiegazioni, parametri e azioni
    di salvataggio o ripristino.
    """
)

tab_rating, tab_matchmaking, tab_scoring, tab_classification, tab_level = st.tabs(
    ["Rating", "Matchmaking", "Scoring", "Classifica", "Livello consigliato"]
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