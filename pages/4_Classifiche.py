from datetime import date

import pandas as pd
import streamlit as st

from src.ratings import recompute_ratings
from src.rankings import build_rankings

st.title("Classifiche")

st.markdown(
    """
Questa pagina mostra una classifica generale costruita come somma dei punti classifica
ottenuti da ciascun atleta nei vari incontri.

Puoi filtrare la vista per:
- stile
- sesso
- età
- peso di riferimento
- stato attivo
"""
)

recompute_ratings()
rankings = build_rankings(reference_date=date.today())

if not rankings:
    st.info("Non ci sono ancora dati sufficienti per mostrare la classifica.")
    st.stop()

df = pd.DataFrame(rankings)

all_styles = sorted(df["style"].dropna().unique().tolist())
all_sexes = sorted(df["sex"].dropna().unique().tolist())
all_levels = sorted(df["level_label"].dropna().unique().tolist())

min_age = int(df["age"].min())
max_age = int(df["age"].max())

min_weight = float(df["default_weight"].min())
max_weight = float(df["default_weight"].max())

st.subheader("Filtri")

col1, col2 = st.columns(2)

with col1:
    selected_styles = st.multiselect(
        "Stile",
        options=all_styles,
        default=all_styles,
    )

    selected_sexes = st.multiselect(
        "Sesso",
        options=all_sexes,
        default=all_sexes,
    )

    selected_levels = st.multiselect(
        "Level",
        options=all_levels,
        default=all_levels,
    )

with col2:
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
        )

show_only_active = st.checkbox("Mostra solo atleti attivi", value=True)
show_only_with_matches = st.checkbox("Mostra solo atleti con almeno un incontro", value=False)

filtered_df = df.copy()

if selected_styles:
    filtered_df = filtered_df[filtered_df["style"].isin(selected_styles)]

if selected_sexes:
    filtered_df = filtered_df[filtered_df["sex"].isin(selected_sexes)]

if selected_levels:
    filtered_df = filtered_df[filtered_df["level_label"].isin(selected_levels)]

age_min, age_max = selected_age_range
filtered_df = filtered_df[
    (filtered_df["age"] >= age_min) &
    (filtered_df["age"] <= age_max)
]

weight_min, weight_max = selected_weight_range
filtered_df = filtered_df[
    (filtered_df["default_weight"] >= weight_min) &
    (filtered_df["default_weight"] <= weight_max)
]

if show_only_active:
    filtered_df = filtered_df[filtered_df["active"] == True]

if show_only_with_matches:
    filtered_df = filtered_df[filtered_df["matches"] > 0]

if filtered_df.empty:
    st.warning("Nessun atleta corrisponde ai filtri selezionati.")
    st.stop()

filtered_df = filtered_df.sort_values(
    by=["class_points_total", "wins", "technical_diff", "technical_points_for", "name"],
    ascending=[False, False, False, False, True],
).reset_index(drop=True)

filtered_df["Posizione"] = filtered_df.index + 1
filtered_df["Rating"] = filtered_df["rating"].apply(lambda x: x if x is not None else "N.D.")
filtered_df["Data nascita"] = filtered_df["birth_date"].apply(lambda d: d.strftime("%d/%m/%Y"))

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

st.subheader("Classifica")

st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True,
)

st.caption(
    "Ordinamento: punti classifica, poi vittorie, poi differenza punti tecnici, poi punti fatti."
)