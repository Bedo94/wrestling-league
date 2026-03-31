from datetime import datetime, timezone

import pandas as pd
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
    DB_SYNC_DIRECTION_LABELS,
    DB_SYNC_DIRECTION_LOCAL_TO_REMOTE,
    DB_SYNC_DIRECTION_REMOTE_TO_LOCAL,
    DEFAULT_TEST_DB_PATH,
    STATE_LEAGUE_LOCAL_PATH,
    STATE_LEAGUE_REMOTE_URL,
    STATE_TEST_LOCAL_PATH,
    STATE_TEST_REMOTE_URL,
    bootstrap_database_from_state,
    build_environment_name,
    build_sync_route,
    build_uploaded_sqlite_destination,
    can_sync_between_environments,
    get_active_database_info,
    get_environment_context,
    get_environment_description,
    get_environment_location,
    get_selected_environment_name,
    get_sync_policy_message,
    get_sync_route_description,
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
from src.sync_service import sync_raw_data

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

CONFLICT_TABLE_ALL = "Tutte"
CONFLICT_REASON_ALL = "Tutti"


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


def build_sync_connection_config(environment_name: str) -> dict:
    if is_local_environment(environment_name):
        return {
            "mode": DB_MODE_SQLITE,
            "sqlite_path": get_environment_sqlite_path(environment_name),
            "postgres_url": "",
        }

    return {
        "mode": DB_MODE_POSTGRES,
        "sqlite_path": "",
        "postgres_url": get_environment_postgres_url(environment_name),
    }


def build_conflicts_dataframe(conflicts: list[dict]) -> pd.DataFrame:
    if not conflicts:
        return pd.DataFrame(
            columns=[
                "table",
                "sync_id",
                "reason",
                "source_updated_at",
                "target_updated_at",
                "source_version_id",
                "target_version_id",
                "details",
            ]
        )

    return pd.DataFrame(conflicts)


bootstrap_database_from_state()
active_db = get_active_database_info()
active_environment = active_db["environment_name"]

st.title("Database")
st.caption("Questa pagina decide quale database usa tutta l'applicazione.")

can_edit_database = bool(st.session_state.get("is_admin", True))
can_download_database = bool(st.session_state.get("is_admin", True))
can_run_sync = bool(st.session_state.get("is_admin", True))

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
    "La sync reale usa la stessa policy."
)

st.markdown("## Sincronizzazione dati grezzi")

st.caption(
    "La prima versione sincronizza solo atleti, eventi e incontri. "
    "Classifiche, rating e matchmaking continuano a essere ricalcolati dai dati grezzi."
)

sync_context = st.radio(
    "Famiglia di ambienti",
    options=(DB_CONTEXT_LEAGUE, DB_CONTEXT_TEST),
    format_func=lambda value: {
        DB_CONTEXT_LEAGUE: "Ufficiale",
        DB_CONTEXT_TEST: "Test",
    }[value],
    horizontal=True,
    disabled=not can_run_sync,
)

sync_direction = st.radio(
    "Direzione",
    options=(
        DB_SYNC_DIRECTION_LOCAL_TO_REMOTE,
        DB_SYNC_DIRECTION_REMOTE_TO_LOCAL,
    ),
    format_func=lambda value: DB_SYNC_DIRECTION_LABELS[value],
    horizontal=True,
    disabled=not can_run_sync,
)

source_environment, target_environment = build_sync_route(
    sync_context,
    sync_direction,
)

st.info(
    f"Percorso selezionato: **{get_sync_route_description(sync_context, sync_direction)}**"
)

if sync_context == DB_CONTEXT_TEST:
    st.warning(
        "Stai sincronizzando un ambiente di test. "
        "Questa sincronizzazione resta confinata tra test_local e test_remote."
    )
else:
    st.success(
        "Stai sincronizzando un ambiente ufficiale. "
        "Questa sincronizzazione resta confinata tra league_local e league_remote."
    )

st.caption(get_sync_policy_message(source_environment, target_environment))

st.markdown("### Filtro opzionale")

