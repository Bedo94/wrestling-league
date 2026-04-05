from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st
from st_aggrid import AgGrid, DataReturnMode, GridOptionsBuilder, GridUpdateMode

DEFAULT_HEADER_HEIGHT = 33
DEFAULT_FLOATING_FILTERS_HEIGHT = 31
DEFAULT_ROW_HEIGHT = 31
DEFAULT_MIN_COLUMN_WIDTH = 84
DEFAULT_MAX_GRID_HEIGHT = 430
DEFAULT_MIN_GRID_HEIGHT = 120
GRID_VERTICAL_PADDING = 6


AGGRID_STREAMLIT_LIKE_CSS: dict[str, dict[str, str]] = {
    ".ag-root-wrapper": {
        "border": "1px solid rgba(49, 51, 63, 0.10)",
        "border-radius": "8px",
        "overflow": "hidden",
        "box-shadow": "none",
        "font-family": "inherit",
        "color": "inherit",
        "text-rendering": "optimizeLegibility",
        "-webkit-font-smoothing": "antialiased",
        "-moz-osx-font-smoothing": "grayscale",
    },
    ".ag-root-wrapper-body": {
        "font-family": "inherit",
    },
    ".ag-header": {
        "border-bottom": "1px solid rgba(49, 51, 63, 0.07)",
        "background-color": "#f7f8fa",
        "font-family": "inherit",
    },
    ".ag-header-viewport": {
        "background-color": "#f7f8fa",
        "border-right": "none !important",
    },
    ".ag-header-row": {
        "font-size": "0.79rem",
        "background-color": "#f7f8fa",
        "font-family": "inherit",
        "font-weight": "500",
    },
    ".ag-header-cell": {
        "font-size": "0.79rem",
        "font-weight": "500",
        "line-height": "1.3",
        "padding-left": "6px",
        "padding-right": "6px",
        "border-right": "1px solid rgba(49, 51, 63, 0.15)",
        "background-color": "#f7f8fa",
        "font-family": "inherit",
        "color": "rgba(49, 51, 63, 0.66)",
    },
    ".ag-header-cell::after": {
        "display": "none !important",
    },
    ".ag-header-group-cell::after": {
        "display": "none !important",
    },
    ".ag-header-cell:last-child": {
        "border-right": "none",
    },
    ".ag-header-cell-label": {
        "gap": "3px",
    },
    ".ag-header-cell-text": {
        "font-weight": "500",
        "color": "rgba(49, 51, 63, 0.66)",
    },
    ".ag-header-cell .ag-icon": {
        "color": "rgba(49, 51, 63, 0.52)",
    },
    ".ag-floating-filter": {
        "border-bottom": "1px solid rgba(49, 51, 63, 0.055)",
        "border-right": "1px solid rgba(49, 51, 63, 0.09)",
        "background-color": "#ffffff",
        "font-family": "inherit",
    },
    ".ag-floating-filter:last-child": {
        "border-right": "none",
    },
    ".ag-floating-filter-viewport": {
        "border-right": "none !important",
    },
    ".ag-floating-filter-body": {
        "padding-left": "2px",
        "padding-right": "2px",
    },
    ".ag-floating-filter-body input": {
        "border": "1px solid rgba(49, 51, 63, 0.075)",
        "border-radius": "5px",
        "padding": "2px 6px",
        "font-size": "0.81rem",
        "font-weight": "400",
        "line-height": "1.3",
        "min-height": "23px",
        "background-color": "#ffffff",
        "box-shadow": "none",
        "font-family": "inherit",
        "color": "rgba(49, 51, 63, 0.88)",
    },
    ".ag-cell": {
        "display": "flex",
        "align-items": "center",
        "font-size": "0.81rem",
        "font-weight": "400",
        "line-height": "1.35",
        "padding-left": "6px",
        "padding-right": "6px",
        "border-right": "1px solid rgba(49, 51, 63, 0.09)",
        "font-family": "inherit",
        "color": "rgba(49, 51, 63, 0.88)",
    },
    ".ag-cell:last-child": {
        "border-right": "none",
    },
    ".ag-row": {
        "border-bottom": "1px solid rgba(49, 51, 63, 0.04)",
        "background-color": "#ffffff",
    },
    ".ag-row:nth-child(even)": {
        "background-color": "#ffffff",
    },
    ".ag-row-hover": {
        "background-color": "rgba(49, 51, 63, 0.010) !important",
    },
    ".ag-cell-inline-editing": {
        "border": "1px solid rgba(49, 51, 63, 0.08)",
        "border-radius": "5px",
        "padding-left": "5px",
        "padding-right": "5px",
        "background-color": "#ffffff",
        "font-family": "inherit",
        "color": "rgba(49, 51, 63, 0.88)",
        "font-size": "0.81rem",
    },
    ".ag-popup-editor": {
        "border-radius": "6px",
        "overflow": "hidden",
        "font-family": "inherit",
    },
    ".ag-theme-streamlit .ag-picker-field-wrapper": {
        "min-height": "23px",
        "border-radius": "5px",
        "border-color": "rgba(49, 51, 63, 0.08)",
        "font-family": "inherit",
    },
    ".ag-theme-streamlit .ag-input-field-input": {
        "font-size": "0.81rem",
        "font-weight": "400",
        "font-family": "inherit",
        "color": "rgba(49, 51, 63, 0.88)",
    },
    ".ag-theme-streamlit .ag-cell-value": {
        "font-family": "inherit",
        "font-weight": "400",
        "color": "rgba(49, 51, 63, 0.88)",
    },
}


