from datetime import date
from typing import Any

import pandas as pd
import streamlit as st
from sqlalchemy import select

from src.database import get_session
from src.formula_config_service import (
    get_full_config,
    get_group_defaults,
    load_config,
    reset_group_to_defaults,
    save_group_parameters,
)
from src.level_evaluation_ui import render_level_assistant
from src.models import Athlete, Match
from src.ratings import recompute_ratings
from src.rankings_ui import render_rankings_panel
from src.pairing import calculate_age, generate_candidate_pairs
from src.scoring import calculate_match_points, get_age_at_event
from src.matchmaking_probability_ui import render_win_probability_metrics

FLASH_MESSAGE_KEY = "admin_formulas_flash_message"
PENDING_RESET_GROUP_KEY = "admin_formulas_pending_reset_group"


def format_label(key: str) -> str:
    return key.replace("_", " ").capitalize()


def get_typed_value(
    source: dict[str, Any],
    key: str,
    fallback: Any,
    expected_type: type,
) -> Any:
    raw_value = source.get(key, fallback)

    if expected_type is bool:
        return bool(raw_value)
    if expected_type is int:
        return int(raw_value)
    if expected_type is float:
        return float(raw_value)

    return raw_value


def get_widget_value(
    prefix: str,
    key: str,
    fallback: Any,
    expected_type: type,
) -> Any:
    widget_key = f"{prefix}_{key}"
    raw_value = st.session_state.get(widget_key, fallback)

    if expected_type is bool:
        return bool(raw_value)
    if expected_type is int:
        return int(raw_value)
    if expected_type is float:
        return float(raw_value)

    return raw_value


def set_flash_message(kind: str, text: str, target: str | None = None) -> None:
    st.session_state[FLASH_MESSAGE_KEY] = {
        "kind": kind,
        "text": text,
        "target": target,
    }


def render_flash_message(target: str | None = None) -> None:
    message = st.session_state.get(FLASH_MESSAGE_KEY)
    if not message:
        return

    message_target = message.get("target")

    if target is not None and message_target != target:
        return

    if target is None and message_target is not None:
        return

    kind = message.get("kind", "info")
    text = message.get("text", "")

    if kind == "success":
        st.success(text)
    elif kind == "warning":
        st.warning(text)
    elif kind == "error":
        st.error(text)
    else:
        st.info(text)

    del st.session_state[FLASH_MESSAGE_KEY]


def sync_widget_state(prefix: str, values: dict[str, Any]) -> None:
    for key, value in values.items():
        if isinstance(value, dict):
            continue
        st.session_state[f"{prefix}_{key}"] = value


def queue_group_reset(group: str, prefix: str) -> None:
    st.session_state[PENDING_RESET_GROUP_KEY] = {
        "group": group,
        "prefix": prefix,
    }


def apply_pending_reset(group: str, prefix: str) -> None:
    pending = st.session_state.get(PENDING_RESET_GROUP_KEY)

    if not pending:
        return

    if pending.get("group") != group or pending.get("prefix") != prefix:
        return

    defaults = get_group_defaults(group)
    sync_widget_state(prefix, defaults)
    del st.session_state[PENDING_RESET_GROUP_KEY]


def render_group_inputs(
    config: dict[str, Any],
    order: list[str],
    prefix: str,
) -> dict[str, Any]:
    inputs: dict[str, Any] = {}

    for key in order:
        if key not in config:
            continue

        default = config[key]
        label = format_label(key)
        widget_key = f"{prefix}_{key}"
        widget_exists = widget_key in st.session_state

        if isinstance(default, bool):
            if widget_exists:
                inputs[key] = st.checkbox(
                    label,
                    key=widget_key,
                )
            else:
                inputs[key] = st.checkbox(
                    label,
                    value=bool(default),
                    key=widget_key,
                )

        elif isinstance(default, int) and not isinstance(default, bool):
            if widget_exists:
                inputs[key] = st.number_input(
                    label,
                    step=1,
                    format="%d",
                    key=widget_key,
                )
            else:
                inputs[key] = st.number_input(
                    label,
                    value=int(default),
                    step=1,
                    format="%d",
                    key=widget_key,
                )

        else:
            if widget_exists:
                inputs[key] = st.number_input(
                    label,
                    format="%.3f",
                    key=widget_key,
                )
            else:
                inputs[key] = st.number_input(
                    label,
                    value=float(default),
                    format="%.3f",
                    key=widget_key,
                )

    return inputs


