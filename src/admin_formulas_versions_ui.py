from __future__ import annotations

import pandas as pd
import streamlit as st

from src.admin_formulas_shared import (
    formula_draft_differs_from_active,
    get_formula_draft_config,
    load_formula_draft_config,
)
from src.db_runtime import DB_ENV_LABELS, get_selected_environment_name
from src.formula_config_service import (
    build_formula_config_preview_rows,
    create_formula_revision,
    get_active_formula_revision,
    get_formula_revision_config,
    list_formula_revisions,
)

FORMULA_REVISION_FLASH_KEY = "admin_formulas_revision_flash"
FORMULA_REVISION_PICKER_KEY = "admin_formulas_revision_picker"
FORMULA_LABEL_INPUT_KEY = "admin_formulas_label_input"
FORMULA_PENDING_REVISION_PICKER_KEY = "admin_formulas_pending_revision_picker"
FORMULA_PENDING_LABEL_INPUT_KEY = "admin_formulas_pending_label_input"


def _set_formula_revision_flash(level: str, message: str) -> None:
    st.session_state[FORMULA_REVISION_FLASH_KEY] = {
        "level": level,
        "message": message,
    }


def render_formula_revision_flash() -> None:
    flash = st.session_state.pop(FORMULA_REVISION_FLASH_KEY, None)
    if not flash:
        return

    level = flash.get("level", "info")
    message = flash.get("message", "")

    if level == "success":
        st.success(message)
    elif level == "warning":
        st.warning(message)
    elif level == "error":
        st.error(message)
    else:
        st.info(message)


def _get_revision_label_value(revision: object) -> str:
    label = getattr(revision, "label", "") or ""
    if label.strip():
        return label.strip()
    return f"Rev {getattr(revision, 'revision_number', '?')}"


def _build_revision_option_label(revision: object) -> str:
    active_suffix = " [attiva]" if getattr(revision, "is_active", False) else ""
    label = _get_revision_label_value(revision)
    created_at = getattr(revision, "created_at", None)
    created_at_text = str(created_at) if created_at is not None else ""
    return f"Rev {revision.revision_number} - {label}{active_suffix} - {created_at_text}"


