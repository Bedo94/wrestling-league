import streamlit as st

from src.database import DEFAULT_DB_PATH
from src.db_runtime import (
    DB_ENV_LABELS,
    DB_ENV_LEAGUE_LOCAL,
    DB_ENV_LEAGUE_REMOTE,
    DB_ENV_TEST_LOCAL,
    DB_ENV_TEST_REMOTE,
    DB_MODE_POSTGRES,
    DB_MODE_SQLITE,
    DEFAULT_TEST_DB_PATH,
    STATE_LEAGUE_LOCAL_PATH,
    STATE_LEAGUE_REMOTE_URL,
    STATE_TEST_LOCAL_PATH,
    STATE_TEST_REMOTE_URL,
    bootstrap_database_from_state,
    build_uploaded_sqlite_destination,
    get_active_database_info,
    get_selected_environment_name,
    save_uploaded_sqlite_file,
    set_database_selection,
)
from src.export_service import (
    EXCEL_DOWNLOAD_MIME,
    SQLITE_DOWNLOAD_MIME,
    export_active_database_to_excel_bytes,
    export_active_database_to_sqlite_bytes,
)

ENVIRONMENT_OPTIONS = (
    DB_ENV_LEAGUE_LOCAL,
    DB_ENV_LEAGUE_REMOTE,
    DB_ENV_TEST_LOCAL,
    DB_ENV_TEST_REMOTE,
)


def get_environment_index(environment_name: str) -> int:
    try:
        return ENVIRONMENT_OPTIONS.index(environment_name)
    except ValueError:
        return 0


def is_local_environment(environment_name: str) -> bool:
    return environment_name in {DB_ENV_LEAGUE_LOCAL, DB_ENV_TEST_LOCAL}


def get_environment_sqlite_path(environment_name: str) -> str:
    if environment_name == DB_ENV_TEST_LOCAL:
        return st.session_state.get(
            STATE_TEST_LOCAL_PATH,
            str(DEFAULT_TEST_DB_PATH.resolve()),
        )

    return st.session_state.get(
        STATE_LEAGUE_LOCAL_PATH,
        str(DEFAULT_DB_PATH.resolve()),
    )


def get_environment_postgres_url(environment_name: str) -> str:
    if environment_name == DB_ENV_TEST_REMOTE:
        return st.session_state.get(STATE_TEST_REMOTE_URL, "")

    return st.session_state.get(STATE_LEAGUE_REMOTE_URL, "")


bootstrap_database_from_state()
active_db = get_active_database_info()

st.title("Database")
st.caption("Questa pagina decide quale database usa tutta l'applicazione.")

can_edit_database = bool(st.session_state.get("is_admin", True))
can_download_database = bool(st.session_state.get("is_admin", True))

if not can_edit_database:
    st.info("La modifica del database è riservata agli admin.")

st.markdown("## Database attivo")
st.write(f"Ambiente: **{active_db.get('environment_label', active_db['mode_label'])}**")
st.write(f"Backend: **{active_db['mode_label']}**")
st.code(active_db["database_url_masked"])

if active_db["sqlite_path"]:
    st.caption(f"File SQLite attivo: {active_db['sqlite_path']}")

st.markdown("## Download")

download_db_label = "Scarica database locale compatibile (.db)"
download_db_help = (
    "Se il backend attivo è PostgreSQL, viene generato uno snapshot SQLite "
    "compatibile con la modalità locale dell'app."
)

if active_db["mode"] == DB_MODE_POSTGRES:
    download_db_label = "Scarica snapshot SQLite (.db)"
    download_db_help = (
        "Il backend attivo è PostgreSQL: verrà generato e scaricato "
        "uno snapshot SQLite dei dati correnti."
    )

col_download_db, col_download_excel = st.columns(2)

with col_download_db:
    st.download_button(
        label=download_db_label,
        data=export_active_database_to_sqlite_bytes,
        file_name="wrestling_league.db",
        mime=SQLITE_DOWNLOAD_MIME,
        help=download_db_help,
        disabled=not can_download_database,
        use_container_width=True,
    )

with col_download_excel:
    st.download_button(
        label="Scarica Excel (.xlsx)",
        data=export_active_database_to_excel_bytes,
        file_name="wrestling_league_export.xlsx",
        mime=EXCEL_DOWNLOAD_MIME,
        help="Esporta tutte le tabelle del database attivo in un file Excel.",
        disabled=not can_download_database,
        use_container_width=True,
    )

if not can_download_database:
    st.caption("Il download del database è riservato agli admin.")

st.markdown("## Configurazione")

selected_environment = st.radio(
    "Scegli l'ambiente",
    options=ENVIRONMENT_OPTIONS,
    index=get_environment_index(get_selected_environment_name()),
    format_func=lambda value: DB_ENV_LABELS[value],
    disabled=not can_edit_database,
)

selected_mode = DB_MODE_SQLITE if is_local_environment(selected_environment) else DB_MODE_POSTGRES
uploaded_sqlite_file = None
sqlite_path = ""
postgres_url = ""

if selected_mode == DB_MODE_SQLITE:
    default_path = (
        DEFAULT_TEST_DB_PATH.resolve()
        if selected_environment == DB_ENV_TEST_LOCAL
        else DEFAULT_DB_PATH.resolve()
    )

    st.markdown("### SQLite locale")

    if selected_environment == DB_ENV_TEST_LOCAL:
        st.info(
            f"Ambiente di test locale. Path di default: {default_path} "
            "(se il file non esiste, verrà creato automaticamente)."
        )
    else:
        st.info(
            f"Ambiente ufficiale locale. Path di default: {default_path} "
            "(se il file non esiste, verrà creato automaticamente)."
        )

    sqlite_path = st.text_input(
        "Percorso file .db",
        value=get_environment_sqlite_path(selected_environment),
        disabled=not can_edit_database,
        help=(
            "Puoi incollare anche un path con virgolette o spazi esterni: "
            "l'app li ripulisce automaticamente."
        ),
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

    if selected_environment == DB_ENV_TEST_REMOTE:
        st.info("Ambiente remoto di test.")
    else:
        st.info("Ambiente remoto ufficiale.")

    postgres_url = st.text_input(
        "DATABASE_URL PostgreSQL",
        value=get_environment_postgres_url(selected_environment),
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
            environment_name=selected_environment,
        )

        st.success("Configurazione database aggiornata.")
        st.rerun()

    except Exception as exc:
        st.error(f"Errore durante la configurazione del database: {exc}")