def render_rating_tab() -> None:
    config = get_full_config()
    rating_config: dict[str, Any] = config.get("ratings", {})

    apply_pending_reset("ratings", "rating")

    st.subheader("Formula rating (Elo modificato)")
    st.markdown(
        r"""
Il rating di un atleta viene aggiornato dopo ogni incontro secondo la formula:

$$
E_A = \frac{1}{1 + 10^{(R_B - R_A)/400}}
$$

$$
R'_A = R_A + (K \times I) \times (S_A - E_A)
$$

dove:

- $R_A$ e $R_B$ sono i rating pre-match dei due atleti
- $E_A$ è il punteggio atteso dell'atleta A
- $S_A$ è il punteggio effettivo dell'atleta A
- $K$ è il `k_factor`
- $I$ è l'`impact` del match
"""
    )

    st.markdown(
        """
**Che cos'è il punteggio atteso**
- se due atleti hanno rating simile, il punteggio atteso è vicino a `0.5`
- se A ha rating molto più alto di B, il punteggio atteso di A è vicino a `1.0`
- se A è sfavorito, il suo punteggio atteso è più vicino a `0.0`

**Che cos'è il K factor**
- il `k_factor` controlla quanto il rating è sensibile ai risultati
- più è alto, più il rating cambia rapidamente
- più è basso, più il rating è stabile

**Che cos'è l'impact**
- `normal_match_impact` pesa i match normali
- `retirement_match_impact` riduce l'effetto dei match vinti/perduti per ritiro
- `forfeit_match_impact` riduce ancora di più l'effetto dei forfait
"""
    )

    with st.expander("Spiegazione intuitiva del metodo Elo"):
        st.markdown(
            """
Il metodo Elo nasce negli scacchi.

L'idea è semplice:

1. ogni atleta ha un rating attuale
2. da quei rating si stima il risultato atteso contro un avversario
3. dopo il match si confronta il risultato reale con quello atteso
4. il rating viene corretto in base alla differenza

Quindi:
- se fai meglio del previsto, sali
- se fai peggio del previsto, scendi
- se il risultato era già atteso, il rating cambia poco
"""
        )

    rating_order = [
        "default_start_rating",
        "k_factor",
        "normal_match_impact",
        "retirement_match_impact",
        "forfeit_match_impact",
    ]

    with st.form("rating_form"):
        ratings_inputs = render_group_inputs(rating_config, rating_order, "rating")

        if "level_start_ratings" in rating_config:
            st.caption(
                f"Valori iniziali per livello (sola lettura): {rating_config['level_start_ratings']}"
            )

        col1, col2, col3 = st.columns(3)
        save_clicked = col1.form_submit_button("Salva parametri rating")
        save_and_recalc_clicked = col2.form_submit_button("Salva e ricalcola rating")
        reset_clicked = col3.form_submit_button("Ripristina default rating")

    if save_clicked:
        save_group_parameters("ratings", ratings_inputs)
        load_config()
        st.success("Parametri rating salvati correttamente.")

    if save_and_recalc_clicked:
        save_group_parameters("ratings", ratings_inputs)
        load_config()
        recompute_ratings()
        st.success("Parametri rating salvati e rating ricalcolati completamente.")

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

    render_rankings_panel(
        state_prefix="rating_rankings_preview",
        title="Anteprima classifica",
        show_filters_expanded=False,
        recompute_before_render=False,
    )

    render_flash_message("ratings")


