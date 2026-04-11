from __future__ import annotations

from collections.abc import Sequence

import pandas as pd
from st_aggrid import GridOptionsBuilder

ACTIVE_LABEL = "Attivo"
INACTIVE_LABEL = "Inattivo"


def configure_text_column(
    gb: GridOptionsBuilder,
    column_name: str,
    *,
    editable: bool = True,
    flex: float | None = None,
    width: int | None = None,
    min_width: int | None = None,
    max_width: int | None = None,
    pinned: str | None = None,
) -> None:
    kwargs: dict[str, object] = {
        "editable": editable,
        "filter": "agTextColumnFilter",
    }

    if flex is not None:
        kwargs["flex"] = flex
    if width is not None:
        kwargs["width"] = width
    if min_width is not None:
        kwargs["minWidth"] = min_width
    if max_width is not None:
        kwargs["maxWidth"] = max_width
    if pinned is not None:
        kwargs["pinned"] = pinned

    gb.configure_column(column_name, **kwargs)


def configure_number_column(
    gb: GridOptionsBuilder,
    column_name: str,
    *,
    editable: bool = True,
    width: int | None = None,
    min_width: int | None = None,
    max_width: int | None = None,
    pinned: str | None = None,
) -> None:
    kwargs: dict[str, object] = {
        "editable": editable,
        "filter": "agNumberColumnFilter",
        "type": ["numericColumn"],
    }

    if width is not None:
        kwargs["width"] = width
    if min_width is not None:
        kwargs["minWidth"] = min_width
    if max_width is not None:
        kwargs["maxWidth"] = max_width
    if pinned is not None:
        kwargs["pinned"] = pinned

    gb.configure_column(column_name, **kwargs)


def configure_select_text_filter_column(
    gb: GridOptionsBuilder,
    column_name: str,
    *,
    options: Sequence[object],
    editable: bool = True,
    width: int | None = None,
    min_width: int | None = None,
    max_width: int | None = None,
) -> None:
    kwargs: dict[str, object] = {
        "editable": editable,
        "filter": "agTextColumnFilter",
        "cellEditor": "agSelectCellEditor",
        "cellEditorParams": {"values": list(options)},
        "cellEditorPopup": True,
    }

    if width is not None:
        kwargs["width"] = width
    if min_width is not None:
        kwargs["minWidth"] = min_width
    if max_width is not None:
        kwargs["maxWidth"] = max_width

    gb.configure_column(column_name, **kwargs)


def prepare_athletes_grid_df(df: pd.DataFrame) -> pd.DataFrame:
    grid_df = df.copy()

    grid_df["Data nascita"] = pd.to_datetime(
        grid_df["Data nascita"],
        errors="coerce",
    ).dt.strftime("%Y-%m-%d")

    grid_df["Attivo"] = grid_df["Attivo"].map(
        {
            True: ACTIVE_LABEL,
            False: INACTIVE_LABEL,
        }
    )

    return grid_df


def normalize_athletes_grid_df(grid_df: pd.DataFrame) -> pd.DataFrame:
    normalized_df = grid_df.copy()

    normalized_df["Data nascita"] = pd.to_datetime(
        normalized_df["Data nascita"],
        errors="raise",
    ).dt.date

    normalized_df["Peso"] = pd.to_numeric(
        normalized_df["Peso"],
        errors="raise",
    ).astype(float)

    normalized_df["Attivo"] = normalized_df["Attivo"].map(
        {
            ACTIVE_LABEL: True,
            INACTIVE_LABEL: False,
        }
    )

    if normalized_df["Attivo"].isna().any():
        raise ValueError(
            "Valore non valido nella colonna 'Attivo'. Usa solo 'Attivo' o 'Inattivo'."
        )

    normalized_df["Attivo"] = normalized_df["Attivo"].astype(bool)

    return normalized_df


