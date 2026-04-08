from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
import streamlit as st

from src.database import DEFAULT_DB_PATH
from src.db_runtime import (
    DB_CONTEXT_LEAGUE,
    DB_LOCATION_LOCAL,
    DB_LOCATION_REMOTE,
    DB_MODE_POSTGRES,
    DB_MODE_SQLITE,
    DB_SYNC_DIRECTION_LOCAL_TO_REMOTE,
    DB_SYNC_DIRECTION_REMOTE_TO_LOCAL,
    STATE_LEAGUE_LOCAL_PATH,
    build_environment_name,
    build_uploaded_sqlite_destination,
    get_active_database_info,
    get_configured_remote_databases,
    get_environment_location,
    get_selected_remote_database_description,
    get_selected_remote_database_key,
    get_selected_remote_database_label,
    get_selected_remote_database_url,
    sanitize_remote_database_key,
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

LOCATION_OPTIONS = (
    DB_LOCATION_LOCAL,
    DB_LOCATION_REMOTE,
)

LOCATION_LABELS = {
    DB_LOCATION_LOCAL: "Locale",
    DB_LOCATION_REMOTE: "Remoto",
}

SYNC_DIRECTION_LABELS = {
    DB_SYNC_DIRECTION_LOCAL_TO_REMOTE: "Locale → Remoto",
    DB_SYNC_DIRECTION_REMOTE_TO_LOCAL: "Remoto → Locale",
}

LEAGUE_LOCAL_ENVIRONMENT = build_environment_name(
    DB_CONTEXT_LEAGUE,
    DB_LOCATION_LOCAL,
)
LEAGUE_REMOTE_ENVIRONMENT = build_environment_name(
    DB_CONTEXT_LEAGUE,
    DB_LOCATION_REMOTE,
)

LAST_SYNC_RESULT_KEY = "last_sync_result"
CONFLICT_TABLE_ALL = "Tutte"
CONFLICT_REASON_ALL = "Tutti"
REMOTE_OPTION_MANUAL = "__manual__"


def get_location_index(location: str) -> int:
    try:
        return LOCATION_OPTIONS.index(location)
    except ValueError:
        return 0


def get_league_local_sqlite_path() -> str:
    return st.session_state.get(
        STATE_LEAGUE_LOCAL_PATH,
        str(DEFAULT_DB_PATH.resolve()),
    )


def get_active_database_locator(active_db: dict) -> str:
    active_location = get_environment_location(active_db["environment_name"])

    if active_location == DB_LOCATION_LOCAL:
        return active_db.get("sqlite_path") or get_league_local_sqlite_path()

    return active_db.get("postgres_url") or get_selected_remote_database_url()


def build_connection_config(environment_name: str) -> dict[str, str]:
    location = get_environment_location(environment_name)

    if location == DB_LOCATION_LOCAL:
        return {
            "mode": DB_MODE_SQLITE,
            "sqlite_path": get_league_local_sqlite_path(),
            "postgres_url": "",
        }

    return {
        "mode": DB_MODE_POSTGRES,
        "sqlite_path": "",
        "postgres_url": get_selected_remote_database_url(),
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


def build_remote_toml_snippet(
    *,
    label: str,
    description: str,
    url: str,
) -> str:
    clean_label = (label or "").replace('"', '\\"').strip()
    clean_description = (description or "").replace('"', '\\"').strip()
    clean_url = (url or "").replace('"', '\\"').strip()

    generated_key = sanitize_remote_database_key(clean_label)

    if not generated_key or not clean_label or not clean_url:
        return ""

    return (
        f'[remote_databases.{generated_key}]\n'
        f'label = "{clean_label}"\n'
        f'description = "{clean_description}"\n'
        f'url = "{clean_url}"'
    )


def render_active_database_summary(active_db: dict) -> None:
    active_location = get_environment_location(active_db["environment_name"])
    active_location_label = LOCATION_LABELS.get(active_location, "Sconosciuto")

    st.write(f"**Posizione attiva:** {active_location_label}")
    st.write(f"**Backend attivo:** {active_db['mode_label']}")

    if active_location == DB_LOCATION_REMOTE:
        remote_label = active_db.get("remote_label") or get_selected_remote_database_label()
        remote_description = (
            active_db.get("remote_description")
            or get_selected_remote_database_description()
        )

        if remote_label:
            st.write(f"**Remoto attivo:** {remote_label}")
        if remote_description:
            st.caption(remote_description)

    st.write("**Percorso / URL attivo:**")
    st.code(get_active_database_locator(active_db))


def render_database_usage_tab(
    *,
    active_db: dict,
) -> None:
    st.subheader("Database attualmente in uso")
    render_active_database_summary(active_db)


def render_remote_database_selector(*, can_edit_database: bool) -> None:
    configured_remotes = get_configured_remote_databases()
    configured_keys = list(configured_remotes.keys())
    selected_remote_key = get_selected_remote_database_key()

    if configured_keys:
        remote_options = configured_keys + [REMOTE_OPTION_MANUAL]
        default_option = (
            selected_remote_key
            if selected_remote_key in configured_remotes
            else REMOTE_OPTION_MANUAL
        )
        default_index = remote_options.index(default_option)

        chosen_remote_option = st.selectbox(
            "Database remoto configurato",
            options=remote_options,
            index=default_index,
            format_func=lambda value: (
                "Personalizzato"
                if value == REMOTE_OPTION_MANUAL
                else configured_remotes[value]["label"]
            ),
            disabled=not can_edit_database,
        )
    else:
        chosen_remote_option = REMOTE_OPTION_MANUAL
        st.info(
            "Nessun remoto configurato in secrets.toml. "
            "Puoi usare la modalità personalizzata."
        )

    if chosen_remote_option != REMOTE_OPTION_MANUAL:
        selected_entry = configured_remotes[chosen_remote_option]

        st.write(f"**Nome:** {selected_entry['label']}")
        if selected_entry["description"]:
            st.caption(selected_entry["description"])

        st.write("**URL:**")
        st.code(selected_entry["url"])
        st.caption(
            "Se il database remoto è vuoto, l'app proverà a inizializzare automaticamente lo schema."
        )

        if st.button(
            "Attiva database remoto selezionato",
            use_container_width=True,
            disabled=not can_edit_database,
            key="activate_configured_remote_db",
        ):
            try:
                set_database_selection(
                    mode=DB_MODE_POSTGRES,
                    sqlite_path="",
                    postgres_url="",
                    environment_name=LEAGUE_REMOTE_ENVIRONMENT,
                    remote_key=selected_entry["key"],
                )
                st.success("Database remoto attivato.")
                st.rerun()

            except Exception as exc:
                st.error(f"Errore durante l'attivazione del database remoto: {exc}")

        return

    st.caption(
        "Modalità personalizzata: attiva subito un remoto non presente nel catalogo. "
        "Per renderlo permanente copia poi lo snippet in secrets.toml."
    )

    manual_default_label = get_selected_remote_database_label()
    manual_default_description = get_selected_remote_database_description()
    manual_default_url = get_selected_remote_database_url()

    is_current_remote_custom = (
        bool(get_selected_remote_database_url())
        and get_selected_remote_database_key() not in configured_remotes
    )

    manual_label = st.text_input(
        "Nome remoto",
        value=manual_default_label if is_current_remote_custom else "",
        disabled=not can_edit_database,
        key="custom_remote_label",
    )

    manual_description = st.text_area(
        "Descrizione",
        value=manual_default_description if is_current_remote_custom else "",
        disabled=not can_edit_database,
        key="custom_remote_description",
    )

    manual_url = st.text_input(
        "DATABASE_URL PostgreSQL",
        value=manual_default_url if is_current_remote_custom else "",
        type="password",
        disabled=not can_edit_database,
        help=(
            "Puoi incollare direttamente anche la URL generata da Neon "
            "(es. postgresql://...). L'app la adatta automaticamente al driver richiesto."
        ),
        key="custom_remote_url",
    )

    st.caption(
        "Puoi incollare direttamente la URL PostgreSQL fornita da Neon o da altri provider. "
        "Se necessario, l'app aggiunge automaticamente il driver compatibile."
    )
    st.caption(
        "Se il database remoto è vuoto, l'app proverà a inizializzare automaticamente lo schema."
    )

    toml_snippet = build_remote_toml_snippet(
        label=manual_label,
        description=manual_description,
        url=manual_url,
    )

    if toml_snippet:
        st.write("**Snippet da copiare in `secrets.toml`**")
        st.code(toml_snippet, language="toml")

    if st.button(
        "Attiva database remoto personalizzato",
        use_container_width=True,
        disabled=not can_edit_database,
        key="activate_custom_remote_db",
    ):
        try:
            generated_remote_key = sanitize_remote_database_key(manual_label)

            if not generated_remote_key:
                st.warning("Inserisci un nome remoto valido.")
                return

            if not manual_label.strip():
                st.warning("Inserisci un nome leggibile per il remoto.")
                return

            if not manual_url.strip():
                st.warning("Inserisci una DATABASE_URL valida.")
                return

            set_database_selection(
                mode=DB_MODE_POSTGRES,
                sqlite_path="",
                postgres_url=manual_url,
                environment_name=LEAGUE_REMOTE_ENVIRONMENT,
                remote_key=generated_remote_key,
                remote_label=manual_label,
                remote_description=manual_description,
            )
            st.success("Database remoto personalizzato attivato.")
            st.rerun()

        except Exception as exc:
            st.error(f"Errore durante l'attivazione del database remoto: {exc}")


def render_import_export_tab(
    *,
    active_db: dict,
    can_download_database: bool,
    can_edit_database: bool,
) -> None:
    st.subheader("Seleziona e attiva il database di lavoro")

    active_location = get_environment_location(active_db["environment_name"])

    selected_location = st.radio(
        "Tipo database",
        options=LOCATION_OPTIONS,
        index=get_location_index(active_location),
        format_func=lambda value: LOCATION_LABELS[value],
        horizontal=True,
        disabled=not can_edit_database,
    )

    if selected_location == DB_LOCATION_LOCAL:
        st.caption(
            "Lavora su un file SQLite locale. "
            "Puoi indicare un path esistente oppure importare un file .db."
        )

        sqlite_path = st.text_input(
            "Percorso file .db",
            value=get_league_local_sqlite_path(),
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
        )

        if uploaded_sqlite_file is not None:
            preview_path = build_uploaded_sqlite_destination(uploaded_sqlite_file.name)
            st.caption(f"Il file verrà salvato in: {preview_path}")

        if st.button(
            "Attiva database locale",
            use_container_width=True,
            disabled=not can_edit_database,
        ):
            try:
                effective_sqlite_path = sqlite_path

                if uploaded_sqlite_file is not None:
                    saved_path = save_uploaded_sqlite_file(uploaded_sqlite_file)
                    effective_sqlite_path = str(saved_path)

                set_database_selection(
                    mode=DB_MODE_SQLITE,
                    sqlite_path=effective_sqlite_path,
                    postgres_url="",
                    environment_name=LEAGUE_LOCAL_ENVIRONMENT,
                )

                st.success("Database locale attivato.")
                st.rerun()

            except Exception as exc:
                st.error(f"Errore durante l'attivazione del database locale: {exc}")

    else:
        render_remote_database_selector(
            can_edit_database=can_edit_database,
        )

    st.divider()
    st.subheader("Esporta il database attivo")

    download_db_label = "Scarica database SQLite (.db)"
    download_db_help = (
        "Se il database attivo è remoto, verrà generato uno snapshot SQLite compatibile."
    )

    if active_db["mode"] == DB_MODE_POSTGRES:
        download_db_label = "Scarica snapshot SQLite (.db)"

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


def render_last_sync_result() -> None:
    last_sync_result = st.session_state.get(LAST_SYNC_RESULT_KEY)
    if not last_sync_result:
        return

    st.divider()
    st.subheader("Esito ultima sincronizzazione")

    if not last_sync_result.get("ok", False):
        st.error(
            f"Sincronizzazione terminata con errore: "
            f"{last_sync_result.get('error_message', '')}"
        )
    elif last_sync_result.get("anteprima_sync", False):
        st.success("Anteprima completata. Nessuna modifica è stata salvata.")
    else:
        st.success("Sincronizzazione completata.")

    source_environment = last_sync_result.get("source_environment", "")
    target_environment = last_sync_result.get("target_environment", "")

    source_label = LOCATION_LABELS.get(
        get_environment_location(source_environment),
        source_environment,
    )
    target_label = LOCATION_LABELS.get(
        get_environment_location(target_environment),
        target_environment,
    )

    st.write(f"**Sorgente:** {source_label}")
    st.write(f"**Destinazione:** {target_label}")

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
    conflicts_df = build_conflicts_dataframe(conflicts)

    st.markdown("#### Conflitti")

    if conflicts_df.empty:
        st.success("Nessun conflitto rilevato.")
    else:
        st.warning(f"Conflitti rilevati: {len(conflicts_df)}")

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
                key="db_conflict_filter_table",
            )

        with col_filter_reason:
            selected_conflict_reason = st.selectbox(
                "Filtra per motivo",
                options=available_reasons,
                index=0,
                key="db_conflict_filter_reason",
            )

        conflict_sync_id_search = st.text_input(
            "Cerca per sync_id",
            value="",
            key="db_conflict_filter_sync_id",
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

    log_prefix = (
        "anteprima_sync"
        if last_sync_result.get("anteprima_sync", False)
        else "sync"
    )

    started_at_iso = last_sync_result.get("started_at", "")
    if started_at_iso:
        timestamp_part = (
            started_at_iso.split("+")[0]
            .replace(":", "")
            .replace("-", "")
            .replace("T", "_")
        )
    else:
        timestamp_part = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    log_file_name = (
        f"{log_prefix}_{source_environment}_to_{target_environment}_{timestamp_part}.txt"
    )

    st.download_button(
        label="Scarica log sincronizzazione (.txt)",
        data=last_sync_result.get("log_text", ""),
        file_name=log_file_name,
        mime="text/plain",
        use_container_width=True,
    )


def render_sync_tab(*, can_run_sync: bool) -> None:
    st.subheader("Sincronizzazione dati grezzi")

    sync_direction = st.radio(
        "Direzione",
        options=(
            DB_SYNC_DIRECTION_LOCAL_TO_REMOTE,
            DB_SYNC_DIRECTION_REMOTE_TO_LOCAL,
        ),
        format_func=lambda value: SYNC_DIRECTION_LABELS[value],
        horizontal=True,
        disabled=not can_run_sync,
    )

    if sync_direction == DB_SYNC_DIRECTION_LOCAL_TO_REMOTE:
        source_environment = LEAGUE_LOCAL_ENVIRONMENT
        target_environment = LEAGUE_REMOTE_ENVIRONMENT
    else:
        source_environment = LEAGUE_REMOTE_ENVIRONMENT
        target_environment = LEAGUE_LOCAL_ENVIRONMENT

    source_label = LOCATION_LABELS[get_environment_location(source_environment)]
    target_label = LOCATION_LABELS[get_environment_location(target_environment)]

    st.caption(f"Percorso selezionato: {source_label} → {target_label}")

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
        help="Calcola inserimenti, aggiornamenti e conflitti senza salvare nulla.",
    )

    if LAST_SYNC_RESULT_KEY not in st.session_state:
        st.session_state[LAST_SYNC_RESULT_KEY] = None

    if st.button(
        "Esegui sincronizzazione",
        type="primary",
        use_container_width=True,
        disabled=not can_run_sync,
    ):
        try:
            source_config = build_connection_config(source_environment)
            target_config = build_connection_config(target_environment)

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

            st.session_state[LAST_SYNC_RESULT_KEY] = result
            st.rerun()

        except Exception as exc:
            st.session_state[LAST_SYNC_RESULT_KEY] = {
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
            st.rerun()

    render_last_sync_result()


def render_database_page() -> None:
    active_db = get_active_database_info()

    st.title("Database")

    can_edit_database = bool(st.session_state.get("is_admin", True))
    can_download_database = bool(st.session_state.get("is_admin", True))
    can_run_sync = bool(st.session_state.get("is_admin", True))

    if not can_edit_database:
        st.info("Le operazioni sul database sono riservate agli admin.")

    tab_usage, tab_import_export, tab_sync = st.tabs(
        [
            "Database in uso",
            "Import / Export",
            "Sincronizzazione",
        ]
    )

    with tab_usage:
        render_database_usage_tab(
            active_db=active_db,
        )

    with tab_import_export:
        render_import_export_tab(
            active_db=active_db,
            can_download_database=can_download_database,
            can_edit_database=can_edit_database,
        )

    with tab_sync:
        render_sync_tab(
            can_run_sync=can_run_sync,
        )