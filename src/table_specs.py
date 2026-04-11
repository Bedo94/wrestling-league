from __future__ import annotations

from typing import Any

import pandas as pd
from st_aggrid import GridOptionsBuilder

from src.aggrid_schemas import (
    configure_athletes_grid,
    configure_events_grid,
    configure_matches_grid,
    normalize_athletes_grid_df,
    normalize_events_grid_df,
    normalize_matches_grid_df,
    prepare_athletes_grid_df,
    prepare_events_grid_df,
    prepare_matches_grid_df,
)
from src.levels import get_level_labels
from src.reference_data import SEX_OPTIONS, STYLE_OPTIONS
from src.table_component import TableSpec


def _configure_athletes_aggrid(gb: GridOptionsBuilder) -> None:
    configure_athletes_grid(
        gb,
        sex_options=SEX_OPTIONS,
        style_options=STYLE_OPTIONS,
        level_labels=get_level_labels(),
    )


def _configure_events_aggrid(gb: GridOptionsBuilder) -> None:
    configure_events_grid(gb)


def _configure_matches_aggrid(gb: GridOptionsBuilder) -> None:
    configure_matches_grid(gb)


def _configure_readonly_grid(
    gb: GridOptionsBuilder,
    df: pd.DataFrame,
    *,
    pinned_left_columns: list[str],
    width_overrides: dict[str, int] | None = None,
    flex_overrides: dict[str, float] | None = None,
) -> None:
    width_overrides = width_overrides or {}
    flex_overrides = flex_overrides or {}
    pinned_left_set = set(pinned_left_columns)

    for column_name in df.columns:
        series = df[column_name]
        is_numeric = pd.api.types.is_numeric_dtype(series)

        kwargs: dict[str, Any] = {
            "editable": False,
            "filter": "agNumberColumnFilter" if is_numeric else "agTextColumnFilter",
        }

        if is_numeric:
            kwargs["type"] = ["numericColumn"]

        if column_name in pinned_left_set:
            kwargs["pinned"] = "left"

        if column_name in flex_overrides:
            kwargs["flex"] = float(flex_overrides[column_name])
            kwargs["minWidth"] = 120
        else:
            width = int(width_overrides.get(column_name, 96 if is_numeric else 110))
            kwargs["width"] = width
            kwargs["minWidth"] = max(width - 8, 70)
            kwargs["maxWidth"] = width + 12

        gb.configure_column(column_name, **kwargs)


ATHLETES_TABLE_SPEC = TableSpec(
    name="athletes",
    csv_filename="atleti.csv",
    caption=(
        "Filtra e seleziona una o più righe dalla tabella. "
        "Puoi modificare le righe visibili senza perdere quelle nascoste dai filtri."
    ),
    prepare_for_view=prepare_athletes_grid_df,
    normalize_from_view=normalize_athletes_grid_df,
    configure_aggrid=_configure_athletes_aggrid,
    editable=True,
    enable_selection=True,
    selection_mode="multiple",
    enable_column_visibility=True,
    always_visible_columns=["Nome"],
    hidden_columns=["::auto_unique_id::"],
    hidden_by_default_columns=["ID", "#", "Livello suggerito"],
    default_visible_columns=None,
    show_row_index=True,
    row_index_column_name="#",
    identity_column="ID",
    header_height=33,
    floating_filters_height=31,
    row_height=31,
    min_column_width=84,
    max_height=430,
    min_height=120,
)

EVENTS_TABLE_SPEC = TableSpec(
    name="events",
    csv_filename="eventi.csv",
    caption=(
        "Filtra e seleziona una o più righe dalla tabella. "
        "Puoi modificare le righe visibili senza perdere quelle nascoste dai filtri."
    ),
    prepare_for_view=prepare_events_grid_df,
    normalize_from_view=normalize_events_grid_df,
    configure_aggrid=_configure_events_aggrid,
    editable=True,
    enable_selection=True,
    selection_mode="multiple",
    enable_column_visibility=True,
    always_visible_columns=["Nome"],
    hidden_columns=["::auto_unique_id::"],
    hidden_by_default_columns=["ID", "#"],
    default_visible_columns=None,
    show_row_index=True,
    row_index_column_name="#",
    identity_column="ID",
    header_height=33,
    floating_filters_height=31,
    row_height=31,
    min_column_width=84,
    max_height=430,
    min_height=120,
)