def configure_athletes_grid(
    gb: GridOptionsBuilder,
    *,
    sex_options: Sequence[str],
    style_options: Sequence[str],
    level_labels: Sequence[str],
) -> None:
    gb.configure_column(
        "ID",
        headerName="ID",
        editable=False,
        pinned="left",
        width=64,
        minWidth=60,
        maxWidth=70,
        filter="agNumberColumnFilter",
        type=["numericColumn"],
    )

    configure_text_column(gb, "Nome", editable=True, flex=1.0, min_width=100)
    configure_text_column(gb, "Cognome", editable=True, flex=1.0, min_width=100)
    configure_text_column(gb, "Nickname", editable=True, flex=0.85, min_width=96)
    configure_text_column(gb, "Team", editable=True, flex=1.15, min_width=135)
    configure_text_column(
        gb,
        "Data nascita",
        editable=True,
        width=118,
        min_width=112,
        max_width=124,
    )

    configure_select_text_filter_column(
        gb,
        "Sesso",
        editable=True,
        options=sex_options,
        width=86,
        min_width=82,
        max_width=92,
    )
    configure_select_text_filter_column(
        gb,
        "Stile",
        editable=True,
        options=style_options,
        width=94,
        min_width=90,
        max_width=100,
    )
    configure_select_text_filter_column(
        gb,
        "Livello assegnato",
        editable=True,
        options=level_labels,
        width=130,
        min_width=122,
        max_width=138,
    )
    configure_text_column(
        gb,
        "Livello suggerito",
        editable=False,
        width=126,
        min_width=118,
        max_width=134,
    )
    configure_number_column(
        gb,
        "Peso",
        editable=True,
        width=76,
        min_width=72,
        max_width=82,
    )
    configure_text_column(
        gb,
        "Rating",
        editable=False,
        width=84,
        min_width=80,
        max_width=90,
    )
    configure_select_text_filter_column(
        gb,
        "Attivo",
        editable=True,
        options=[ACTIVE_LABEL, INACTIVE_LABEL],
        width=88,
        min_width=82,
        max_width=96,
    )


def prepare_events_grid_df(df: pd.DataFrame) -> pd.DataFrame:
    grid_df = df.copy()

    grid_df["Data"] = pd.to_datetime(
        grid_df["Data"],
        errors="coerce",
    ).dt.strftime("%Y-%m-%d")

    return grid_df


def normalize_events_grid_df(grid_df: pd.DataFrame) -> pd.DataFrame:
    normalized_df = grid_df.copy()

    normalized_df["Data"] = pd.to_datetime(
        normalized_df["Data"],
        errors="raise",
    ).dt.date

    return normalized_df


def configure_events_grid(gb: GridOptionsBuilder) -> None:
    gb.configure_column(
        "ID",
        headerName="ID",
        editable=False,
        pinned="left",
        width=64,
        minWidth=60,
        maxWidth=70,
        filter="agNumberColumnFilter",
        type=["numericColumn"],
    )

    configure_text_column(
        gb,
        "Nome",
        editable=True,
        flex=1.2,
        min_width=150,
    )
    configure_text_column(
        gb,
        "Data",
        editable=True,
        width=118,
        min_width=112,
        max_width=124,
    )
    configure_text_column(
        gb,
        "Note",
        editable=True,
        flex=1.8,
        min_width=220,
    )


def prepare_matches_grid_df(df: pd.DataFrame) -> pd.DataFrame:
    grid_df = df.copy()

    if "Data" in grid_df.columns:
        grid_df["Data"] = pd.to_datetime(
            grid_df["Data"],
            errors="coerce",
        ).dt.strftime("%Y-%m-%d")

    return grid_df


def normalize_matches_grid_df(grid_df: pd.DataFrame) -> pd.DataFrame:
    return grid_df.copy()


def configure_matches_grid(gb: GridOptionsBuilder) -> None:
    gb.configure_column(
        "ID",
        headerName="ID",
        editable=False,
        pinned="left",
        width=64,
        minWidth=60,
        maxWidth=70,
        filter="agNumberColumnFilter",
        type=["numericColumn"],
    )

    configure_text_column(gb, "Evento", editable=False, flex=1.15, min_width=150)
    configure_text_column(gb, "Data", editable=False, width=118, min_width=112, max_width=124)
    configure_text_column(gb, "Stile", editable=False, width=90, min_width=86, max_width=96)

    configure_text_column(gb, "Atleta A", editable=False, flex=1.0, min_width=140)
    configure_number_column(gb, "Peso A", editable=False, width=78, min_width=74, max_width=84)
    configure_text_column(gb, "Livello A", editable=False, width=98, min_width=92, max_width=104)
    configure_number_column(gb, "Punti A", editable=False, width=78, min_width=74, max_width=84)

    configure_text_column(gb, "Atleta B", editable=False, flex=1.0, min_width=140)
    configure_number_column(gb, "Peso B", editable=False, width=78, min_width=74, max_width=84)
    configure_text_column(gb, "Livello B", editable=False, width=98, min_width=92, max_width=104)
    configure_number_column(gb, "Punti B", editable=False, width=78, min_width=74, max_width=84)

    configure_text_column(gb, "Vincitore", editable=False, flex=1.0, min_width=140)
    configure_text_column(gb, "Modo vittoria", editable=False, width=118, min_width=110, max_width=126)
    configure_text_column(gb, "Token", editable=False, width=74, min_width=70, max_width=80)
    configure_text_column(gb, "Spende token", editable=False, flex=1.0, min_width=140)
    configure_text_column(gb, "Punti classifica A", editable=False, width=120, min_width=112, max_width=128)
    configure_text_column(gb, "Punti classifica B", editable=False, width=120, min_width=112, max_width=128)
    configure_text_column(gb, "Note", editable=False, flex=1.4, min_width=180)
