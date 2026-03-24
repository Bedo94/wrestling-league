from pathlib import Path

import streamlit as st

from src.database import DB_PATH

st.set_page_config(
    page_title="Wrestling League",
    page_icon="🤼",
    layout="wide",
)

st.title("Wrestling League Manager")
st.subheader("Base iniziale del progetto")

st.markdown(
    """
Questa applicazione servirà a gestire:

- atleti
- eventi/giornate
- incontri
- punteggi
- classifiche
- accoppiamenti bilanciati
"""
)

st.markdown("## Stato progetto")

if Path(DB_PATH).exists():
    st.success(f"Database trovato: {DB_PATH}")
else:
    st.warning("Database non ancora creato.")

st.markdown("## Step attuale")
st.info("Step 1: fondamenta dell'applicazione")