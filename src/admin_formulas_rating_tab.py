from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd
import streamlit as st
from sqlalchemy import select

from src.admin_formulas_shared import (
    apply_pending_reset,
    format_athlete_preview_label,
    format_winner_fallback_label,
    get_typed_value,
    get_widget_value,
    queue_group_reset,
    render_flash_message,
    render_group_inputs,
    set_flash_message,
)
from src.database import get_session
from src.formula_config_service import (
    get_full_config,
    reset_group_to_defaults,
    save_group_parameters,
)
from src.models import Athlete
from src.pairing import calculate_age
from src.ratings import (
    get_start_rating,
    preview_rating_update,
    recompute_ratings,
)


def render_rating_tab() -> None:
    config = get_full_config()
    rating_config: dict[str, Any] = config.get("ratings", {})

    apply_pending_reset("ratings", "rating")

    current_k_factor = get_typed_value(
        rating_config,
        "k_factor",
        32.0,
        float,
    )
    current_logistic_divisor = get_typed_value(
        rating_config,
        "logistic_divisor",
        400.0,
        float,
    )
    current_normal_match_impact = get_typed_value(
        rating_config,
        "normal_match_impact",
        1.0,
        float,
    )
    current_retirement_match_impact = get_typed_value(
        rating_config,
        "retirement_match_impact",
        0.6,
        float,
    )
    current_forfeit_match_impact = get_typed_value(
        rating_config,
        "forfeit_match_impact",
        0.3,
        float,
    )

    st.subheader("Rating dinamico per matchmaking")

    st.info(
        """
Il rating **non determina la classifica finale**.

Serve invece a:
- stimare chi è favorito tra due atleti
- aggiornare la forza competitiva dopo ogni match
- contribuire al matchmaking e alla probabilità attesa delle anteprime
"""
    )

    st.markdown(
        fr"""
L'aggiornamento rating usa una formula tipo Elo:

$$
E_A = \frac{{1}}{{1 + 10^{{(R_B - R_A)/D}}}}
$$

$$
R'_A = R_A + (K \times I) \times (S_A - E_A)
$$

dove:

- $R_A$ e $R_B$ sono i rating pre-match
- $E_A$ è il punteggio atteso dell'atleta A
- $S_A$ è il punteggio effettivo dell'atleta A
- $K$ è il `k_factor`
- $I$ è l'`impact` del match
- $D$ è il divisore logistico `logistic_divisor = {current_logistic_divisor:g}`
"""
    )

    with st.expander("Interpretazione intuitiva dei parametri"):
        st.markdown(
            """
- **Punteggio atteso `E`**  
  è la stima teorica del risultato contro l'avversario in base ai rating pre-match

- **Punteggio effettivo `S`**  
  nel sistema attuale non è solo vittoria o sconfitta:
  - se il match ha `points_a` e `points_b`, allora  
    `S_A = points_a / (points_a + points_b)` e `S_B = points_b / (points_a + points_b)`
  - se entrambi i punti sono zero, si usa il vincitore come fallback:
    - vittoria A → `1.0 / 0.0`
    - vittoria B → `0.0 / 1.0`
    - nessun vincitore definito → `0.5 / 0.5`

- **K factor**  
  controlla quanto il rating cambia rapidamente:
  - più alto = rating più sensibile
  - più basso = rating più stabile

- **Logistic divisor**  
  controlla quanto la differenza rating polarizza il pronostico:
  - più basso = le probabilità si allontanano prima dal 50/50
  - più alto = il sistema resta più conservativo

- **Impact del match**  
  riduce o amplifica l'effetto dell'incontro:
  - match normale → impatto pieno
  - ritiro → impatto ridotto
  - forfait → impatto ancora più ridotto
"""
        )

    rating_order = [
        "default_start_rating",
        "k_factor",
        "logistic_divisor",
        "normal_match_impact",
        "retirement_match_impact",
        "forfeit_match_impact",
    ]

    with st.expander("Parametri rating", expanded=False):
        with st.form("rating_form"):
            ratings_inputs = render_group_inputs(rating_config, rating_order, "rating")

            if "level_start_ratings" in rating_config:
                level_start_ratings = rating_config["level_start_ratings"]
                if isinstance(level_start_ratings, dict) and level_start_ratings:
                    level_start_df = pd.DataFrame(
                        [
                            {"Level": int(level), "Rating iniziale": float(value)}
                            for level, value in sorted(level_start_ratings.items())
                        ]
                    )
                    st.caption("Rating iniziali per livello")
                    st.dataframe(
                        level_start_df,
                        use_container_width=True,
                        hide_index=True,
                    )
                else:
                    st.caption(
                        f"Valori iniziali per livello (sola lettura): {level_start_ratings}"
                    )

            col1, col2, col3 = st.columns(3)
            save_clicked = col1.form_submit_button("Salva parametri rating")
            save_and_recalc_clicked = col2.form_submit_button("Salva e ricalcola rating")
            reset_clicked = col3.form_submit_button("Ripristina default rating")

    if save_clicked:
        save_group_parameters("ratings", ratings_inputs)
        set_flash_message(
            "success",
            "Parametri rating salvati correttamente.",
            target="ratings",
        )
        st.rerun()

    if save_and_recalc_clicked:
        save_group_parameters("ratings", ratings_inputs)
        recompute_ratings()
        set_flash_message(
            "success",
            "Parametri rating salvati e rating ricalcolati completamente.",
            target="ratings",
        )
        st.rerun()

    if reset_clicked:
        reset_group_to_defaults("ratings")
        queue_group_reset("ratings", "rating")
        set_flash_message(
            "warning",
            "Parametri rating ripristinati ai valori di default.",
            target="ratings",
        )
        st.rerun()

    st.divider()
    st.subheader("Anteprima aggiornamento rating")

    session = get_session()
    try:
        athletes: list[Athlete] = list(
            session.scalars(select(Athlete).where(Athlete.active == True)).all()
        )
    finally:
        session.close()

    if len(athletes) < 2:
        st.info("Servono almeno due atleti attivi per mostrare l'anteprima.")
        render_flash_message("ratings")
        return

    athlete_options = {
        athlete.id: format_athlete_preview_label(athlete, date.today())
        for athlete in athletes
    }
    athlete_ids = list(athlete_options.keys())
    default_b_index = 1 if len(athlete_ids) > 1 else 0

    col1, col2 = st.columns(2)
    with col1:
        athlete_a_id = st.selectbox(
            "Atleta A",
            options=athlete_ids,
            format_func=lambda athlete_id: athlete_options[athlete_id],
            key="rating_preview_athlete_a",
        )
    with col2:
        athlete_b_id = st.selectbox(
            "Atleta B",
            options=athlete_ids,
            format_func=lambda athlete_id: athlete_options[athlete_id],
            key="rating_preview_athlete_b",
            index=default_b_index,
        )

    if athlete_a_id == athlete_b_id:
        st.warning("Seleziona due atleti diversi per l'anteprima.")
        render_flash_message("ratings")
        return

    athlete_by_id = {athlete.id: athlete for athlete in athletes}
    athlete_a = athlete_by_id[athlete_a_id]
    athlete_b = athlete_by_id[athlete_b_id]

    rating_a = float(
        athlete_a.rating
        if athlete_a.rating is not None
        else get_start_rating(int(athlete_a.level))
    )
    rating_b = float(
        athlete_b.rating
        if athlete_b.rating is not None
        else get_start_rating(int(athlete_b.level))
    )

    preview_k_factor = get_widget_value(
        "rating",
        "k_factor",
        current_k_factor,
        float,
    )
    preview_logistic_divisor = get_widget_value(
        "rating",
        "logistic_divisor",
        current_logistic_divisor,
        float,
    )
    preview_normal_match_impact = get_widget_value(
        "rating",
        "normal_match_impact",
        current_normal_match_impact,
        float,
    )
    preview_retirement_match_impact = get_widget_value(
        "rating",
        "retirement_match_impact",
        current_retirement_match_impact,
        float,
    )
    preview_forfeit_match_impact = get_widget_value(
        "rating",
        "forfeit_match_impact",
        current_forfeit_match_impact,
        float,
    )

    st.caption(
        """
Questa anteprima usa i rating correnti dei due atleti.
Se inserisci punti > 0, il punteggio effettivo `S` viene calcolato dalla quota punti.
Se entrambi i punti sono zero, viene usato il vincitore di fallback; se non è definito, il sistema usa `0.5 / 0.5`.
"""
    )

    col1, col2 = st.columns(2)
    with col1:
        win_type = st.selectbox(
            "Tipo match",
            options=["Punti", "Schienamento", "Ritiro", "Forfait"],
            key="rating_preview_win_type",
        )

    winner_options: list[str | None] = [None, "A", "B"]

    with col2:
        winner_side = st.selectbox(
            "Vincitore di fallback (se i punti sono zero)",
            options=winner_options,
            format_func=format_winner_fallback_label,
            key="rating_preview_winner_side",
        )

    col3, col4 = st.columns(2)
    with col3:
        points_a = st.number_input(
            "Punti usati dal rating atleta A",
            min_value=0.0,
            value=0.0,
            step=1.0,
            key="rating_preview_points_a",
        )
    with col4:
        points_b = st.number_input(
            "Punti usati dal rating atleta B",
            min_value=0.0,
            value=0.0,
            step=1.0,
            key="rating_preview_points_b",
        )

    preview = preview_rating_update(
        rating_a=rating_a,
        rating_b=rating_b,
        points_a=float(points_a),
        points_b=float(points_b),
        winner_side=winner_side,
        win_type=win_type,
        k_factor=float(preview_k_factor),
        logistic_divisor=float(preview_logistic_divisor),
        normal_match_impact=float(preview_normal_match_impact),
        retirement_match_impact=float(preview_retirement_match_impact),
        forfeit_match_impact=float(preview_forfeit_match_impact),
    )

    athlete_a_name = f"{athlete_a.first_name} {athlete_a.last_name or ''}".strip()
    athlete_b_name = f"{athlete_b.first_name} {athlete_b.last_name or ''}".strip()

    athlete_info_df = pd.DataFrame(
        [
            {
                "Atleta": athlete_a_name,
                "Stile": athlete_a.style,
                "Sesso": athlete_a.sex,
                "Età": calculate_age(athlete_a.birth_date, date.today()),
                "Level": int(athlete_a.level),
                "Team": athlete_a.team or "",
                "Rating usato": round(rating_a, 2),
                "Rating iniziale livello": round(get_start_rating(int(athlete_a.level)), 2),
            },
            {
                "Atleta": athlete_b_name,
                "Stile": athlete_b.style,
                "Sesso": athlete_b.sex,
                "Età": calculate_age(athlete_b.birth_date, date.today()),
                "Level": int(athlete_b.level),
                "Team": athlete_b.team or "",
                "Rating usato": round(rating_b, 2),
                "Rating iniziale livello": round(get_start_rating(int(athlete_b.level)), 2),
            },
        ]
    )

    st.write("**Atleti selezionati**")
    st.table(athlete_info_df)

    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
    with metric_col1:
        st.metric(
            f"Prob. attesa {athlete_a_name}",
            f"{preview['expected_a'] * 100:.1f}%",
        )
    with metric_col2:
        st.metric(
            f"Prob. attesa {athlete_b_name}",
            f"{preview['expected_b'] * 100:.1f}%",
        )
    with metric_col3:
        st.metric(
            f"Δ rating {athlete_a_name}",
            f"{preview['delta_a']:+.2f}",
        )
    with metric_col4:
        st.metric(
            f"Δ rating {athlete_b_name}",
            f"{preview['delta_b']:+.2f}",
        )

    summary_df = pd.DataFrame(
        [
            {
                "Voce": "Rating iniziale",
                athlete_a_name: round(float(preview["rating_a"]), 2),
                athlete_b_name: round(float(preview["rating_b"]), 2),
            },
            {
                "Voce": "Punteggio atteso E",
                athlete_a_name: round(float(preview["expected_a"]), 4),
                athlete_b_name: round(float(preview["expected_b"]), 4),
            },
            {
                "Voce": "Punteggio effettivo S",
                athlete_a_name: round(float(preview["actual_a"]), 4),
                athlete_b_name: round(float(preview["actual_b"]), 4),
            },
            {
                "Voce": "Delta rating",
                athlete_a_name: round(float(preview["delta_a"]), 2),
                athlete_b_name: round(float(preview["delta_b"]), 2),
            },
            {
                "Voce": "Rating finale",
                athlete_a_name: round(float(preview["new_rating_a"]), 2),
                athlete_b_name: round(float(preview["new_rating_b"]), 2),
            },
        ]
    )

    parameter_df = pd.DataFrame(
        [
            {
                "Parametro": "K factor",
                "Valore": round(float(preview["k_factor"]), 4),
                "Significato": "Sensibilità base del rating",
            },
            {
                "Parametro": "Impact",
                "Valore": round(float(preview["impact"]), 4),
                "Significato": "Peso del tipo di match",
            },
            {
                "Parametro": "K effettivo",
                "Valore": round(float(preview["effective_k"]), 4),
                "Significato": "Prodotto K × impact",
            },
            {
                "Parametro": "Logistic divisor",
                "Valore": round(float(preview["logistic_divisor"]), 4),
                "Significato": "Apre o chiude la forbice delle probabilità attese",
            },
            {
                "Parametro": "Punti input A / B",
                "Valore": f"{float(preview['points_a']):.2f} / {float(preview['points_b']):.2f}",
                "Significato": "Usati per ricavare S quando il totale è > 0",
            },
            {
                "Parametro": "Vincitore fallback",
                "Valore": format_winner_fallback_label(winner_side),
                "Significato": "Usato solo se entrambi i punti sono zero",
            },
        ]
    )

    st.write("**Scomposizione aggiornamento rating**")
    st.table(summary_df)

    st.write("**Parametri applicati nella simulazione**")
    st.table(parameter_df)

    render_flash_message("ratings")