def create_soft_grid_builder(
    df: pd.DataFrame,
    *,
    editable: bool = True,
    header_height: int = DEFAULT_HEADER_HEIGHT,
    floating_filters_height: int = DEFAULT_FLOATING_FILTERS_HEIGHT,
    row_height: int = DEFAULT_ROW_HEIGHT,
    min_column_width: int = DEFAULT_MIN_COLUMN_WIDTH,
) -> GridOptionsBuilder:
    gb = GridOptionsBuilder.from_dataframe(df)

    gb.configure_default_column(
        editable=editable,
        sortable=True,
        filter=True,
        resizable=True,
        floatingFilter=True,
        minWidth=min_column_width,
    )

    gb.configure_grid_options(
        headerHeight=header_height,
        floatingFiltersHeight=floating_filters_height,
        rowHeight=row_height,
        stopEditingWhenCellsLoseFocus=True,
        suppressMovableColumns=True,
        ensureDomOrder=True,
        animateRows=False,
        suppressHorizontalScroll=False,
    )

    return gb


def _compute_grid_height(
    row_count: int,
    *,
    header_height: int,
    floating_filters_height: int,
    row_height: int,
    min_height: int,
    max_height: int,
    vertical_padding: int = GRID_VERTICAL_PADDING,
) -> int:
    safe_row_count = max(row_count, 1)

    content_height = (
        header_height
        + floating_filters_height
        + (safe_row_count * row_height)
        + vertical_padding
    )

    return max(min_height, min(content_height, max_height))


def render_soft_aggrid(
    df: pd.DataFrame,
    *,
    grid_options: dict[str, Any],
    key: str | None = None,
    csv_filename: str | None = None,
    csv_button_label: str = "Scarica CSV",
    height: int | None = None,
    max_height: int = DEFAULT_MAX_GRID_HEIGHT,
    min_height: int = DEFAULT_MIN_GRID_HEIGHT,
    header_height: int = DEFAULT_HEADER_HEIGHT,
    floating_filters_height: int = DEFAULT_FLOATING_FILTERS_HEIGHT,
    row_height: int = DEFAULT_ROW_HEIGHT,
) -> Any:
    effective_height = height
    if effective_height is None:
        effective_height = _compute_grid_height(
            len(df),
            header_height=header_height,
            floating_filters_height=floating_filters_height,
            row_height=row_height,
            min_height=min_height,
            max_height=max_height,
        )

    grid_response = AgGrid(
        df,
        gridOptions=grid_options,
        data_return_mode=DataReturnMode.AS_INPUT,
        update_mode=(
            GridUpdateMode.VALUE_CHANGED
            | GridUpdateMode.MODEL_CHANGED
            | GridUpdateMode.SELECTION_CHANGED
        ),
        fit_columns_on_grid_load=False,
        theme="streamlit",
        custom_css=AGGRID_STREAMLIT_LIKE_CSS,
        height=effective_height,
        reload_data=False,
        allow_unsafe_jscode=False,
        key=key,
    )

    if csv_filename:
        current_grid_df = pd.DataFrame(grid_response["data"]).copy()
        csv_data = current_grid_df.to_csv(index=False).encode("utf-8-sig")

        csv_left_col, csv_right_col = st.columns([1, 6])
        with csv_left_col:
            st.download_button(
                label=csv_button_label,
                data=csv_data,
                file_name=csv_filename,
                mime="text/csv",
                use_container_width=True,
                key=f"{key}_download_csv" if key else None,
            )

    return grid_response