sync_only_after_enabled = st.checkbox(
    "Sincronizza solo i record modificati dopo una certa data/ora",
    value=False,
    disabled=not can_run_sync,
)

changed_since_value = None

if sync_only_after_enabled:
    col_date, col_time = st.columns(2)

    with col_date:
        sync_since_date = st.date_input(
            "Data minima",
            value=None,
            format="DD/MM/YYYY",
            disabled=not can_run_sync,
        )

    with col_time:
        sync_since_time = st.time_input(
            "Ora minima",
            value=None,
            disabled=not can_run_sync,
        )

    if sync_since_date is not None:
        if sync_since_time is None:
            sync_since_time = datetime.min.time()

        changed_since_dt = datetime.combine(sync_since_date, sync_since_time)
        changed_since_dt = changed_since_dt.replace(tzinfo=timezone.utc)
        changed_since_value = changed_since_dt.isoformat(timespec="seconds")

        st.caption(f"Filtro applicato: {changed_since_value}")

anteprima_sync_enabled = st.checkbox(
    "Anteprima sync",
    value=True,
    disabled=not can_run_sync,
    help=(
        "Calcola inserimenti, aggiornamenti e conflitti senza salvare nulla "
        "nel database di destinazione."
    ),
)

if "last_sync_result" not in st.session_state:
    st.session_state["last_sync_result"] = None

if st.button(
    "Sincronizza dati grezzi",
    type="primary",
    use_container_width=True,
    disabled=not can_run_sync,
):
    try:
        source_config = build_sync_connection_config(source_environment)
        target_config = build_sync_connection_config(target_environment)

        result = sync_raw_data(
            source_environment=source_environment,
            source_mode=source_config["mode"],
            source_sqlite_path=source_config["sqlite_path"],
            source_postgres_url=source_config["postgres_url"],
            target_environment=target_environment,
            target_mode=target_config["mode"],
            target_sqlite_path=target_config["sqlite_path"],
            target_postgres_url=target_config["postgres_url"],
            changed_since=changed_since_value,
            anteprima_sync=anteprima_sync_enabled,
        )

        st.session_state["last_sync_result"] = result

        if result["ok"]:
            if result.get("anteprima_sync", False):
                st.success(
                    "Anteprima sync completata. Nessuna modifica è stata salvata."
                )
            else:
                st.success("Sincronizzazione completata.")
        else:
            st.error(f"Sincronizzazione terminata con errore: {result['error_message']}")

    except Exception as exc:
        st.session_state["last_sync_result"] = {
            "ok": False,
            "error_message": str(exc),
            "source_environment": source_environment,
            "target_environment": target_environment,
            "changed_since": changed_since_value,
            "anteprima_sync": anteprima_sync_enabled,
            "started_at": "",
            "finished_at": "",
            "summary": {},
            "conflicts": [],
            "log_text": f"SYNC ERROR\n==========\n{exc}",
        }
        st.error(f"Errore durante la sincronizzazione: {exc}")

last_sync_result = st.session_state.get("last_sync_result")

