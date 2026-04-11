from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd
import streamlit as st
from sqlalchemy import select

from src.admin_formulas_shared import (
    apply_pending_reset,
    format_athlete_preview_label,
    get_formula_draft_config,
    queue_group_reset,
    reset_formula_group_draft,
    render_flash_message,
    render_group_inputs,
    save_formula_group_draft,
    set_flash_message,
)
from src.database import get_session
from src.matches import recompute_all_match_scores
from src.models import Athlete
from src.ratings import build_current_rating_map, recompute_ratings
from src.scoring import calculate_match_points, get_age_at_event


def render_scoring_tab() -> None:
    config = get_formula_draft_config()
    scoring_config: dict[str, Any] = config.get("scoring", {})

    apply_pending_reset("scoring", "scoring")

    st.subheader("Formula punteggio")

    st.info(
        """
Lo scoring calcola i **punti classifica** assegnati ai due atleti dopo ogni match.

Questi punti:
- alimentano direttamente la classifica atleti
- influenzano indirettamente anche la classifica team
- sono separati dal rating, che invece serve a stimare forza competitiva e matchmaking
"""
    )

    st.markdown(
        r"""
Il punteggio assegnato a ciascun atleta in un match è:

$$
punteggio =
(\text{base\_points} + \text{performance\_bonus} + \text{finish\_bonus})
\times weight\_factor
\times special\_factor
$$
"""
    )

    with st.expander("Interpretazione intuitiva dei parametri"):
        st.markdown(
            r"""
### Base points
I `base_points` dipendono dal risultato:
- vittoria normale → `winner_base_points`
- sconfitta normale → `loser_base_points`
- ritiro → `retirement_winner_base_points` / `retirement_loser_base_points`
- forfait → `forfeit_winner_base_points` / `forfeit_loser_base_points`

### Performance bonus
Misura quanto l'atleta ha prodotto tecnicamente rispetto all'avversario:

$$
performance\_bonus =
\frac{raw\_score}{raw\_score + opponent\_raw\_score}
\times performance\_bonus\_max
$$

### Finish bonus
Dipende dal tipo di vittoria:
- `Punti` → `points_finish_bonus`
- `Schienamento` → `pinfall_finish_bonus`
- `Ritiro` → `retirement_finish_bonus`
- `Forfait` → `forfeit_finish_bonus`

### Weight factor
Il `weight_factor` dipende dalla differenza di peso rispetto all'avversario:

$$
weight\_factor = 1 + ((peso\_avversario - peso\_proprio) \times weight\_bonus\_per\_kg)
$$

Interpretazione:
- se affronti un atleta più pesante, il tuo fattore aumenta
- se affronti un atleta più leggero, il tuo fattore diminuisce
- il valore finale viene limitato tra `0.5` e `1.5`

Se la differenza di peso supera `max_weight_diff_kg`, il match non è valido per il calcolo.

### Special factor
Applica `special_bonus_factor` se l'atleta è femmina oppure minorenne e affronta un maschio adulto.
Negli altri casi vale `1.0`.
"""
        )

    scoring_order = [
        "max_weight_diff_kg",
        "weight_bonus_per_kg",
        "winner_base_points",
        "loser_base_points",
        "performance_bonus_max",
        "points_finish_bonus",
        "pinfall_finish_bonus",
        "retirement_finish_bonus",
        "forfeit_finish_bonus",
        "minor_age_threshold",
        "special_bonus_factor",
        "retirement_winner_base_points",
        "retirement_loser_base_points",
        "forfeit_winner_base_points",
        "forfeit_loser_base_points",
    ]

    with st.expander("Parametri scoring", expanded=False):
        with st.form("scoring_form"):
            scoring_inputs = render_group_inputs(scoring_config, scoring_order, "scoring")

            col1, col2 = st.columns(2)
            save_and_apply_clicked = col1.form_submit_button("Salva e applica scoring")
            reset_clicked = col2.form_submit_button("Ripristina default scoring")

    if save_and_apply_clicked:
        save_formula_group_draft("scoring", scoring_inputs)
        try:
            updated_matches = recompute_all_match_scores()
            recompute_ratings()
            set_flash_message(
                "success",
                "Parametri scoring applicati. "
                f"Ricalcolati {updated_matches} match e aggiornati anche i rating.",
                target="scoring",
            )
        except ValueError as exc:
            set_flash_message(
                "error",
                f"Parametri scoring salvati ma ricalcolo interrotto: {exc}",
                target="scoring",
            )
        st.rerun()

    if reset_clicked:
        reset_formula_group_draft("scoring")
        queue_group_reset("scoring", "scoring")
        set_flash_message(
            "warning",
            "Parametri scoring della bozza ripristinati ai valori di default.",
            target="scoring",
        )
        st.rerun()

    st.divider()
    st.subheader("Anteprima scoring")

    session = get_session()
    try:
        athletes: list[Athlete] = list(
            session.scalars(select(Athlete).where(Athlete.active == True)).all()
        )
    finally:
        session.close()

    if len(athletes) < 2:
        st.info("Servono almeno due atleti attivi per mostrare l'anteprima.")
        render_flash_message("scoring")
        return

    athlete_options = {
        a.id: format_athlete_preview_label(a, date.today())
        for a in athletes
    }
    athlete_ids = list(athlete_options.keys())

    default_b_index = 1 if len(athlete_ids) > 1 else 0

    col1, col2 = st.columns(2)
    with col1:
        athlete_a_id = st.selectbox(
            "Atleta A",
            options=athlete_ids,
            format_func=lambda athlete_id: athlete_options[athlete_id],
            key="scoring_preview_athlete_a",
        )
    with col2:
        athlete_b_id = st.selectbox(
            "Atleta B",
            options=athlete_ids,
            format_func=lambda athlete_id: athlete_options[athlete_id],
            key="scoring_preview_athlete_b",
            index=default_b_index,
        )

    if athlete_a_id == athlete_b_id:
        st.warning("Seleziona due atleti diversi per l'anteprima.")
        render_flash_message("scoring")
        return

    athlete_by_id = {a.id: a for a in athletes}
    athlete_a = athlete_by_id[athlete_a_id]
    athlete_b = athlete_by_id[athlete_b_id]
    rating_by_athlete_id = build_current_rating_map()

    st.caption(
        "La data evento serve anche per calcolare l'età degli atleti: "
        "le età mostrate nelle combobox e nell'anteprima sono riferite a questa data."
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        event_date = st.date_input(
            "Data evento",
            value=date.today(),
            format="DD/MM/YYYY",
            key="scoring_preview_event_date",
        )
    with col2:
        win_type = st.selectbox(
            "Tipo vittoria",
            options=["Punti", "Schienamento", "Ritiro", "Forfait"],
            key="scoring_preview_win_type",
        )
    with col3:
        winner_side = st.selectbox(
            "Vincitore",
            options=["Atleta A", "Atleta B"],
            key="scoring_preview_winner_side",
        )

    col4, col5 = st.columns(2)
    with col4:
        weight_a = st.number_input(
            "Peso usato atleta A (kg)",
            min_value=1.0,
            max_value=300.0,
            value=float(athlete_a.default_weight),
            step=0.5,
            key="scoring_preview_weight_a",
        )
        raw_score_a = st.number_input(
            "Punti tecnici atleta A",
            min_value=0.0,
            value=0.0,
            step=1.0,
            key="scoring_preview_raw_score_a",
        )
    with col5:
        weight_b = st.number_input(
            "Peso usato atleta B (kg)",
            min_value=1.0,
            max_value=300.0,
            value=float(athlete_b.default_weight),
            step=0.5,
            key="scoring_preview_weight_b",
        )
        raw_score_b = st.number_input(
            "Punti tecnici atleta B",
            min_value=0.0,
            value=0.0,
            step=1.0,
            key="scoring_preview_raw_score_b",
        )

    athlete_a_name = f"{athlete_a.first_name} {athlete_a.last_name or ''}".strip()
    athlete_b_name = f"{athlete_b.first_name} {athlete_b.last_name or ''}".strip()

    athlete_info_df = pd.DataFrame(
        [
            {
                "Atleta": athlete_a_name,
                "Stile": athlete_a.style,
                "Sesso": athlete_a.sex,
                "Età evento": get_age_at_event(athlete_a.birth_date, event_date),
                "Peso usato": float(weight_a),
                "Level": int(athlete_a.level),
                "Rating": (
                    rating_by_athlete_id[athlete_a.id]
                    if athlete_a.id in rating_by_athlete_id
                    else "N.D."
                ),
                "Team": athlete_a.team or "",
            },
            {
                "Atleta": athlete_b_name,
                "Stile": athlete_b.style,
                "Sesso": athlete_b.sex,
                "Età evento": get_age_at_event(athlete_b.birth_date, event_date),
                "Peso usato": float(weight_b),
                "Level": int(athlete_b.level),
                "Rating": (
                    rating_by_athlete_id[athlete_b.id]
                    if athlete_b.id in rating_by_athlete_id
                    else "N.D."
                ),
                "Team": athlete_b.team or "",
            },
        ]
    )

    st.write("**Atleti selezionati**")
    st.table(athlete_info_df)

    winner_id = athlete_a.id if winner_side == "Atleta A" else athlete_b.id

    try:
        preview = calculate_match_points(
            athlete_a_id=athlete_a.id,
            athlete_b_id=athlete_b.id,
            winner_id=winner_id,
            win_type=win_type,
            weight_a=float(weight_a),
            weight_b=float(weight_b),
            raw_score_a=float(raw_score_a),
            raw_score_b=float(raw_score_b),
            athlete_a_sex=athlete_a.sex,
            athlete_b_sex=athlete_b.sex,
            athlete_a_birth_date=athlete_a.birth_date,
            athlete_b_birth_date=athlete_b.birth_date,
            event_date=event_date,
        )
    except ValueError as exc:
        st.warning(str(exc))
        render_flash_message("scoring")
        return

    col1, col2 = st.columns(2)
    with col1:
        st.metric(f"Punti finali {athlete_a_name}", preview["total_points_a"])
    with col2:
        st.metric(f"Punti finali {athlete_b_name}", preview["total_points_b"])

    breakdown_df = pd.DataFrame(
        [
            {
                "Atleta": athlete_a_name,
                "Base points": preview["result_base_a"],
                "Performance bonus": preview["performance_bonus_a"],
                "Finish bonus": preview["finish_bonus_a"],
                "Pre-multiplier": preview["pre_multiplier_a"],
                "Weight factor": preview["weight_factor_a"],
                "Special factor": preview["special_factor_a"],
                "Punti finali": preview["total_points_a"],
            },
            {
                "Atleta": athlete_b_name,
                "Base points": preview["result_base_b"],
                "Performance bonus": preview["performance_bonus_b"],
                "Finish bonus": preview["finish_bonus_b"],
                "Pre-multiplier": preview["pre_multiplier_b"],
                "Weight factor": preview["weight_factor_b"],
                "Special factor": preview["special_factor_b"],
                "Punti finali": preview["total_points_b"],
            },
        ]
    )

    st.write("**Scomposizione scoring**")
    st.table(breakdown_df)

    render_flash_message("scoring")
