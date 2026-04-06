from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Literal

import pandas as pd
import streamlit as st
from st_aggrid import GridOptionsBuilder

from src.aggrid_ui import create_soft_grid_builder, render_soft_aggrid

TableRenderer = Literal["aggrid", "streamlit"]
TableSelectionMode = Literal["single", "multiple"]


def _identity_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    return df.copy()


@dataclass(frozen=True)
class TableSpec:
    name: str
    csv_filename: str | None = None
    caption: str | None = None

    prepare_for_view: Callable[[pd.DataFrame], pd.DataFrame] = _identity_dataframe
    normalize_from_view: Callable[[pd.DataFrame], pd.DataFrame] = _identity_dataframe

    configure_aggrid: Callable[[GridOptionsBuilder], None] | None = None

    streamlit_column_config: dict[str, Any] = field(default_factory=dict)
    streamlit_disabled_columns: list[str] = field(default_factory=list)

    editable: bool = True
    enable_selection: bool = False
    selection_mode: TableSelectionMode = "single"

    enable_column_visibility: bool = False

    always_visible_columns: list[str] = field(default_factory=list)
    hidden_columns: list[str] = field(default_factory=list)
    hidden_by_default_columns: list[str] = field(default_factory=list)
    default_visible_columns: list[str] | None = None

    column_visibility_button_label: str = "☷"
    csv_download_button_label: str = "⭳"

    show_row_index: bool = False
    row_index_column_name: str = "#"

    identity_column: str | None = "ID"

    header_height: int = 33
    floating_filters_height: int = 31
    row_height: int = 31
    min_column_width: int = 84
    max_height: int = 430
    min_height: int = 120


@dataclass(frozen=True)
class TableRenderResult:
    view_df: pd.DataFrame
    edited_df: pd.DataFrame
    selected_rows_df: pd.DataFrame


def _normalize_selected_rows(selected_rows_raw: Any) -> pd.DataFrame:
    if selected_rows_raw is None:
        return pd.DataFrame()

    if isinstance(selected_rows_raw, pd.DataFrame):
        return selected_rows_raw.copy()

    if isinstance(selected_rows_raw, list):
        if len(selected_rows_raw) == 0:
            return pd.DataFrame()
        return pd.DataFrame(selected_rows_raw).copy()

    return pd.DataFrame()


def _with_row_index(df: pd.DataFrame, *, column_name: str) -> pd.DataFrame:
    indexed_df = df.copy()
    indexed_df.insert(0, column_name, range(1, len(indexed_df) + 1))
    return indexed_df


def _prepare_visible_columns_state(
    *,
    key: str,
    optional_columns: list[str],
    default_optional_columns: list[str],
) -> tuple[str, str]:
    visible_columns_key = f"{key}__visible_columns"
    signature_key = f"{key}__visible_columns_signature"

    current_signature = tuple(optional_columns)
    previous_signature = st.session_state.get(signature_key)
    current_selection = st.session_state.get(
        visible_columns_key,
        default_optional_columns,
    )

    valid_selection = [column for column in current_selection if column in optional_columns]
    if not valid_selection and default_optional_columns:
        valid_selection = list(default_optional_columns)

    if previous_signature != current_signature:
        st.session_state[visible_columns_key] = valid_selection
        st.session_state[signature_key] = current_signature

    if visible_columns_key not in st.session_state:
        st.session_state[visible_columns_key] = list(default_optional_columns)

    return visible_columns_key, signature_key


def _is_internal_column(
    *,
    column_name: str,
    spec: TableSpec,
) -> bool:
    normalized = str(column_name).strip()

    if column_name in spec.hidden_columns:
        return True

    if normalized.startswith("__"):
        return True

    if normalized.startswith("::") and normalized.endswith("::"):
        return True

    return False


def _get_aggrid_hidden_columns(
    *,
    df: pd.DataFrame,
    spec: TableSpec,
) -> list[str]:
    return [
        column_name
        for column_name in df.columns
        if _is_internal_column(column_name=column_name, spec=spec)
    ]


def _get_default_visible_columns(
    *,
    available_columns: list[str],
    spec: TableSpec,
) -> list[str]:
    if spec.default_visible_columns is not None:
        return [
            column_name
            for column_name in spec.default_visible_columns
            if column_name in available_columns
        ]

    hidden_by_default = {
        column_name
        for column_name in spec.hidden_by_default_columns
        if column_name in available_columns
    }

    default_visible_columns = [
        column_name
        for column_name in available_columns
        if column_name not in hidden_by_default
    ]

    if not default_visible_columns:
        return available_columns.copy()

    return default_visible_columns