if last_sync_result:
    st.markdown("### Esito ultima sincronizzazione")

    if last_sync_result.get("anteprima_sync", False):
        st.info(
            "Modalità anteprima sync: nessuna modifica è stata salvata "
            "nel database di destinazione."
        )

    st.write(
        f"Sorgente: **{DB_ENV_LABELS.get(last_sync_result['source_environment'], last_sync_result['source_environment'])}**"
    )
    st.write(
        f"Destinazione: **{DB_ENV_LABELS.get(last_sync_result['target_environment'], last_sync_result['target_environment'])}**"
    )

    changed_since_label = last_sync_result.get("changed_since") or "FULL_SYNC"
    st.caption(
        f"Inizio: {last_sync_result.get('started_at', '')} — "
        f"Fine: {last_sync_result.get('finished_at', '')} — "
        f"Filtro: {changed_since_label}"
    )

    summary = last_sync_result.get("summary", {})
    if summary:
        summary_rows = []
        for table_name, values in summary.items():
            summary_rows.append(
                {
                    "Tabella": table_name,
                    "Scansionati": values.get("scanned", 0),
                    "Inseriti": values.get("inserted", 0),
                    "Aggiornati": values.get("updated", 0),
                    "Saltati": values.get("skipped", 0),
                    "Conflitti": values.get("conflicts", 0),
                }
            )

        st.dataframe(
            pd.DataFrame(summary_rows),
            use_container_width=True,
            hide_index=True,
        )

    conflicts = last_sync_result.get("conflicts", [])
    st.markdown("### Conflitti")

    conflicts_df = build_conflicts_dataframe(conflicts)

    if conflicts_df.empty:
        st.success("Nessun conflitto rilevato.")
    else:
        st.warning(f"Conflitti rilevati: {len(conflicts_df)}")

        st.markdown("#### Filtri conflitti")

        available_tables = [CONFLICT_TABLE_ALL] + sorted(
            value for value in conflicts_df["table"].dropna().unique().tolist()
        )
        available_reasons = [CONFLICT_REASON_ALL] + sorted(
            value for value in conflicts_df["reason"].dropna().unique().tolist()
        )

        col_filter_table, col_filter_reason = st.columns(2)

        with col_filter_table:
            selected_conflict_table = st.selectbox(
                "Filtra per tabella",
                options=available_tables,
                index=0,
                key="conflict_filter_table",
            )

        with col_filter_reason:
            selected_conflict_reason = st.selectbox(
                "Filtra per motivo",
                options=available_reasons,
                index=0,
                key="conflict_filter_reason",
            )

        conflict_sync_id_search = st.text_input(
            "Cerca per sync_id",
            value="",
            key="conflict_filter_sync_id",
            help="Mostra solo i conflitti il cui sync_id contiene questo testo.",
        ).strip()

        filtered_conflicts_df = conflicts_df.copy()

        if selected_conflict_table != CONFLICT_TABLE_ALL:
            filtered_conflicts_df = filtered_conflicts_df[
                filtered_conflicts_df["table"] == selected_conflict_table
            ]

        if selected_conflict_reason != CONFLICT_REASON_ALL:
            filtered_conflicts_df = filtered_conflicts_df[
                filtered_conflicts_df["reason"] == selected_conflict_reason
            ]

        if conflict_sync_id_search:
            filtered_conflicts_df = filtered_conflicts_df[
                filtered_conflicts_df["sync_id"]
                .fillna("")
                .str.contains(conflict_sync_id_search, case=False, regex=False)
            ]

        st.caption(
            f"Conflitti mostrati: {len(filtered_conflicts_df)} / {len(conflicts_df)}"
        )

        if filtered_conflicts_df.empty:
            st.info("Nessun conflitto corrisponde ai filtri selezionati.")
        else:
            st.dataframe(
                filtered_conflicts_df,
                use_container_width=True,
                hide_index=True,
            )

    # crea prefisso in base alla modalità (anteprima/effettiva)
    log_prefix = "anteprima_sync" if last_sync_result.get("anteprima_sync", False) else "sync"

    # ricava un timestamp dalla data di avvio sync (ISO) e rimuove caratteri non ammessi nei nomi file
    started_at_iso = last_sync_result.get("started_at", "")
    if started_at_iso:
        # es. 2026-03-31T14:20:03+00:00 -> 20260331_142003
        timestamp_part = started_at_iso.split("+")[0].replace(":", "").replace("-", "").replace("T", "_")
    else:
        # fallback se per qualche motivo non c’è started_at
        timestamp_part = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    # compone il nome del log con prefisso, ambienti e timestamp
    log_file_name = (
        f"{log_prefix}_{last_sync_result['source_environment']}_to_"
        f"{last_sync_result['target_environment']}_{timestamp_part}.txt"
    )

    st.download_button(
        label="Scarica log sincronizzazione (.txt)",
        data=last_sync_result.get("log_text", ""),
        file_name=log_file_name,
        mime="text/plain",
        use_container_width=True,
    )