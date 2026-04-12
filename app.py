from pathlib import Path

import streamlit as st

from src.db_runtime import (
    DB_MODE_POSTGRES,
    get_active_database_info,
)

st.set_page_config(
    page_title="Wrestling League",
    page_icon="🤼",
    layout="wide",
)

active_db = get_active_database_info()

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

st.success(
    f"Ambiente attivo: {active_db.get('environment_label', active_db['mode_label'])}"
)
st.caption(f"Backend: {active_db['mode_label']}")

if active_db["mode"] == DB_MODE_POSTGRES:
    st.caption(active_db["database_url_masked"])
else:
    db_path = Path(active_db["sqlite_path"])
    if db_path.exists():
        st.success(f"Database trovato: {db_path}")
    else:
        st.warning(f"Database non ancora creato: {db_path}")

st.caption("Puoi cambiare il database dalla pagina 'Database'.")

st.markdown("## Step attuale")
st.info("Step attuale: scoring e preparazione classifiche")