MATCHES_TABLE_SPEC = TableSpec(
    name="matches",
    csv_filename="incontri.csv",
    caption=(
        "Filtra e seleziona una o più righe dalla tabella. "
        "L'ultima riga selezionata viene caricata automaticamente nel form."
    ),
    prepare_for_view=prepare_matches_grid_df,
    normalize_from_view=normalize_matches_grid_df,
    configure_aggrid=_configure_matches_aggrid,
    editable=False,
    enable_selection=True,
    selection_mode="multiple",
    enable_column_visibility=True,
    always_visible_columns=["Evento", "Atleta A", "Atleta B"],
    hidden_columns=["::auto_unique_id::"],
    hidden_by_default_columns=["ID", "#"],
    default_visible_columns=None,
    show_row_index=True,
    row_index_column_name="#",
    identity_column="ID",
    header_height=33,
    floating_filters_height=31,
    row_height=31,
    min_column_width=84,
    max_height=430,
    min_height=120,
)


def build_athlete_rankings_table_spec(
    *,
    display_df: pd.DataFrame,
) -> TableSpec:
    def _configure(gb: GridOptionsBuilder) -> None:
        _configure_readonly_grid(
            gb,
            display_df,
            pinned_left_columns=["Posizione", "Atleta"],
            width_overrides={
                "Posizione": 86,
                "Stile": 90,
                "Sesso": 86,
                "Età": 78,
                "Peso rif.": 92,
                "Level": 96,
                "Rating": 90,
                "Incontri": 88,
                "Vittorie": 84,
                "Sconfitte": 92,
                "Punti classifica": 118,
                "Media punti": 102,
                "Provvisorio": 96,
                "Punti fatti": 96,
                "Punti subiti": 100,
                "Differenza punti": 116,
                "Data nascita": 112,
            },
            flex_overrides={
                "Atleta": 1.2,
                "Nickname": 0.95,
                "Team": 1.1,
            },
        )

    return TableSpec(
        name="athlete_rankings",
        csv_filename="classifica_atleti.csv",
        caption="Puoi mostrare o nascondere colonne dal menu Colonne.",
        prepare_for_view=lambda df: df.copy(),
        normalize_from_view=lambda df: df.copy(),
        configure_aggrid=_configure,
        editable=False,
        enable_selection=False,
        enable_column_visibility=True,
        always_visible_columns=["Posizione", "Atleta"],
        default_visible_columns=list(display_df.columns),
        show_row_index=False,
        header_height=33,
        floating_filters_height=31,
        row_height=31,
        min_column_width=84,
        max_height=430,
        min_height=120,
    )


def build_team_rankings_table_spec(
    *,
    display_df: pd.DataFrame,
) -> TableSpec:
    def _configure(gb: GridOptionsBuilder) -> None:
        _configure_readonly_grid(
            gb,
            display_df,
            pinned_left_columns=["Posizione", "Team"],
            width_overrides={
                "Posizione": 86,
                "Atleti nel filtro": 120,
                "Atleti partecipanti": 136,
                "Incontri": 88,
                "Vittorie": 84,
                "Sconfitte": 92,
                "Punti classifica": 118,
                "Bonus partecipazione": 136,
                "Media punti/partecipante": 154,
                "Punteggio team": 116,
                "Punti fatti": 96,
                "Punti subiti": 100,
                "Differenza punti": 116,
            },
            flex_overrides={
                "Team": 1.2,
            },
        )

    return TableSpec(
        name="team_rankings",
        csv_filename="classifica_team.csv",
        caption="Puoi mostrare o nascondere colonne dal menu Colonne.",
        prepare_for_view=lambda df: df.copy(),
        normalize_from_view=lambda df: df.copy(),
        configure_aggrid=_configure,
        editable=False,
        enable_selection=False,
        enable_column_visibility=True,
        always_visible_columns=["Posizione", "Team"],
        default_visible_columns=list(display_df.columns),
        show_row_index=False,
        header_height=33,
        floating_filters_height=31,
        row_height=31,
        min_column_width=84,
        max_height=430,
        min_height=120,
    )