def _resolve_column_visibility_context(
    *,
    df: pd.DataFrame,
    spec: TableSpec,
) -> tuple[list[str], list[str], list[str], list[str], list[str]]:
    all_columns = list(df.columns)
    hidden_columns = _get_aggrid_hidden_columns(
        df=df,
        spec=spec,
    )
    hidden_columns_set = set(hidden_columns)

    available_columns = [
        column_name
        for column_name in all_columns
        if column_name not in hidden_columns_set
    ]

    always_visible_columns = [
        column_name
        for column_name in spec.always_visible_columns
        if column_name in available_columns
    ]

    default_visible_columns = _get_default_visible_columns(
        available_columns=available_columns,
        spec=spec,
    )

    optional_columns = [
        column_name
        for column_name in available_columns
        if column_name not in always_visible_columns
    ]

    default_optional_columns = [
        column_name
        for column_name in default_visible_columns
        if column_name in optional_columns
    ]

    return (
        available_columns,
        always_visible_columns,
        optional_columns,
        default_optional_columns,
        hidden_columns,
    )


def _render_column_visibility_controls(
    *,
    key: str,
    optional_columns: list[str],
    default_optional_columns: list[str],
    button_label: str,
) -> None:
    visible_columns_key, _ = _prepare_visible_columns_state(
        key=key,
        optional_columns=optional_columns,
        default_optional_columns=default_optional_columns,
    )

    current_selected_columns = list(
        st.session_state.get(visible_columns_key, default_optional_columns)
    )

    checkbox_keys: dict[str, str] = {}
    for column_name in optional_columns:
        checkbox_key = f"{key}__visible_col__{column_name}"
        checkbox_keys[column_name] = checkbox_key

        if checkbox_key not in st.session_state:
            st.session_state[checkbox_key] = column_name in current_selected_columns

    with st.popover(button_label, use_container_width=True):
        st.caption("Colonne visibili")

        if not optional_columns:
            st.caption("Nessuna colonna configurabile.")
            return

        checkbox_columns = st.columns(2)

        for idx, column_name in enumerate(optional_columns):
            with checkbox_columns[idx % 2]:
                st.checkbox(
                    column_name,
                    key=checkbox_keys[column_name],
                )

    selected_optional_columns = [
        column_name
        for column_name in optional_columns
        if st.session_state.get(checkbox_keys[column_name], False)
    ]

    st.session_state[visible_columns_key] = selected_optional_columns


def _get_visible_columns_from_state(
    *,
    df: pd.DataFrame,
    spec: TableSpec,
    key: str,
) -> list[str]:
    (
        available_columns,
        always_visible_columns,
        optional_columns,
        default_optional_columns,
        _hidden_columns,
    ) = _resolve_column_visibility_context(
        df=df,
        spec=spec,
    )

    if not spec.enable_column_visibility:
        return available_columns

    if not optional_columns:
        return available_columns

    visible_columns_key, _ = _prepare_visible_columns_state(
        key=key,
        optional_columns=optional_columns,
        default_optional_columns=default_optional_columns,
    )

    selected_optional_columns = list(
        st.session_state.get(visible_columns_key, default_optional_columns)
    )
    selected_optional_columns = [
        column_name
        for column_name in selected_optional_columns
        if column_name in optional_columns
    ]

    visible_columns_set = set(always_visible_columns) | set(selected_optional_columns)

    ordered_visible_columns = [
        column_name
        for column_name in available_columns
        if column_name in visible_columns_set
    ]

    if not ordered_visible_columns and available_columns:
        return available_columns[:1]

    return ordered_visible_columns


def _merge_partial_df_into_full_df(
    *,
    full_df: pd.DataFrame,
    partial_df: pd.DataFrame,
    identity_column: str | None,
) -> pd.DataFrame:
    if set(partial_df.columns) == set(full_df.columns):
        return partial_df.copy()

    if identity_column and identity_column in full_df.columns and identity_column in partial_df.columns:
        merged_df = full_df.copy().set_index(identity_column, drop=False)
        partial_indexed = partial_df.copy().set_index(identity_column, drop=False)

        common_ids = partial_indexed.index.intersection(merged_df.index)
        common_columns = [
            column_name
            for column_name in partial_indexed.columns
            if column_name in merged_df.columns
        ]

        merged_df.loc[common_ids, common_columns] = partial_indexed.loc[
            common_ids,
            common_columns,
        ]

        original_order = full_df[identity_column].tolist()
        return merged_df.loc[original_order].reset_index(drop=True)

    if len(full_df) != len(partial_df):
        return partial_df.copy()

    merged_df = full_df.copy()
    for column_name in partial_df.columns:
        merged_df[column_name] = partial_df[column_name].to_numpy()

    return merged_df


