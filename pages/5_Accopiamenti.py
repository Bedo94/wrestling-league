from datetime import date

import pandas as pd
import streamlit as st

from src.athletes import list_athletes
from src.events import list_events
from src.levels import get_level_label
from src.pairing import calculate_age, generate_candidate_pairs, select_greedy_pairings
from src.matches import list_matches

st.title("Accoppiamenti / Matchmaking")

st.markdown(
    """
Questa pagina suggerisce matchup bilanciati in base a:

- stile
- peso
- level
- rating
- età
- precedenti incontri

**Nota:** questa versione propone accoppiamenti ma non crea ancora incontri nel database.
"""
)


def athlete_label(athlete, reference_date: date) -> str:
    full_name = f"{athlete.first_name} {athlete.last_name or ''}".strip()
    age = calculate_age(athlete.birth_date, reference_date)
    rating_value = athlete.rating if athlete.rating is not None else "N.D."
    return (
        f"{full_name} — {athlete.style} — {athlete.sex} — "
        f"{athlete.default_weight:.1f} kg — "
        f"{get_level_label(athlete.level)} — "
        f"{age} anni — rating {rating_value}"
    )


events = list_events()
all_athletes = list_athletes(include_inactive=False)
all_matches = list_matches()

if not events:
    st.warning("Prima devi creare almeno un evento.")
    st.stop()

if len(all_athletes) < 2:
    st.warning("Servono almeno due atleti attivi.")
    st.stop()

st.subheader("Configurazione")

selected_event = st.selectbox(
    "Evento di riferimento",
    options=events,
    format_func=lambda e: f"{e.name} — {e.event_date}",
)

reference_date = selected_event.event_date

styles = sorted({athlete.style for athlete in all_athletes})
selected_style = st.selectbox("Stile", options=styles)

style_athletes = [athlete for athlete in all_athletes if athlete.style == selected_style]

if len(style_athletes) < 2:
    st.warning("Non ci sono abbastanza atleti attivi per questo stile.")
    st.stop()

sex_options = sorted({athlete.sex for athlete in style_athletes})
selected_sexes = st.multiselect("Sesso", options=sex_options, default=sex_options)

filtered_pool = [athlete for athlete in style_athletes if athlete.sex in selected_sexes]

if len(filtered_pool) < 2:
    st.warning("I filtri correnti lasciano meno di due atleti.")
    st.stop()

min_age = min(calculate_age(a.birth_date, reference_date) for a in filtered_pool)
max_age = max(calculate_age(a.birth_date, reference_date) for a in filtered_pool)

min_weight = min(float(a.default_weight) for a in filtered_pool)
max_weight = max(float(a.default_weight) for a in filtered_pool)

col1, col2 = st.columns(2)

with col1:
    if min_age == max_age:
        st.caption(f"Età disponibile: {min_age}")
        selected_age_range = (min_age, max_age)
    else:
        selected_age_range = st.slider(
            "Fascia età",
            min_value=min_age,
            max_value=max_age,
            value=(min_age, max_age),
            step=1,
        )

    max_pair_weight_diff = st.number_input(
        "Differenza peso massima per coppia (kg)",
        min_value=0.0,
        max_value=50.0,
        value=10.0,
        step=0.5,
    )

    max_pair_level_diff = st.number_input(
        "Differenza level massima per coppia",
        min_value=0,
        max_value=10,
        value=2,
        step=1,
    )

with col2:
    if min_weight == max_weight:
        st.caption(f"Peso disponibile: {min_weight:.1f} kg")
        selected_weight_range = (min_weight, max_weight)
    else:
        selected_weight_range = st.slider(
            "Fascia peso di riferimento (kg)",
            min_value=float(min_weight),
            max_value=float(max_weight),
            value=(float(min_weight), float(max_weight)),
            step=0.5,
        )

    max_pair_age_diff = st.number_input(
        "Differenza età massima per coppia",
        min_value=0,
        max_value=100,
        value=8,
        step=1,
    )

    use_rating = st.checkbox("Usa rating nella compatibilità", value=True)
    avoid_rematches = st.checkbox("Penalizza rematch", value=True)
    same_sex_only = st.checkbox("Accoppia solo atleti dello stesso sesso", value=False)

age_min, age_max = selected_age_range
weight_min, weight_max = selected_weight_range

filtered_pool = [
    athlete
    for athlete in filtered_pool
    if age_min <= calculate_age(athlete.birth_date, reference_date) <= age_max
    and weight_min <= float(athlete.default_weight) <= weight_max
]