def render_matchmaking_tab() -> None:
    config = get_full_config()
    matchmaking_config: dict[str, Any] = config.get("matchmaking", {})

    apply_pending_reset("matchmaking", "matchmaking")

    st.subheader("Formula matchmaking (indice di disomogeneità)")
    st.markdown(
        r"""
L'indice di disomogeneità tra due atleti A e B è calcolato così:

$$
mismatch =
(|peso_A - peso_B| \times weight\_factor)
+
(|livello_A - livello_B| \times level\_factor)
+
\left(\frac{|rating_A - rating_B|}{rating\_divisor}\right)
+
(|età_A - età_B| \times age\_factor)
+
(\text{rematch\_count} \times rematch\_penalty)
$$
"""
    )

    st.markdown(
        """
**Come viene usato**
- il sistema costruisce le coppie candidate
- calcola il mismatch per ogni coppia
- ordina le coppie dalla migliore alla peggiore
- privilegia quelle con indice più basso
"""
    )

    st.caption(
        "La probabilità attesa di vittoria mostrata nell'anteprima deriva dal rating Elo, non dal mismatch."
    )

    with st.expander("Come viene calcolata la probabilità attesa"):
        st.markdown(
            r"""
    La probabilità attesa usa il **rating Elo** e corrisponde al punteggio atteso:

    $$
    E_A = \frac{1}{1 + 10^{(R_B - R_A)/400}}
    $$

    dove:

    - $R_A$ è il rating dell'atleta A
    - $R_B$ è il rating dell'atleta B
    - $E_A$ è il punteggio atteso di A contro B

    Nel sistema viene mostrato come **probabilità attesa di vittoria**:
    - rating uguali → circa **50% / 50%**
    - rating più alto → probabilità attesa più alta

    Quindi:
    - **mismatch** = quanto l'accoppiamento è equilibrato e adatto
    - **probabilità attesa Elo** = chi è favorito in base ai rating correnti
    """
        )

    matchmaking_order = [
        "max_weight_diff_default",
        "weight_factor",
        "max_level_diff_default",
        "level_factor",
        "use_rating_default",
        "rating_divisor",
        "max_age_diff_default",
        "age_factor",
        "avoid_rematches_default",
        "rematch_penalty",
        "same_sex_only_default",
    ]

    with st.form("matchmaking_form"):
        matchmaking_inputs = render_group_inputs(
            matchmaking_config,
            matchmaking_order,
            "matchmaking",
        )

        st.caption(
            """
**Significato dei parametri logici**
- `use_rating_default`: decide se includere la differenza rating nel mismatch
- `avoid_rematches_default`: decide se penalizzare gli atleti che si sono già affrontati
- `same_sex_only_default`: decide se consentire solo accoppiamenti tra atleti dello stesso sesso
"""
        )

        col1, col2 = st.columns(2)
        save_clicked = col1.form_submit_button("Salva parametri matchmaking")
        reset_clicked = col2.form_submit_button("Ripristina default matchmaking")

    if save_clicked:
        save_group_parameters("matchmaking", matchmaking_inputs)
        load_config()
        st.success("Parametri matchmaking salvati correttamente.")

    if reset_clicked:
        reset_group_to_defaults("matchmaking")
        queue_group_reset("matchmaking", "matchmaking")
        set_flash_message(
            "warning",
            "Parametri matchmaking ripristinati ai valori di default.",
            target="matchmaking",
        )
        st.rerun()

    st.divider()
    st.subheader("Anteprima mismatch")

    session = get_session()
    try:
        athletes: list[Athlete] = list(
            session.scalars(select(Athlete).where(Athlete.active == True)).all()
        )
        matches: list[Match] = list(session.scalars(select(Match)).all())
    finally:
        session.close()

    if len(athletes) < 2:
        st.info("Servono almeno due atleti attivi per mostrare l'anteprima.")
        render_flash_message("matchmaking")
        return

    athlete_options = {
        a.id: f"{a.first_name} {a.last_name or ''}".strip() + f" (id={a.id})"
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
            key="matchmaking_preview_athlete_a",
        )
    with col2:
        athlete_b_id = st.selectbox(
            "Atleta B",
            options=athlete_ids,
            format_func=lambda athlete_id: athlete_options[athlete_id],
            key="matchmaking_preview_athlete_b",
            index=default_b_index,
        )

    if athlete_a_id == athlete_b_id:
        st.warning("Seleziona due atleti diversi per l'anteprima.")
        render_flash_message("matchmaking")
        return

    athlete_by_id = {a.id: a for a in athletes}
    selected_athletes = [athlete_by_id[athlete_a_id], athlete_by_id[athlete_b_id]]

    max_weight_diff = get_widget_value(
        "matchmaking",
        "max_weight_diff_default",
        matchmaking_config["max_weight_diff_default"],
        float,
    )
    max_level_diff = get_widget_value(
        "matchmaking",
        "max_level_diff_default",
        matchmaking_config["max_level_diff_default"],
        int,
    )
    raw_max_age_diff = st.session_state.get(
        "matchmaking_max_age_diff_default",
        matchmaking_config["max_age_diff_default"],
    )
    max_age_diff = None if raw_max_age_diff is None else int(raw_max_age_diff)

    use_rating = get_widget_value(
        "matchmaking",
        "use_rating_default",
        matchmaking_config["use_rating_default"],
        bool,
    )
    avoid_rematches = get_widget_value(
        "matchmaking",
        "avoid_rematches_default",
        matchmaking_config["avoid_rematches_default"],
        bool,
    )
    same_sex_only = get_widget_value(
        "matchmaking",
        "same_sex_only_default",
        matchmaking_config["same_sex_only_default"],
        bool,
    )

    preview_pairs = generate_candidate_pairs(
        athletes=selected_athletes,
        matches=matches,
        reference_date=date.today(),
        max_weight_diff=max_weight_diff,
        max_level_diff=max_level_diff,
        max_age_diff=max_age_diff,
        use_rating=use_rating,
        avoid_rematches=avoid_rematches,
        same_sex_only=same_sex_only,
    )

    if not preview_pairs:
        st.info("Con i parametri attuali questa coppia non genera un accoppiamento valido.")
        render_flash_message("matchmaking")
        return

    row = preview_pairs[0]

    athlete_a = row["athlete_a"]
    athlete_b = row["athlete_b"]

    athlete_a_name = f"{athlete_a.first_name} {athlete_a.last_name or ''}".strip()
    athlete_b_name = f"{athlete_b.first_name} {athlete_b.last_name or ''}".strip()

    athlete_info_df = pd.DataFrame(
        [
            {
                "Atleta": athlete_a_name,
                "Stile": athlete_a.style,
                "Sesso": athlete_a.sex,
                "Età": calculate_age(athlete_a.birth_date, date.today()),
                "Peso": float(athlete_a.default_weight),
                "Level": int(athlete_a.level),
                "Rating": row["rating_a"],
                "Team": athlete_a.team or "",
            },
            {
                "Atleta": athlete_b_name,
                "Stile": athlete_b.style,
                "Sesso": athlete_b.sex,
                "Età": calculate_age(athlete_b.birth_date, date.today()),
                "Peso": float(athlete_b.default_weight),
                "Level": int(athlete_b.level),
                "Rating": row["rating_b"],
                "Team": athlete_b.team or "",
            },
        ]
    )

    st.write("**Atleti selezionati**")
    st.table(athlete_info_df)

    render_win_probability_metrics(
        athlete_a_name=athlete_a_name,
        athlete_b_name=athlete_b_name,
        rating_a=row["rating_a"],
        rating_b=row["rating_b"],
        mismatch_index=row["mismatch_index"],
        previous_matches=row["previous_matches"],
    )

    preview_df = pd.DataFrame(
        [
            {
                "Componente": "Differenza peso",
                "Valore base": f"{row['weight_diff']} kg",
                "Parametro": f"× {matchmaking_config['weight_factor']}",
                "Contributo": row["weight_component"],
            },
            {
                "Componente": "Differenza level",
                "Valore base": row["level_diff"],
                "Parametro": f"× {matchmaking_config['level_factor']}",
                "Contributo": row["level_component"],
            },
            {
                "Componente": "Differenza rating",
                "Valore base": row["rating_diff"],
                "Parametro": (
                    f"÷ {matchmaking_config['rating_divisor']}"
                    if use_rating else "Disattivato"
                ),
                "Contributo": row["rating_component"],
            },
            {
                "Componente": "Differenza età",
                "Valore base": row["age_diff"],
                "Parametro": f"× {matchmaking_config['age_factor']}",
                "Contributo": row["age_component"],
            },
            {
                "Componente": "Rematch penalty",
                "Valore base": row["previous_matches"],
                "Parametro": (
                    f"× {matchmaking_config['rematch_penalty']}"
                    if avoid_rematches else "Disattivato"
                ),
                "Contributo": row["rematch_penalty"],
            },
        ]
    )

    st.write("**Scomposizione mismatch**")
    st.table(preview_df)

    render_flash_message("matchmaking")


