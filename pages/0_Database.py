import streamlit as st

from src.database import DEFAULT_DB_PATH
from src.db_runtime import (
    DB_MODE_LABELS,
    DB_MODE_OPTIONS,
    DB_MODE_POSTGRES,
    DB_MODE_SQLITE,
    bootstrap_database_from_state,
    build_uploaded_sqlite_destination,
    get_active_database_info,
    get_mode_index,
    get_selected_mode,
    get_selected_postgres_url,
    get_selected_sqlite_path,
    save_uploaded_sqlite_file,
    set_database_selection,
)

bootstrap_database_from_state()
active_db = get_active_database_info()

st.title("Database")
st.caption("Questa pagina decide quale database usa tutta l'applicazione.")

can_edit_database = bool(st.session_state.get("is_admin", True))

if not can_edit_database:
    st.info("La modifica del database è riservata agli admin.")

st.markdown("## Database attivo")
st.write(f"Tipo: **{active_db['mode_label']}**")
st.code(active_db["database_url_masked"])

if active_db["sqlite_path"]:
    st.caption(f"File SQLite attivo: {active_db['sqlite_path']}")

st.markdown("## Configurazione")

selected_mode = st.radio(
    "Scegli il backend",
    options=DB_MODE_OPTIONS,
    index=get_mode_index(get_selected_mode()),
    format_func=lambda value: DB_MODE_LABELS[value],
    disabled=not can_edit_database,
)

sqlite_path = get_selected_sqlite_path()
postgres_url = get_selected_postgres_url()
uploaded_sqlite_file = None

if selected_mode == DB_MODE_SQLITE:
    st.markdown("### SQLite locale")
    st.info(
        f"Path di default: {DEFAULT_DB_PATH.resolve()} "
        "(se il file non esiste, verrà creato automaticamente)."
    )

    sqlite_path = st.text_input(
        "Percorso file .db",
        value=get_selected_sqlite_path(),
        disabled=not can_edit_database,
        help="Puoi incollare anche un path con virgolette o spazi esterni: l'app li ripulisce automaticamente. Se lasci vuoto, viene usato league.db.",
    )

    uploaded_sqlite_file = st.file_uploader(
        "Oppure scegli un file .db dal computer",
        type=["db", "sqlite", "sqlite3"],
        accept_multiple_files=False,
        disabled=not can_edit_database,
        help="Alla conferma, il file verrà copiato dentro data/uploaded_dbs e poi attivato.",
    )

    if uploaded_sqlite_file is not None:
        preview_path = build_uploaded_sqlite_destination(uploaded_sqlite_file.name)
        st.caption(f"Alla conferma, il file verrà salvato in: {preview_path}")

else:
    st.markdown("### PostgreSQL remoto")
    postgres_url = st.text_input(
        "DATABASE_URL PostgreSQL",
        value=get_selected_postgres_url(),
        type="password",
        disabled=not can_edit_database,
        help="Esempio: postgresql+psycopg://user:password@host:5432/dbname",
    )

if st.button("Applica configurazione", use_container_width=True, disabled=not can_edit_database):
    try:
        effective_sqlite_path = sqlite_path

        if selected_mode == DB_MODE_SQLITE and uploaded_sqlite_file is not None:
            saved_path = save_uploaded_sqlite_file(uploaded_sqlite_file)
            effective_sqlite_path = str(saved_path)

        set_database_selection(
            mode=selected_mode,
            sqlite_path=effective_sqlite_path,
            postgres_url=postgres_url,
        )

        st.success("Configurazione database aggiornata.")
        st.rerun()

    except Exception as exc:
        st.error(f"Errore durante la configurazione del database: {exc}")