def _estimate_column_base_width(column_def: dict[str, Any]) -> int:
    for key in ("width", "initialWidth", "minWidth"):
        value = column_def.get(key)
        if isinstance(value, (int, float)) and value > 0:
            return int(value)
    return 110


def _apply_aggrid_responsive_column_sizing(
    *,
    grid_options: dict[str, Any],
    visible_columns: list[str],
    hidden_columns: list[str],
) -> dict[str, Any]:
    visible_columns_set = set(visible_columns)
    hidden_columns_set = set(hidden_columns)

    column_defs = grid_options.get("columnDefs", [])
    for column_def in column_defs:
        field_name = column_def.get("field")
        if field_name is None:
            continue

        if field_name in hidden_columns_set or field_name not in visible_columns_set:
            continue

        if column_def.get("pinned"):
            continue

        base_width = _estimate_column_base_width(column_def)
        existing_min_width = column_def.get("minWidth")
        computed_min_width = max(int(base_width * 0.72), 70)

        if not isinstance(existing_min_width, (int, float)):
            column_def["minWidth"] = computed_min_width
        else:
            column_def["minWidth"] = max(int(existing_min_width), 70)

        if "flex" not in column_def:
            column_def["flex"] = max(1, round(base_width / 36))

        column_def.pop("maxWidth", None)
        column_def["suppressSizeToFit"] = False

    default_col_def = grid_options.get("defaultColDef", {})
    default_col_def["resizable"] = True
    grid_options["defaultColDef"] = default_col_def

    return grid_options


def _apply_aggrid_column_visibility(
    *,
    grid_options: dict[str, Any],
    visible_columns: list[str],
    hidden_columns: list[str],
) -> dict[str, Any]:
    visible_columns_set = set(visible_columns)
    hidden_columns_set = set(hidden_columns)

    column_defs = grid_options.get("columnDefs", [])
    for column_def in column_defs:
        field_name = column_def.get("field")
        if field_name is None:
            continue

        if field_name in hidden_columns_set:
            column_def["hide"] = True
            continue

        column_def["hide"] = field_name not in visible_columns_set

    grid_options = _apply_aggrid_responsive_column_sizing(
        grid_options=grid_options,
        visible_columns=visible_columns,
        hidden_columns=hidden_columns,
    )

    return grid_options


def _configure_row_index_column(
    gb: GridOptionsBuilder,
    *,
    column_name: str,
) -> None:
    gb.configure_column(
        column_name,
        headerName=column_name,
        editable=False,
        pinned="left",
        width=54,
        minWidth=48,
        maxWidth=60,
        filter="agNumberColumnFilter",
        type=["numericColumn"],
    )


def _strip_internal_columns(
    *,
    df: pd.DataFrame,
    spec: TableSpec,
) -> pd.DataFrame:
    cleaned_df = df.copy()

    drop_columns: list[str] = []

    if spec.show_row_index and spec.row_index_column_name in cleaned_df.columns:
        drop_columns.append(spec.row_index_column_name)

    drop_columns.extend(
        [
            column_name
            for column_name in cleaned_df.columns
            if _is_internal_column(column_name=column_name, spec=spec)
        ]
    )

    if drop_columns:
        cleaned_df = cleaned_df.drop(columns=list(dict.fromkeys(drop_columns)), errors="ignore")

    return cleaned_df


def _build_export_df(
    *,
    edited_df: pd.DataFrame,
    visible_columns: list[str],
    spec: TableSpec,
) -> pd.DataFrame:
    export_columns = [
        column_name
        for column_name in visible_columns
        if column_name in edited_df.columns and column_name != spec.row_index_column_name
    ]

    if not export_columns:
        return edited_df.copy()

    return edited_df[export_columns].copy()


