# pages/6_Admin_Formule.py
import streamlit as st
from datetime import date

from sqlalchemy import select

from src.db_runtime import bootstrap_database_from_state
from src.formula_config_service import (
    load_config,
    get_full_config,
    save_parameters,
    reset_to_defaults,
)
from src.settings import (
    SCORING_SETTINGS,
    MATCHMAKING_SETTINGS,
    RATINGS_SETTINGS,
)
from src.ratings import recompute_ratings, recompute_ratings_from_date
from src.pairing import generate_candidate_pairs
from src.database import get_session
from src.models import Athlete


# Ensure the database is configured and schema exists
bootstrap_database_from_state()

# Load any saved configuration into the in-memory settings dictionaries
load_config()

st.title("Amministrazione formule")
st.markdown(
    """
    In questa pagina puoi personalizzare i parametri utilizzati per le formule di punteggio, rating e matchmaking.
    I valori modificati vengono salvati nel database e applicati immediatamente. Puoi anche ricalcolare i rating
    degli atleti dopo aver cambiato i parametri.
    """
)

# Display formulas for reference
st.subheader("Formula rating (Elo modificato)")
st.markdown(
    r"""
    Il rating di un atleta viene aggiornato dopo ogni incontro secondo la formula:

    $$
    E_A = \frac{1}{1 + 10^{(R_B - R_A)/400}} \quad\quad R'_A = R_A + (K \times I) \times (S_A - E_A)
    $$

    dove:

    - $R_A$ e $R_B$ sono i rating pre-match dei due atleti.
    - $E_A$ è il punteggio atteso per l'atleta A.
    - $S_A$ è il punteggio effettivo (1 per vittoria, 0.5 per pareggio o proporzionale ai punti).
    - $K$ è il `k_factor`.
    - $I$ è l'`impact` del match (normale, ritiro, forfait).
    """,
    unsafe_allow_html=True,
)

st.subheader("Formula matchmaking (indice di disomogeneità)")
st.markdown(
    r"""
    L'indice di disomogeneità tra due atleti A e B è calcolato così:

    $$
    mismatch = (|peso_A - peso_B| \times weight\_factor) +\ \n    (|livello_A - livello_B| \times level\_factor) +\ \n    \left(\frac{|rating_A - rating_B|}{rating\_divisor}\right) +\ \n    (|età_A - età_B| \times age\_factor) +\ \n    (\text{rematch\_count} \times rematch\_penalty)
    $$
    """,
    unsafe_allow_html=True,
)

st.subheader("Formula punteggio")
st.markdown(
    r"""
    Il punteggio assegnato a ciascun atleta in un match è:

    $$
    punteggio = (\text{base\_points} + \text{performance\_bonus}) \times weight\_factor \times special\_factor
    $$

    dove `base_points` dipende dal risultato (vittoria/sconfitta/ritiro/forfait) e `performance_bonus`
    è proporzionale ai punti tecnici realizzati.
    """,
    unsafe_allow_html=True,
)

# Retrieve current configuration (defaults merged with DB values)
config = get_full_config()

# Build the form for parameter editing
with st.form(key="config_form"):
    st.header("Parametri Scoring (punti)")
    scoring_inputs = {}
    for key, default in config.get("scoring", {}).items():
        # user-friendly label
        label = key.replace("_", " ").capitalize()
        scoring_inputs[key] = st.number_input(
            label,
            value=float(default),
            format="%.3f",
        )

    st.header("Parametri Matchmaking")
    matchmaking_inputs = {}
    for key, default in config.get("matchmaking", {}).items():
        label = key.replace("_", " ").capitalize()
        # booleans as checkboxes, integers as integer inputs, floats as floats
        if isinstance(default, bool):
            matchmaking_inputs[key] = st.checkbox(label, value=bool(default))
        elif isinstance(default, int) and not isinstance(default, bool):
            matchmaking_inputs[key] = st.number_input(
                label,
                value=int(default),
                step=1,
                format="%d",
            )
        else:
            matchmaking_inputs[key] = st.number_input(
                label,
                value=float(default),
                format="%.3f",
            )

    st.header("Parametri Rating")
    ratings_inputs = {}
    for key, default in config.get("ratings", {}).items():
        # skip non-editable structures like level_start_ratings
        if key == "level_start_ratings":
            continue
        label = key.replace("_", " ").capitalize()
        if isinstance(default, int) and not isinstance(default, bool):
            ratings_inputs[key] = st.number_input(
                label,
                value=int(default),
                step=1,
                format="%d",
            )
        else:
            ratings_inputs[key] = st.number_input(
                label,
                value=float(default),
                format="%.3f",
            )

    st.header("Opzioni")
    recalc = st.checkbox("Ricalcola rating dopo il salvataggio", value=False)
    recalc_scope = "Completo"
    if recalc:
        recalc_scope = st.radio(
            "Ambito ricalcolo rating",
            options=["Completo", "Solo dai match futuri"],
            horizontal=True,
        )
    preview = st.checkbox(
        "Mostra anteprima mismatch su due atleti campione", value=False
    )

    submit = st.form_submit_button("Salva parametri")
    reset = st.form_submit_button("Ripristina valori default")