if len(filtered_pool) < 2:
    st.warning("Dopo i filtri rimangono meno di due atleti.")
    st.stop()

athlete_options = {athlete.id: athlete_label(athlete, reference_date) for athlete in filtered_pool}

selected_athlete_ids = st.multiselect(
    "Atleti da includere",
    options=list(athlete_options.keys()),
    default=list(athlete_options.keys()),
    format_func=lambda athlete_id: athlete_options[athlete_id],
)

selected_athletes = [athlete for athlete in filtered_pool if athlete.id in selected_athlete_ids]

if len(selected_athletes) < 2:
    st.warning("Seleziona almeno due atleti per generare accoppiamenti.")
    st.stop()

candidates = generate_candidate_pairs(
    athletes=selected_athletes,
    matches=all_matches,
    reference_date=reference_date,
    max_weight_diff=float(max_pair_weight_diff),
    max_level_diff=int(max_pair_level_diff),
    max_age_diff=int(max_pair_age_diff),
    use_rating=use_rating,
    avoid_rematches=avoid_rematches,
    same_sex_only=same_sex_only,
)

if not candidates:
    st.warning("Nessuna coppia valida trovata con i vincoli selezionati.")
    st.stop()

selected_pairs, leftovers = select_greedy_pairings(candidates, selected_athletes)

st.subheader("Accoppiamenti suggeriti")

if not selected_pairs:
    st.info("Nessun accoppiamento selezionabile.")
else:
    selected_rows = []
    for pair in selected_pairs:
        athlete_a = pair["athlete_a"]
        athlete_b = pair["athlete_b"]

        selected_rows.append(
            {
                "Atleta A": f"{athlete_a.first_name} {athlete_a.last_name or ''}".strip(),
                "Atleta B": f"{athlete_b.first_name} {athlete_b.last_name or ''}".strip(),
                "Stile": pair["style"],
                "Δ peso": pair["weight_diff"],
                "Δ level": pair["level_diff"],
                "Δ rating": pair["rating_diff"],
                "Δ età": pair["age_diff"],
                "Precedenti": pair["previous_matches"],
                "Score": pair["score"],
                "Dettaglio": pair["explanation"],
            }
        )

    st.dataframe(pd.DataFrame(selected_rows), use_container_width=True, hide_index=True)

st.subheader("Tutte le coppie candidate")

candidate_rows = []
for pair in candidates:
    athlete_a = pair["athlete_a"]
    athlete_b = pair["athlete_b"]

    candidate_rows.append(
        {
            "Atleta A": f"{athlete_a.first_name} {athlete_a.last_name or ''}".strip(),
            "Atleta B": f"{athlete_b.first_name} {athlete_b.last_name or ''}".strip(),
            "Stile": pair["style"],
            "Peso A": float(athlete_a.default_weight),
            "Peso B": float(athlete_b.default_weight),
            "Level A": get_level_label(athlete_a.level),
            "Level B": get_level_label(athlete_b.level),
            "Rating A": pair["rating_a"],
            "Rating B": pair["rating_b"],
            "Età A": pair["age_a"],
            "Età B": pair["age_b"],
            "Δ peso": pair["weight_diff"],
            "Δ level": pair["level_diff"],
            "Δ rating": pair["rating_diff"],
            "Δ età": pair["age_diff"],
            "Precedenti": pair["previous_matches"],
            "Score": pair["score"],
            "Dettaglio": pair["explanation"],
        }
    )

st.dataframe(pd.DataFrame(candidate_rows), use_container_width=True, hide_index=True)

st.subheader("Atleti senza accoppiamento")

if not leftovers:
    st.success("Tutti gli atleti selezionati hanno ricevuto un accoppiamento.")
else:
    leftover_rows = []
    for athlete in leftovers:
        leftover_rows.append(
            {
                "Atleta": f"{athlete.first_name} {athlete.last_name or ''}".strip(),
                "Sesso": athlete.sex,
                "Stile": athlete.style,
                "Peso": float(athlete.default_weight),
                "Level": get_level_label(athlete.level),
                "Rating": athlete.rating if athlete.rating is not None else "N.D.",
                "Età": calculate_age(athlete.birth_date, reference_date),
            }
        )

    st.dataframe(pd.DataFrame(leftover_rows), use_container_width=True, hide_index=True)

st.caption(
    "Score più basso = matchup migliore. "
    "La selezione finale usa un algoritmo greedy: prende la migliore coppia disponibile, "
    "poi esclude quei due atleti e continua."
)