import pandas as pd
import streamlit as st

from src.level_evaluation import LevelEvaluationInput, calculate_level_evaluation
from src.levels import get_level_label


def _key(prefix: str, name: str) -> str:
    return f"{prefix}_{name}"


def _render_medal_inputs(
    *,
    state_prefix: str,
    group_key: str,
    title: str,
) -> tuple[int, int, int]:
    st.markdown(f"**{title}**")

    col1, col2, col3 = st.columns(3)

    with col1:
        gold = st.number_input(
            "Ori",
            min_value=0,
            step=1,
            value=0,
            key=_key(state_prefix, f"{group_key}_gold"),
        )

    with col2:
        silver = st.number_input(
            "Argenti",
            min_value=0,
            step=1,
            value=0,
            key=_key(state_prefix, f"{group_key}_silver"),
        )

    with col3:
        bronze = st.number_input(
            "Bronzi",
            min_value=0,
            step=1,
            value=0,
            key=_key(state_prefix, f"{group_key}_bronze"),
        )

    return int(gold), int(silver), int(bronze)


@st.fragment
def render_level_assistant(
    *,
    state_prefix: str,
    title: str | None = None,
    show_apply_button: bool = False,
    apply_target_session_key: str | None = None,
    apply_button_label: str = "Usa livello consigliato",
) -> dict:
    if title:
        st.subheader(title)

    st.caption(
        "Assistente compatto per stimare il livello iniziale dell'atleta. "
        "Il risultato è un suggerimento, non una modifica automatica."
    )

    col1, col2 = st.columns(2)

    with col1:
        years_practice = st.number_input(
            "Anni di pratica",
            min_value=0,
            step=1,
            value=0,
            key=_key(state_prefix, "years_practice"),
        )

    with col2:
        matches_count = st.number_input(
            "Numero gare disputate",
            min_value=0,
            step=1,
            value=0,
            key=_key(state_prefix, "matches_count"),
        )

    tab_regional, tab_interregional, tab_national, tab_coppa, tab_italiani, tab_international = st.tabs(
        [
            "Regionali",
            "Interregionali",
            "Nazionali open",
            "Coppa Italia",
            "Camp. italiani",
            "Internazionali",
        ]
    )

    with tab_regional:
        regional_gold, regional_silver, regional_bronze = _render_medal_inputs(
            state_prefix=state_prefix,
            group_key="regional",
            title="Risultati regionali",
        )

    with tab_interregional:
        interregional_gold, interregional_silver, interregional_bronze = _render_medal_inputs(
            state_prefix=state_prefix,
            group_key="interregional",
            title="Risultati interregionali",
        )

    with tab_national:
        national_open_gold, national_open_silver, national_open_bronze = _render_medal_inputs(
            state_prefix=state_prefix,
            group_key="national_open",
            title="Risultati nazionali open",
        )

    with tab_coppa:
        coppa_italia_gold, coppa_italia_silver, coppa_italia_bronze = _render_medal_inputs(
            state_prefix=state_prefix,
            group_key="coppa_italia",
            title="Risultati Coppa Italia",
        )

    with tab_italiani:
        campionato_italiano_gold, campionato_italiano_silver, campionato_italiano_bronze = _render_medal_inputs(
            state_prefix=state_prefix,
            group_key="campionato_italiano",
            title="Risultati campionati italiani",
        )

    with tab_international:
        international_gold, international_silver, international_bronze = _render_medal_inputs(
            state_prefix=state_prefix,
            group_key="international",
            title="Risultati internazionali",
        )

    evaluation_input = LevelEvaluationInput(
        years_practice=int(years_practice),
        matches_count=int(matches_count),
        regional_gold=regional_gold,
        regional_silver=regional_silver,
        regional_bronze=regional_bronze,
        interregional_gold=interregional_gold,
        interregional_silver=interregional_silver,
        interregional_bronze=interregional_bronze,
        national_open_gold=national_open_gold,
        national_open_silver=national_open_silver,
        national_open_bronze=national_open_bronze,
        coppa_italia_gold=coppa_italia_gold,
        coppa_italia_silver=coppa_italia_silver,
        coppa_italia_bronze=coppa_italia_bronze,
        campionato_italiano_gold=campionato_italiano_gold,
        campionato_italiano_silver=campionato_italiano_silver,
        campionato_italiano_bronze=campionato_italiano_bronze,
        international_gold=international_gold,
        international_silver=international_silver,
        international_bronze=international_bronze,
    )

    evaluation = calculate_level_evaluation(evaluation_input)
    suggested_level_label = get_level_label(evaluation["suggested_level"])

    col1, col2 = st.columns(2)

    with col1:
        st.metric("Experience index", evaluation["experience_index"])

    with col2:
        st.metric("Livello consigliato", suggested_level_label)

    breakdown_df = pd.DataFrame(
        [
            {"Componente": "Anni di pratica", "Valore": evaluation["years_component"]},
            {"Componente": "Numero gare", "Valore": evaluation["matches_component"]},
            {"Componente": "Punti risultati", "Valore": evaluation["medals_points"]},
            {"Componente": "Componente risultati", "Valore": evaluation["medals_component"]},
        ]
    )

    st.table(breakdown_df)

    if show_apply_button and apply_target_session_key:
        if st.button(
            apply_button_label,
            key=_key(state_prefix, "apply_suggested_level"),
        ):
            st.session_state[apply_target_session_key] = suggested_level_label
            st.rerun()

    return evaluation