def render_table_component(
    *,
    df: pd.DataFrame,
    spec: TableSpec,
    renderer: TableRenderer,
    key: str,
) -> TableRenderResult:
    view_df = spec.prepare_for_view(df)

    if spec.show_row_index and spec.row_index_column_name not in view_df.columns:
        view_df = _with_row_index(view_df, column_name=spec.row_index_column_name)

    if renderer == "aggrid":
        toolbar_export_placeholder = None

        if spec.caption or spec.enable_column_visibility or spec.csv_filename:
            left_col, visibility_col, csv_col = st.columns([12, 0.8, 0.8])

            with left_col:
                if spec.caption:
                    st.caption(spec.caption)

            with visibility_col:
                if spec.enable_column_visibility:
                    (
                        _available_columns,
                        _always_visible_columns,
                        optional_columns,
                        default_optional_columns,
                        _hidden_columns,
                    ) = _resolve_column_visibility_context(
                        df=view_df,
                        spec=spec,
                    )

                    if optional_columns:
                        _render_column_visibility_controls(
                            key=key,
                            optional_columns=optional_columns,
                            default_optional_columns=default_optional_columns,
                            button_label=spec.column_visibility_button_label,
                        )

            with csv_col:
                toolbar_export_placeholder = st.empty()

        visible_columns = _get_visible_columns_from_state(
            df=view_df,
            spec=spec,
            key=key,
        )

        hidden_columns = _get_aggrid_hidden_columns(
            df=view_df,
            spec=spec,
        )

        if spec.configure_aggrid is None:
            raise ValueError(f"La tabella '{spec.name}' non ha una configurazione AgGrid.")

        gb = create_soft_grid_builder(
            view_df,
            editable=spec.editable,
            header_height=spec.header_height,
            floating_filters_height=spec.floating_filters_height,
            row_height=spec.row_height,
            min_column_width=spec.min_column_width,
        )

        if spec.show_row_index and spec.row_index_column_name in view_df.columns:
            _configure_row_index_column(
                gb,
                column_name=spec.row_index_column_name,
            )

        if spec.enable_selection:
            gb.configure_grid_options(
                rowSelection=spec.selection_mode,
                rowMultiSelectWithClick=spec.selection_mode == "multiple",
                suppressRowClickSelection=False,
            )

        spec.configure_aggrid(gb)
        grid_options = gb.build()
        grid_options = _apply_aggrid_column_visibility(
            grid_options=grid_options,
            visible_columns=visible_columns,
            hidden_columns=hidden_columns,
        )

        grid_response = render_soft_aggrid(
            view_df,
            grid_options=grid_options,
            key=key,
            csv_filename=None,
            max_height=spec.max_height,
            min_height=spec.min_height,
            header_height=spec.header_height,
            floating_filters_height=spec.floating_filters_height,
            row_height=spec.row_height,
        )

        partial_edited_df = pd.DataFrame(grid_response["data"]).copy()
        edited_df = _merge_partial_df_into_full_df(
            full_df=view_df,
            partial_df=partial_edited_df,
            identity_column=spec.identity_column,
        )
        edited_df = _strip_internal_columns(
            df=edited_df,
            spec=spec,
        )

        selected_rows_df = _normalize_selected_rows(grid_response.get("selected_rows"))
        selected_rows_df = _strip_internal_columns(
            df=selected_rows_df,
            spec=spec,
        )

        export_df = _build_export_df(
            edited_df=edited_df,
            visible_columns=visible_columns,
            spec=spec,
        )

        if toolbar_export_placeholder is not None and spec.csv_filename:
            with toolbar_export_placeholder.container():
                st.download_button(
                    label=spec.csv_download_button_label,
                    data=export_df.to_csv(index=False).encode("utf-8-sig"),
                    file_name=spec.csv_filename,
                    mime="text/csv",
                    use_container_width=True,
                    key=f"{key}_download_csv",
                )

        return TableRenderResult(
            view_df=_strip_internal_columns(df=view_df, spec=spec),
            edited_df=edited_df,
            selected_rows_df=selected_rows_df,
        )

    if renderer == "streamlit":
        partial_edited_df = st.data_editor(
            view_df,
            use_container_width=True,
            hide_index=True,
            num_rows="fixed",
            column_config=spec.streamlit_column_config,
            disabled=spec.streamlit_disabled_columns,
            key=key,
        )

        edited_df = _merge_partial_df_into_full_df(
            full_df=view_df,
            partial_df=pd.DataFrame(partial_edited_df).copy(),
            identity_column=spec.identity_column,
        )
        edited_df = _strip_internal_columns(
            df=edited_df,
            spec=spec,
        )

        if spec.csv_filename:
            csv_data = edited_df.to_csv(index=False).encode("utf-8-sig")
            csv_left_col, _ = st.columns([1, 6])
            with csv_left_col:
                st.download_button(
                    label="Scarica CSV",
                    data=csv_data,
                    file_name=spec.csv_filename,
                    mime="text/csv",
                    use_container_width=True,
                    key=f"{key}_download_csv",
                )

        return TableRenderResult(
            view_df=_strip_internal_columns(df=view_df, spec=spec),
            edited_df=edited_df,
            selected_rows_df=pd.DataFrame(),
        )

    raise ValueError(f"Renderer non supportato: {renderer}")