def render_scoring_tab() -> None:
    config = get_full_config()
    scoring_config: dict[str, Any] = config.get("scoring", {})

    apply_pending_reset("scoring", "scoring")

    st.subheader("Formula punteggio")
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

    st.markdown(
        r"""
### Base points
I `base_points` dipendono dal risultato:
- vittoria normale → `winner_base_points`
- sconfitta normale → `loser_base_points`
- ritiro → `retirement_winner_base_points` / `retirement_loser_base_points`
- forfait → `forfeit_winner_base_points` / `forfeit_loser_base_points`

### Performance bonus
$$
performance\_bonus =
\frac{raw\_score}{raw\_score + opponent\_raw\_score}
\times performance\_bonus\_max
$$

### Finish bonus
- `Punti` → `points_finish_bonus`
- `Schienamento` → `pinfall_finish_bonus`
- `Ritiro` → `retirement_finish_bonus`
- `Forfait` → `forfeit_finish_bonus`

### Special factor
- `special_bonus_factor` se l'atleta è femmina oppure minorenne e affronta un maschio adulto
- `1.0` in tutti gli altri casi
"""
    )

    st.markdown(
        """
**Come viene usato**
- i punti calcolati da questa formula vanno nella classifica
- quindi questo blocco è quello che incide direttamente sulla posizione finale
- la partecipazione è già valorizzata in modo indiretto, perché più incontri significano più occasioni di accumulare punti
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

    with st.form("scoring_form"):
        scoring_inputs = render_group_inputs(scoring_config, scoring_order, "scoring")

        col1, col2 = st.columns(2)
        save_clicked = col1.form_submit_button("Salva parametri scoring")
        reset_clicked = col2.form_submit_button("Ripristina default scoring")

    if save_clicked:
        save_group_parameters("scoring", scoring_inputs)
        load_config()
        st.success("Parametri scoring salvati correttamente.")

    if reset_clicked:
        reset_group_to_defaults("scoring")
        queue_group_reset("scoring", "scoring")
        set_flash_message(
            "warning",
            "Parametri scoring ripristinati ai valori di default.",
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
        a.id: f"{a.first_name} {a.last_name or ''}".strip() + f" (id={a.id})"
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

    st.caption(
        "Questa anteprima usa i dati anagrafici degli atleti selezionati e ti permette "
        "di simulare il punteggio risultante in base a esito, punteggio tecnico, peso e data evento."
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
                "Rating": athlete_a.rating if athlete_a.rating is not None else "N.D.",
                "Team": athlete_a.team or "",
            },
            {
                "Atleta": athlete_b_name,
                "Stile": athlete_b.style,
                "Sesso": athlete_b.sex,
                "Età evento": get_age_at_event(athlete_b.birth_date, event_date),
                "Peso usato": float(weight_b),
                "Level": int(athlete_b.level),
                "Rating": athlete_b.rating if athlete_b.rating is not None else "N.D.",
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

def render_level_evaluation_tab() -> None:
    config = get_full_config()
    level_config: dict[str, Any] = config.get("level_evaluation", {})

    apply_pending_reset("level_evaluation", "level_eval")

    st.subheader("Formula valutazione livello consigliato")
    st.markdown(
        r"""
Questa formula **non assegna automaticamente** il livello dell'atleta.
Produce un **livello consigliato** come supporto all'inserimento.

L'indice esperienza è:

$$
experience\_index =
years\_component + matches\_component + medals\_component
$$

dove:

$$
years\_component =
\frac{\min(years\_practice, years\_cap)}{years\_cap} \times years\_weight
$$

$$
matches\_component =
\frac{\min(matches\_count, matches\_cap)}{matches\_cap} \times matches\_weight
$$

$$
medals\_component =
\frac{\min(medals\_points, medals\_cap)}{medals\_cap} \times medals\_weight
$$
"""
    )

    st.markdown(
        """
I `medals_points` dipendono da:
- tipo di medaglia (`gold_weight`, `silver_weight`, `bronze_weight`)
- tipo di competizione (`regional_weight`, `coppa_italia_weight`, ecc.)

Le soglie finali producono il livello consigliato:
- sotto `threshold_level_2` → livello 1
- sotto `threshold_level_3` → livello 2
- sotto `threshold_level_4` → livello 3
- sopra → livello 4
"""
    )

    level_order = [
        "years_weight",
        "matches_weight",
        "medals_weight",
        "years_cap",
        "matches_cap",
        "medals_cap",
        "gold_weight",
        "silver_weight",
        "bronze_weight",
        "regional_weight",
        "interregional_weight",
        "national_open_weight",
        "coppa_italia_weight",
        "campionato_italiano_weight",
        "international_weight",
        "threshold_level_2",
        "threshold_level_3",
        "threshold_level_4",
    ]

    with st.form("level_evaluation_form"):
        level_inputs = render_group_inputs(level_config, level_order, "level_eval")

        col1, col2 = st.columns(2)
        save_clicked = col1.form_submit_button("Salva parametri valutazione livello")
        reset_clicked = col2.form_submit_button("Ripristina default valutazione livello")

    if save_clicked:
        save_group_parameters("level_evaluation", level_inputs)
        load_config()
        st.success("Parametri valutazione livello salvati correttamente.")

    if reset_clicked:
        reset_group_to_defaults("level_evaluation")
        queue_group_reset("level_evaluation", "level_eval")
        set_flash_message(
            "warning",
            "Parametri valutazione livello ripristinati ai valori di default.",
            target="level_evaluation",
        )
        st.rerun()

    st.divider()

    render_level_assistant(
        state_prefix="admin_level_preview",
        title="Anteprima livello consigliato",
        show_apply_button=False,
    )

    render_flash_message("level_evaluation")