def build_selected_pairings_table_spec(
    *,
    display_df: pd.DataFrame,
) -> TableSpec:
    def _configure(gb: GridOptionsBuilder) -> None:
        _configure_readonly_grid(
            gb,
            display_df,
            pinned_left_columns=["Atleta A", "Atleta B"],
            width_overrides={
                "Stile": 90,
                "Δ peso": 86,
                "Δ level": 96,
                "Δ rating": 96,
                "Δ età": 80,
                "Storico": 94,
                "Prob. A (%)": 96,
                "Prob. B (%)": 96,
                "Indice mismatch": 118,
            },
            flex_overrides={
                "Atleta A": 1.15,
                "Atleta B": 1.15,
            },
        )

    return TableSpec(
        name="selected_pairings",
        csv_filename="accoppiamenti_suggeriti.csv",
        caption="Puoi mostrare o nascondere colonne dal menu Colonne.",
        prepare_for_view=lambda df: df.copy(),
        normalize_from_view=lambda df: df.copy(),
        configure_aggrid=_configure,
        editable=False,
        enable_selection=False,
        enable_column_visibility=True,
        always_visible_columns=["Atleta A", "Atleta B"],
        default_visible_columns=list(display_df.columns),
        show_row_index=False,
        header_height=33,
        floating_filters_height=31,
        row_height=31,
        min_column_width=84,
        max_height=430,
        min_height=120,
    )


def build_candidate_pairings_table_spec(
    *,
    display_df: pd.DataFrame,
) -> TableSpec:
    def _configure(gb: GridOptionsBuilder) -> None:
        _configure_readonly_grid(
            gb,
            display_df,
            pinned_left_columns=["Atleta A", "Atleta B"],
            width_overrides={
                "Stile": 90,
                "Peso A": 88,
                "Peso B": 88,
                "Level A": 94,
                "Level B": 94,
                "Rating A": 90,
                "Rating B": 90,
                "Età A": 80,
                "Età B": 80,
                "Δ peso": 86,
                "Δ level": 96,
                "Δ rating": 96,
                "Δ età": 80,
                "Storico": 94,
                "Prob. A (%)": 96,
                "Prob. B (%)": 96,
                "Comp. peso": 96,
                "Comp. level": 100,
                "Comp. rating": 100,
                "Comp. età": 90,
                "Pen. rematch": 104,
                "Indice mismatch": 118,
            },
            flex_overrides={
                "Atleta A": 1.15,
                "Atleta B": 1.15,
            },
        )

    return TableSpec(
        name="candidate_pairings",
        csv_filename="tutti_gli_accoppiamenti.csv",
        caption="Puoi mostrare o nascondere colonne dal menu Colonne.",
        prepare_for_view=lambda df: df.copy(),
        normalize_from_view=lambda df: df.copy(),
        configure_aggrid=_configure,
        editable=False,
        enable_selection=False,
        enable_column_visibility=True,
        always_visible_columns=["Atleta A", "Atleta B"],
        default_visible_columns=list(display_df.columns),
        show_row_index=False,
        header_height=33,
        floating_filters_height=31,
        row_height=31,
        min_column_width=84,
        max_height=520,
        min_height=120,
    )


def build_pairing_leftovers_table_spec(
    *,
    display_df: pd.DataFrame,
) -> TableSpec:
    def _configure(gb: GridOptionsBuilder) -> None:
        _configure_readonly_grid(
            gb,
            display_df,
            pinned_left_columns=["Atleta"],
            width_overrides={
                "Sesso": 84,
                "Stile": 90,
                "Peso": 84,
                "Level": 92,
                "Rating": 90,
                "Età": 78,
            },
            flex_overrides={
                "Atleta": 1.2,
            },
        )

    return TableSpec(
        name="pairing_leftovers",
        csv_filename="atleti_senza_accoppiamento.csv",
        caption="Puoi mostrare o nascondere colonne dal menu Colonne.",
        prepare_for_view=lambda df: df.copy(),
        normalize_from_view=lambda df: df.copy(),
        configure_aggrid=_configure,
        editable=False,
        enable_selection=False,
        enable_column_visibility=True,
        always_visible_columns=["Atleta"],
        default_visible_columns=list(display_df.columns),
        show_row_index=False,
        header_height=33,
        floating_filters_height=31,
        row_height=31,
        min_column_width=84,
        max_height=360,
        min_height=120,
    )
