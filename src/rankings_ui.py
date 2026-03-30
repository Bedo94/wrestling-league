from datetime import date
from typing import Any

import pandas as pd
import streamlit as st

from src.events import list_events
from src.rankings import build_rankings, build_team_rankings
from src.ratings import recompute_ratings


def _key(prefix: str, name: str) -> str:
    return f"{prefix}_{name}"


def _prepare_event_selection_state(prefix: str, event_options: list[int]) -> str:
    event_ids_key = _key(prefix, "event_ids")
    signature_key = _key(prefix, "event_options_signature")

    event_options_signature = tuple(event_options)
    current_selection = st.session_state.get(event_ids_key, [])
    valid_selection = [event_id for event_id in current_selection if event_id in event_options]
    previous_signature = st.session_state.get(signature_key)

    if previous_signature != event_options_signature:
        st.session_state[event_ids_key] = valid_selection
        st.session_state[signature_key] = event_options_signature

    if event_ids_key not in st.session_state:
        st.session_state[event_ids_key] = []

    return event_ids_key


def render_rankings_panel(
    *,
    state_prefix: str,
    title: str | None = None,
    show_filters_expanded: bool = False,
    recompute_before_render: bool = False,
) -> None:
    if recompute_before_render:
        recompute_ratings()

    events = list_events()
    events_map = {event.id: event for event in events}
    available_years = sorted({event.event_date.year for event in events})

    if title:
        st.subheader(title)

    selected_years: list[int] = []
    selected_event_ids: list[int] = []
    filtered_df = pd.DataFrame()

    with st.expander("Filtri classifica", expanded=show_filters_expanded):
        st.markdown("### Periodo ed evento")

        top_col1, top_col2 = st.columns(2)

        with top_col1:
            if available_years:
                if len(available_years) == 1:
                    st.caption(f"Anno disponibile: {available_years[0]}")
                    selected_year_range = (available_years[0], available_years[0])
                else:
                    selected_year_range = st.slider(
                        "Intervallo anni",
                        min_value=available_years[0],
                        max_value=available_years[-1],
                        value=(available_years[0], available_years[-1]),
                        step=1,
                        key=_key(state_prefix, "year_range"),
                    )

                selected_years = list(
                    range(selected_year_range[0], selected_year_range[1] + 1)
                )

        with top_col2:
            filtered_events = [
                event
                for event in events
                if not selected_years or event.event_date.year in selected_years
            ]

            event_options = [event.id for event in filtered_events]
            event_ids_key = _prepare_event_selection_state(state_prefix, event_options)

            if not event_options:
                st.caption("Nessun evento disponibile per gli anni selezionati.")
                selected_event_ids = []
            else:
                selected_event_ids = st.multiselect(
                    "Evento",
                    options=event_options,
                    key=event_ids_key,
                    format_func=lambda event_id: (
                        f"{events_map[event_id].name} — "
                        f"{events_map[event_id].event_date.strftime('%d/%m/%Y')}"
                    ),
                    placeholder="Seleziona uno o più eventi",
                )

        st.caption(
            "Se il filtro evento è vuoto, vengono considerati tutti gli eventi del periodo selezionato."
        )

        rankings = build_rankings(
            reference_date=date.today(),
            years=selected_years or None,
            event_ids=selected_event_ids or None,
        )

        if not rankings:
            st.info("Non ci sono ancora dati sufficienti per mostrare la classifica.")
            return

        df = pd.DataFrame(rankings)

        all_styles = sorted(df["style"].dropna().unique().tolist())
        all_sexes = sorted(df["sex"].dropna().unique().tolist())
        all_levels = sorted(df["level_label"].dropna().unique().tolist())
        all_teams = sorted(
            [
                team.strip()
                for team in df["team"].dropna().unique().tolist()
                if isinstance(team, str) and team.strip()
            ]
        )

        min_age = int(df["age"].min())
        max_age = int(df["age"].max())

        min_weight = float(df["default_weight"].min())
        max_weight = float(df["default_weight"].max())

        st.markdown("### Profilo atleta")

        left_col, right_col = st.columns(2)

        with left_col:
            selected_styles = st.multiselect(
                "Stile",
                options=all_styles,
                default=all_styles,
                key=_key(state_prefix, "styles"),
            )

            selected_sexes = st.multiselect(
                "Sesso",
                options=all_sexes,
                default=all_sexes,
                key=_key(state_prefix, "sexes"),
            )

            selected_levels = st.multiselect(
                "Level",
                options=all_levels,
                default=all_levels,
                key=_key(state_prefix, "levels"),
            )

        with right_col:
            if min_age == max_age:
                st.caption(f"Età disponibile: {min_age}")
                selected_age_range = (min_age, max_age)
            else:
                selected_age_range = st.slider(
                    "Età",
                    min_value=min_age,
                    max_value=max_age,
                    value=(min_age, max_age),
                    step=1,
                    key=_key(state_prefix, "age_range"),
                )

            if min_weight == max_weight:
                st.caption(f"Peso disponibile: {min_weight:.1f} kg")
                selected_weight_range = (float(min_weight), float(max_weight))
            else:
                selected_weight_range = st.slider(
                    "Peso di riferimento (kg)",
                    min_value=float(min_weight),
                    max_value=float(max_weight),
                    value=(float(min_weight), float(max_weight)),
                    step=0.5,
                    key=_key(state_prefix, "weight_range"),
                )

        st.markdown("### Stato e team")

        status_col1, status_col2 = st.columns(2)

        with status_col1:
            show_only_active = st.checkbox(
                "Mostra solo atleti attivi",
                value=True,
                key=_key(state_prefix, "show_only_active"),
            )

            show_only_with_matches = st.checkbox(
                "Mostra solo atleti con almeno un incontro",
                value=False,
                key=_key(state_prefix, "show_only_with_matches"),
            )

        with status_col2:
            enable_team_filter = st.checkbox(
                "Filtra per team",
                value=False,
                key=_key(state_prefix, "enable_team_filter"),
            )

        selected_teams: list[str] = []
        team_filter_mode = "Includi"

        if enable_team_filter and all_teams:
            team_col1, team_col2 = st.columns(2)

            with team_col1:
                team_filter_mode = st.radio(
                    "Modalità filtro team",
                    options=["Includi", "Escludi"],
                    horizontal=True,
                    key=_key(state_prefix, "team_filter_mode"),
                )

            with team_col2:
                selected_teams = st.multiselect(
                    "Team",
                    options=all_teams,
                    default=[],
                    placeholder="Cerca uno o più team",
                    key=_key(state_prefix, "teams"),
                )

        filtered_df = df.copy()

        if selected_styles:
            filtered_df = filtered_df[filtered_df["style"].isin(selected_styles)]

        if selected_sexes:
            filtered_df = filtered_df[filtered_df["sex"].isin(selected_sexes)]

        if selected_levels:
            filtered_df = filtered_df[filtered_df["level_label"].isin(selected_levels)]

        age_min, age_max = selected_age_range
        filtered_df = filtered_df[
            (filtered_df["age"] >= age_min) & (filtered_df["age"] <= age_max)
        ]

        weight_min, weight_max = selected_weight_range
        filtered_df = filtered_df[
            (filtered_df["default_weight"] >= weight_min)
            & (filtered_df["default_weight"] <= weight_max)
        ]

        if show_only_active:
            filtered_df = filtered_df[filtered_df["active"] == True]

        if show_only_with_matches:
            filtered_df = filtered_df[filtered_df["matches"] > 0]

        if enable_team_filter and selected_teams:
            if team_filter_mode == "Includi":
                filtered_df = filtered_df[filtered_df["team"].isin(selected_teams)]
            else:
                filtered_df = filtered_df[~filtered_df["team"].isin(selected_teams)]

    if filtered_df.empty:
        st.warning("Nessun atleta corrisponde ai filtri selezionati.")
        return

    if filtered_df["matches"].sum() == 0:
        filtered_df = filtered_df.sort_values(
            by=[
                "rating",
                "name",
            ],
            ascending=[False, True],
        ).reset_index(drop=True)
    else:
        filtered_df = filtered_df.sort_values(
            by=[
                "class_points_total",
                "wins",
                "technical_diff",
                "technical_points_for",
                "name",
            ],
            ascending=[False, False, False, False, True],
        ).reset_index(drop=True)

    filtered_df["Posizione"] = filtered_df.index + 1
    filtered_df["Rating"] = filtered_df["rating"].apply(
        lambda x: x if x is not None else "N.D."
    )
    filtered_df["Data nascita"] = filtered_df["birth_date"].apply(
        lambda d: d.strftime("%d/%m/%Y")
    )

    display_df = filtered_df[
        [
            "Posizione",
            "name",
            "nickname",
            "team",
            "style",
            "sex",
            "age",
            "default_weight",
            "level_label",
            "Rating",
            "matches",
            "wins",
            "losses",
            "class_points_total",
            "avg_class_points",
            "technical_points_for",
            "technical_points_against",
            "technical_diff",
            "Data nascita",
        ]
    ].rename(
        columns={
            "name": "Atleta",
            "nickname": "Nickname",
            "team": "Team",
            "style": "Stile",
            "sex": "Sesso",
            "age": "Età",
            "default_weight": "Peso rif.",
            "level_label": "Level",
            "matches": "Incontri",
            "wins": "Vittorie",
            "losses": "Sconfitte",
            "class_points_total": "Punti classifica",
            "avg_class_points": "Media punti",
            "technical_points_for": "Punti fatti",
            "technical_points_against": "Punti subiti",
            "technical_diff": "Differenza punti",
        }
    )

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
    )

    show_team_ranking = st.checkbox(
        "Mostra classifica team",
        value=False,
        key=_key(state_prefix, "show_team_ranking"),
    )

    if show_team_ranking:
        ranking_rows: list[dict[str, Any]] = [
            {str(k): v for k, v in row.items()}
            for row in filtered_df.to_dict(orient="records")
        ]

        team_rows = build_team_rankings(
            ranking_rows=ranking_rows,
        )

        if team_rows:
            team_df = pd.DataFrame(team_rows).rename(
                columns={
                    "rank": "Posizione",
                    "team": "Team",
                    "athletes_count": "Atleti nel filtro",
                    "participating_athletes": "Atleti partecipanti",
                    "matches": "Incontri",
                    "wins": "Vittorie",
                    "losses": "Sconfitte",
                    "class_points_total": "Punti classifica",
                    "participation_bonus": "Bonus partecipazione",
                    "team_score": "Punteggio team",
                    "avg_points_per_participating_athlete": "Media punti/partecipante",
                    "technical_points_for": "Punti fatti",
                    "technical_points_against": "Punti subiti",
                    "technical_diff": "Differenza punti",
                }
            )

            st.subheader("Classifica team")

            st.dataframe(
                team_df[
                    [
                        "Posizione",
                        "Team",
                        "Atleti nel filtro",
                        "Atleti partecipanti",
                        "Incontri",
                        "Vittorie",
                        "Sconfitte",
                        "Punti classifica",
                        "Bonus partecipazione",
                        "Punteggio team",
                        "Media punti/partecipante",
                        "Punti fatti",
                        "Punti subiti",
                        "Differenza punti",
                    ]
                ],
                use_container_width=True,
                hide_index=True,
            )

    if filtered_df["matches"].sum() == 0:
        st.caption(
            "Ordinamento: in assenza di incontri, rating iniziale; a parità, nome."
        )
    else:
        st.caption(
            "Ordinamento: punti classifica, poi vittorie, poi differenza punti tecnici, poi punti fatti."
        )