if reset:
    reset_to_defaults()
    st.warning("Tutti i parametri sono stati ripristinati ai valori di default.")
    st.stop()

if submit:
    values = {
        "scoring": scoring_inputs,
        "matchmaking": matchmaking_inputs,
        "ratings": ratings_inputs,
    }
    save_parameters(values)
    st.success("Parametri salvati.")
    if recalc:
        if recalc_scope == "Completo":
            recompute_ratings()
            st.info("Rating ricalcolati completamente.")
        else:
            recompute_ratings_from_date(date.today())
            st.info("Rating ricalcolati solo per i match futuri.")
    # reload the configuration into in-memory settings
    load_config()

if preview:
    # Preview mismatch index for a pair of active athletes
    session = get_session()
    try:
        athletes: list[Athlete] = list(
            session.scalars(select(Athlete).where(Athlete.active == True)).all()
        )

        if len(athletes) >= 2:
            sample_athletes: list[Athlete] = athletes[:2]

            max_weight_diff = float(
                matchmaking_inputs.get(
                    "max_weight_diff_default",
                    config["matchmaking"]["max_weight_diff_default"],
                )
            )
            max_level_diff = int(
                matchmaking_inputs.get(
                    "max_level_diff_default",
                    config["matchmaking"]["max_level_diff_default"],
                )
            )

            raw_max_age_diff = matchmaking_inputs.get(
                "max_age_diff_default",
                config["matchmaking"]["max_age_diff_default"],
            )
            max_age_diff = None if raw_max_age_diff is None else int(raw_max_age_diff)

            use_rating = bool(
                matchmaking_inputs.get(
                    "use_rating_default",
                    config["matchmaking"]["use_rating_default"],
                )
            )
            avoid_rematches = bool(
                matchmaking_inputs.get(
                    "avoid_rematches_default",
                    config["matchmaking"]["avoid_rematches_default"],
                )
            )
            same_sex_only = bool(
                matchmaking_inputs.get(
                    "same_sex_only_default",
                    config["matchmaking"]["same_sex_only_default"],
                )
            )

            sample_pairs = generate_candidate_pairs(
                athletes=sample_athletes,
                matches=[],
                reference_date=date.today(),
                max_weight_diff=max_weight_diff,
                max_level_diff=max_level_diff,
                max_age_diff=max_age_diff,
                use_rating=use_rating,
                avoid_rematches=avoid_rematches,
                same_sex_only=same_sex_only,
            )

            if sample_pairs:
                row = sample_pairs[0]
                st.subheader("Anteprima mismatch index")
                st.write(
                    f"{row['athlete_a'].first_name} vs {row['athlete_b'].first_name}"
                )
                st.json(
                    {
                        "weight_diff": row["weight_diff"],
                        "level_diff": row["level_diff"],
                        "rating_diff": row["rating_diff"],
                        "age_diff": row["age_diff"],
                        "previous_matches": row["previous_matches"],
                        "mismatch_index": row["mismatch_index"],
                        "components": {
                            "weight_component": row["weight_component"],
                            "level_component": row["level_component"],
                            "rating_component": row["rating_component"],
                            "age_component": row["age_component"],
                            "rematch_penalty": row["rematch_penalty"],
                        },
                    }
                )
        else:
            st.info(
                "Non ci sono almeno due atleti attivi nel database per mostrare l'anteprima."
            )
    finally:
        session.close()