def _build_revision_rows(revisions: list[object]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for revision in revisions:
        rows.append(
            {
                "Rev": str(revision.revision_number),
                "Stato": "Attiva" if revision.is_active else "",
                "Label": revision.label or "",
                "Nota": revision.note or "",
                "Creata il": str(revision.created_at or ""),
                "Origine": (
                    f"Rev {revision.source_revision_id}"
                    if revision.source_revision_id is not None
                    else ""
                ),
            }
        )
    return rows


def _get_revision_picker_key(environment_name: str) -> str:
    return f"{FORMULA_REVISION_PICKER_KEY}__{environment_name}"


def _get_formula_label_input_key(environment_name: str) -> str:
    return f"{FORMULA_LABEL_INPUT_KEY}__{environment_name}"


def _get_pending_revision_picker_key(environment_name: str) -> str:
    return f"{FORMULA_PENDING_REVISION_PICKER_KEY}__{environment_name}"


def _get_pending_label_input_key(environment_name: str) -> str:
    return f"{FORMULA_PENDING_LABEL_INPUT_KEY}__{environment_name}"


def render_formula_versions_header() -> None:
    environment_name = get_selected_environment_name()
    environment_label = DB_ENV_LABELS.get(environment_name, environment_name)
    active_revision = get_active_formula_revision(environment_name)

    header_col1, header_col2, header_col3 = st.columns([3, 2, 1])

    with header_col1:
        if active_revision is None:
            st.caption(f"Ambiente: {environment_label} | Revisione attiva: default")
        else:
            st.caption(
                f"Ambiente: {environment_label} | "
                f"Revisione attiva: rev {active_revision.revision_number} - "
                f"{_get_revision_label_value(active_revision)}"
            )

    with header_col2:
        if formula_draft_differs_from_active():
            st.caption("Bozza diversa dalla revisione attiva")
        else:
            st.caption("Bozza allineata alla revisione attiva")

    with header_col3:
        if st.button("Gestisci versioni", use_container_width=True):
            _render_formula_versions_dialog()


@st.dialog("Gestisci versioni", width="large")
def _render_formula_versions_dialog() -> None:
    environment_name = get_selected_environment_name()
    environment_label = DB_ENV_LABELS.get(environment_name, environment_name)
    active_revision = get_active_formula_revision(environment_name)
    revisions = list_formula_revisions(environment_name=environment_name)
    revisions_by_id = {revision.id: revision for revision in revisions}
    revision_picker_key = _get_revision_picker_key(environment_name)
    formula_label_input_key = _get_formula_label_input_key(environment_name)
    pending_revision_picker_key = _get_pending_revision_picker_key(environment_name)
    pending_label_input_key = _get_pending_label_input_key(environment_name)

    pending_revision_picker_value = st.session_state.pop(
        pending_revision_picker_key,
        None,
    )
    if pending_revision_picker_value is not None:
        st.session_state[revision_picker_key] = pending_revision_picker_value

    pending_label_input_value = st.session_state.pop(
        pending_label_input_key,
        None,
    )
    if pending_label_input_value is not None:
        st.session_state[formula_label_input_key] = pending_label_input_value

    st.caption(f"Ambiente formule: {environment_label} (`{environment_name}`)")

    if revisions and revision_picker_key not in st.session_state:
        st.session_state[revision_picker_key] = (
            active_revision.id if active_revision is not None else revisions[0].id
        )

    if formula_label_input_key not in st.session_state:
        st.session_state[formula_label_input_key] = ""

    draft_config = get_formula_draft_config()
    selected_revision_id = None
    selected_config: dict[str, dict[str, object]] | None = None

    tab_draft, tab_revisions = st.tabs(
        ["Versiona bozza corrente", "Carica revisioni"]
    )

    with tab_draft:
        if active_revision is None:
            st.caption("Revisione attiva attuale: default")
        else:
            st.caption(
                "Revisione attiva attuale: "
                f"rev {active_revision.revision_number} - {_get_revision_label_value(active_revision)}"
            )

        if formula_draft_differs_from_active():
            st.warning(
                "La bozza corrente differisce dalla revisione attiva. "
                "Puoi continuare a fare prove sulle anteprime e versionare solo quando sei soddisfatto."
            )
        else:
            st.info(
                "La bozza corrente e allineata alla revisione attiva. "
                "Se versioni ora, creerai una nuova revisione con gli stessi parametri."
            )

        with st.form("formula_versions_dialog_create_form"):
            st.text_input(
                "Label nuova revisione",
                key=formula_label_input_key,
                placeholder="Es. rating stabile aprile",
            )
            create_note = st.text_area(
                "Nota revisione",
                placeholder="Facoltativa",
                height=100,
            )
            create_clicked = st.form_submit_button("Versiona e attiva bozza corrente")

        if create_clicked:
            try:
                selected_label = st.session_state.get(formula_label_input_key, "").strip()
                source_revision_id = active_revision.id if active_revision is not None else None
                created_revision = create_formula_revision(
                    environment_name=environment_name,
                    config=draft_config,
                    label=selected_label or None,
                    note=create_note.strip() or None,
                    source_revision_id=source_revision_id,
                    activate=True,
                )
                st.session_state[pending_revision_picker_key] = created_revision.id
                st.session_state[pending_label_input_key] = ""
                _set_formula_revision_flash(
                    "success",
                    f"Creata e attivata la revisione {created_revision.revision_number}.",
                )
                st.rerun()
            except Exception as exc:
                st.error(f"Errore durante la creazione della revisione: {exc}")

        st.caption("Anteprima parametri attualmente in bozza")
        st.dataframe(
            pd.DataFrame(build_formula_config_preview_rows(draft_config)),
            use_container_width=True,
            hide_index=True,
            height=260,
        )

    with tab_revisions:
        if revisions:
            selected_revision_id = st.selectbox(
                "Revisioni disponibili",
                options=[revision.id for revision in revisions],
                format_func=lambda revision_id: _build_revision_option_label(
                    revisions_by_id[revision_id]
                ),
                key=revision_picker_key,
            )
            selected_config = get_formula_revision_config(selected_revision_id)
        else:
            st.info("Nessuna revisione salvata per questo ambiente.")

        if revisions:
            st.dataframe(
                pd.DataFrame(_build_revision_rows(revisions)),
                use_container_width=True,
                hide_index=True,
            )

        if selected_revision_id is not None:
            selected_revision = revisions_by_id[selected_revision_id]
            st.caption(
                "Revisione selezionata: "
                f"rev {selected_revision.revision_number} - {_get_revision_label_value(selected_revision)}"
            )
            if selected_revision.note:
                st.caption(f"Nota: {selected_revision.note}")

        if selected_config is not None:
            st.caption("Anteprima parametri della revisione selezionata")
            st.dataframe(
                pd.DataFrame(build_formula_config_preview_rows(selected_config)),
                use_container_width=True,
                hide_index=True,
                height=260,
            )

        if st.button(
            "Carica nella bozza",
            use_container_width=True,
            disabled=selected_config is None,
        ):
            assert selected_config is not None
            load_formula_draft_config(selected_config)
            st.session_state[pending_label_input_key] = ""
            _set_formula_revision_flash(
                "success",
                "Revisione caricata nella bozza corrente.",
            )
            st.rerun()
