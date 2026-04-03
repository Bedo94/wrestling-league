from src.db_runtime import bootstrap_database_from_state
from src.rankings_ui import render_rankings_panel
import streamlit as st

bootstrap_database_from_state()

st.title("Classifiche")

st.markdown(
    """
    Questa pagina mostra la classifica degli atleti e, opzionalmente, anche quella dei team.

    I filtri servono solo a restringere il dataset visualizzato.
    I metodi di classifica per atleti e team si scelgono separatamente sopra le rispettive tabelle.
    """
)

render_rankings_panel(
    state_prefix="rankings_page",
    title="Classifica atleti",
    show_filters_expanded=False,
    recompute_before_render=True,
)