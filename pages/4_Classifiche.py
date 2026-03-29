from src.db_runtime import bootstrap_database_from_state
from src.rankings_ui import render_rankings_panel
import streamlit as st

bootstrap_database_from_state()

st.title("Classifiche")

st.markdown(
    """
    Questa pagina mostra una classifica generale costruita come somma dei punti classifica
    ottenuti da ciascun atleta nei vari incontri.

    Puoi filtrare la vista per:
    - anno
    - evento
    - stile
    - sesso
    - età
    - peso di riferimento
    - stato attivo
    - team
    """
)

render_rankings_panel(
    state_prefix="rankings_page",
    title="Classifica atleti",
    show_filters_expanded=True,
    recompute_before_render=True,
)