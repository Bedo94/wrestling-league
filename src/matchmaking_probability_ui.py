import pandas as pd
import streamlit as st

from src.ratings import expected_score


def build_win_probability_metrics(
    *,
    athlete_a_name: str,
    athlete_b_name: str,
    rating_a: float | None,
    rating_b: float | None,
) -> dict:
    safe_rating_a = float(rating_a or 0.0)
    safe_rating_b = float(rating_b or 0.0)

    expected_a = expected_score(safe_rating_a, safe_rating_b)
    expected_b = 1.0 - expected_a

    return {
        "rating_a": safe_rating_a,
        "rating_b": safe_rating_b,
        "expected_a": expected_a,
        "expected_b": expected_b,
        "label_a": f"Prob. attesa {athlete_a_name}",
        "label_b": f"Prob. attesa {athlete_b_name}",
    }


def render_win_probability_metrics(
    *,
    athlete_a_name: str,
    athlete_b_name: str,
    rating_a: float | None,
    rating_b: float | None,
    mismatch_index: float | None = None,
    previous_matches: int | None = None,
) -> None:
    prob = build_win_probability_metrics(
        athlete_a_name=athlete_a_name,
        athlete_b_name=athlete_b_name,
        rating_a=rating_a,
        rating_b=rating_b,
    )

    if mismatch_index is not None and previous_matches is not None:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Mismatch index", mismatch_index)
        with col2:
            st.metric("Precedenti incontri", previous_matches)
        with col3:
            st.metric(prob["label_a"], f"{prob['expected_a'] * 100:.1f}%")
        with col4:
            st.metric(prob["label_b"], f"{prob['expected_b'] * 100:.1f}%")
    else:
        col1, col2 = st.columns(2)
        with col1:
            st.metric(prob["label_a"], f"{prob['expected_a'] * 100:.1f}%")
        with col2:
            st.metric(prob["label_b"], f"{prob['expected_b'] * 100:.1f}%")

    st.caption(
        "Le probabilità attese derivano dal rating Elo: indicano chi è favorito "
        "in base ai rating correnti, mentre il mismatch misura quanto il pairing è equilibrato e adatto."
    )


def build_win_probability_columns(df: pd.DataFrame) -> pd.DataFrame:
    if "rating_a" not in df.columns or "rating_b" not in df.columns:
        return df

    result = df.copy()

    expected_a_values: list[float] = []
    expected_b_values: list[float] = []

    for _, row in result.iterrows():
        rating_a = float(row.get("rating_a") or 0.0)
        rating_b = float(row.get("rating_b") or 0.0)
        expected_a = expected_score(rating_a, rating_b)
        expected_b = 1.0 - expected_a
        expected_a_values.append(round(expected_a * 100, 1))
        expected_b_values.append(round(expected_b * 100, 1))

    result["Prob. A (%)"] = expected_a_values
    result["Prob. B (%)"] = expected_b_values
    return result