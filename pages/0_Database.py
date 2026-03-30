import streamlit as st

from src.database import DEFAULT_DB_PATH
from src.db_runtime import (
    DB_CONTEXT_LEAGUE,
    DB_CONTEXT_TEST,
    DB_ENV_LABELS,
    DB_ENV_OPTIONS,
    DB_LOCATION_LOCAL,
    DB_LOCATION_REMOTE,
    DB_MODE_POSTGRES,
    DB_MODE_SQLITE,
    DEFAULT_TEST_DB_PATH,
    STATE_LEAGUE_LOCAL_PATH,
    STATE_LEAGUE_REMOTE_URL,
    STATE_TEST_LOCAL_PATH,
    STATE_TEST_REMOTE_URL,
    bootstrap_database_from_state,
    build_environment_name,
    build_uploaded_sqlite_destination,
    can_sync_between_environments,
    get_active_database_info,
    get_environment_context,
    get_environment_description,
    get_environment_location,
    get_selected_environment_name,
    get_sync_policy_message,
    is_local_environment,
    list_sync_compatible_targets,
    save_uploaded_sqlite_file,
    set_database_selection,
)
from src.export_service import (
    EXCEL_DOWNLOAD_MIME,
    SQLITE_DOWNLOAD_MIME,
    export_active_database_to_excel_bytes,
    export_active_database_to_sqlite_bytes,
)

CONTEXT_OPTIONS = (
    DB_CONTEXT_LEAGUE,
    DB_CONTEXT_TEST,
)

CONTEXT_LABELS = {
    DB_CONTEXT_LEAGUE: "Ufficiale",
    DB_CONTEXT_TEST: "Test",
}

LOCATION_OPTIONS = (
    DB_LOCATION_LOCAL,
    DB_LOCATION_REMOTE,
)

LOCATION_LABELS = {
    DB_LOCATION_LOCAL: "Locale",
    DB_LOCATION_REMOTE: "Remoto",
}


def get_context_index(context: str) -> int:
    try:
        return CONTEXT_OPTIONS.index(context)
    except ValueError:
        return 0


def get_location_index(location: str) -> int:
    try:
        return LOCATION_OPTIONS.index(location)
    except ValueError:
        return 0


def get_environment_sqlite_path(environment_name: str) -> str:
    if environment_name == "test_local":
        return st.session_state.get(
            STATE_TEST_LOCAL_PATH,
            str(DEFAULT_TEST_DB_PATH.resolve()),
        )

    return st.session_state.get(
        STATE_LEAGUE_LOCAL_PATH,
        str(DEFAULT_DB_PATH.resolve()),
    )


def get_environment_postgres_url(environment_name: str) -> str:
    if environment_name == "test_remote":
        return st.session_state.get(STATE_TEST_REMOTE_URL, "")

    return st.session_state.get(STATE_LEAGUE_REMOTE_URL, "")


bootstrap_database_from_state()
active_db = get_active_database_info()
active_environment = active_db["environment_name"]

st.title("Database")
st.caption("Questa pagina decide quale database usa tutta l'applicazione.")

can_edit_database = bool(st.session_state.get("is_admin", True))
can_download_database = bool(st.session_state.get("is_admin", True))

if not can_edit_database:
    st.info("La modifica del database è riservata agli admin.")

st.markdown("## Database attivo")
st.write(f"Ambiente: **{active_db['environment_label']}**")
st.write(f"Backend: **{active_db['mode_label']}**")
st.code(active_db["database_url_masked"])

if active_db["sqlite_path"]:
    st.caption(f"File SQLite attivo: {active_db['sqlite_path']}")

environment_description = active_db.get(
    "environment_description",
    get_environment_description(active_environment),
)

if get_environment_context(active_environment) == DB_CONTEXT_TEST:
    st.warning(
        "Stai lavorando su un ambiente di test. "
        "I dati NON sono ufficiali e non devono essere sincronizzati con gli ambienti league_*."
    )
else:
    st.success(
        "Stai lavorando su un ambiente ufficiale. "
        "Usalo solo per dati reali o copie operative ufficiali."
    )

st.caption(environment_description)

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

selected_context = st.radio(
    "Contesto",
    options=CONTEXT_OPTIONS,
    index=get_context_index(get_environment_context(get_selected_environment_name())),
    format_func=lambda value: CONTEXT_LABELS[value],
    horizontal=True,
    disabled=not can_edit_database,
)

selected_location = st.radio(
    "Posizione",
    options=LOCATION_OPTIONS,
    index=get_location_index(get_environment_location(get_selected_environment_name())),
    format_func=lambda value: LOCATION_LABELS[value],
    horizontal=True,
    disabled=not can_edit_database,
)

selected_environment = build_environment_name(selected_context, selected_location)
selected_mode = DB_MODE_SQLITE if is_local_environment(selected_environment) else DB_MODE_POSTGRES

st.caption(f"Ambiente selezionato: **{DB_ENV_LABELS[selected_environment]}**")
st.caption(get_environment_description(selected_environment))

if selected_context == DB_CONTEXT_TEST:
    st.warning(
        "Ambiente di test: qualsiasi futura sincronizzazione verso ambienti ufficiali "
        "sarà bloccata."
    )
else:
    st.info(
        "Ambiente ufficiale: usa questa modalità solo per dati reali o copie operative ufficiali."
    )

uploaded_sqlite_file = None
sqlite_path = ""
postgres_url = ""

if selected_mode == DB_MODE_SQLITE:
    default_path = (
        DEFAULT_TEST_DB_PATH.resolve()
        if selected_environment == "test_local"
        else DEFAULT_DB_PATH.resolve()
    )

    st.markdown("### SQLite locale")
    st.info(
        f"Path di default: {default_path} "
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

st.markdown("## Regole di sincronizzazione")

compatible_targets = list_sync_compatible_targets(active_environment)

if compatible_targets:
    st.success(
        "Target compatibili con l'ambiente attivo: "
        + ", ".join(DB_ENV_LABELS[target] for target in compatible_targets)
    )
else:
    st.warning("Nessun target di sincronizzazione compatibile con l'ambiente attivo.")

for target_environment in DB_ENV_OPTIONS:
    if target_environment == active_environment:
        continue

    allowed = can_sync_between_environments(active_environment, target_environment)
    icon = "✅" if allowed else "🚫"
    st.write(
        f"{icon} **{DB_ENV_LABELS[target_environment]}** — "
        f"{get_sync_policy_message(active_environment, target_environment)}"
    )

st.caption(
    "Questa regola è centralizzata in src/db_runtime.py. "
    "Quando implementerai la sync vera, dovrà usare la stessa policy."
)