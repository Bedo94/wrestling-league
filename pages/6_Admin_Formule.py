import streamlit as st
from datetime import date
from typing import Any

from sqlalchemy import select

from src.db_runtime import bootstrap_database_from_state
from src.formula_config_service import (
    load_config,
    get_full_config,
    save_parameters,
    reset_to_defaults,
)
from src.ratings import recompute_ratings, recompute_ratings_from_date
from src.pairing import generate_candidate_pairs
from src.database import get_session
from src.models import Athlete


bootstrap_database_from_state()
load_config()

st.title("Amministrazione formule")
st.markdown(
    """
    In questa pagina puoi personalizzare i parametri utilizzati per le formule di rating,
    matchmaking e punteggio.

    I valori modificati vengono salvati nel database e applicati immediatamente.
    """
)


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


config = get_full_config()

rating_config: dict[str, Any] = config.get("ratings", {})
matchmaking_config: dict[str, Any] = config.get("matchmaking", {})
scoring_config: dict[str, Any] = config.get("scoring", {})

# ============================================================
# SPIEGAZIONE GENERALE: COME QUESTI VALORI VENGONO USATI
# ============================================================

st.subheader("Come vengono usati nel sistema")
st.markdown(
    """
    **Rating**
    - serve a stimare la forza relativa degli atleti
    - viene aggiornato dopo ogni incontro
    - entra nel matchmaking come uno dei fattori del mismatch
    - viene mostrato nelle classifiche come indicatore dinamico della forza attuale

    **Matchmaking / mismatch**
    - il sistema genera tutte le coppie candidate possibili
    - per ogni coppia calcola un `mismatch_index`
    - più il mismatch è basso, più il match è considerato equilibrato
    - gli accoppiamenti suggeriti vengono scelti privilegiando le coppie con mismatch minore

    **Punteggio**
    - i punti calcolati dal sistema di scoring alimentano la classifica
    - quindi il punteggio incide direttamente sulla posizione in classifica
    - il rating invece non determina da solo la classifica: serve soprattutto come indicatore dinamico e come supporto al matchmaking
    """
)

st.divider()

# ============================================================
# 1. RATING
# ============================================================

st.subheader("1. Formula rating (Elo modificato)")
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

In pratica:
- battere un atleta forte fa salire più del previsto
- perdere contro un atleta debole fa scendere di più
- forfait e ritiro modificano il rating molto meno
"""
)

with st.expander("Spiegazione intuitiva del metodo Elo"):
    st.markdown(
        """
Il metodo Elo nasce negli scacchi per stimare la forza relativa dei giocatori.

L'idea è molto semplice:

1. ogni atleta ha un rating attuale
2. da quei rating si stima quanto ci si aspetta che uno faccia meglio dell'altro
3. dopo il match si confronta il risultato reale con quello atteso
4. il rating viene corretto in base alla differenza

Quindi il rating non misura solo chi vince, ma anche quanto il risultato fosse sorprendente.
Se un atleta sfavorito ottiene un grande risultato, guadagna molto di più.
"""
    )

st.divider()

# ============================================================
# 2. MATCHMAKING
# ============================================================

st.subheader("2. Formula matchmaking (indice di disomogeneità)")
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

**Interpretazione dei parametri**
- `weight_factor`: quanto pesa la differenza di peso
- `level_factor`: quanto pesa la differenza di livello
- `rating_divisor`: rende più o meno influente la differenza rating
- `age_factor`: quanto pesa la differenza di età
- `rematch_penalty`: penalità per chi si è già affrontato
"""
)

st.divider()

# ============================================================
# 3. PUNTEGGIO
# ============================================================

st.subheader("3. Formula punteggio")
st.markdown(
    r"""
Il punteggio assegnato a ciascun atleta in un match è:

$$
punteggio =
(\text{base\_points} + \text{performance\_bonus})
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
Il bonus prestazione è calcolato così:

$$
performance\_bonus = \frac{score}{score + opponent\_score} \times performance\_bonus\_max
$$

Quindi:
- più punti tecnici realizzi rispetto all'avversario, più bonus prendi
- il valore massimo del bonus è `performance_bonus_max`

### Weight factor
Il fattore peso nasce dalla differenza di peso:

$$
weight\_factor = 1 + ((peso\_avversario - peso\_proprio) \times weight\_bonus\_per\_kg)
$$

poi viene limitato tra `0.5` e `1.5`.

### Special factor
Lo `special_factor` vale:
- `special_bonus_factor` se l'atleta è **femmina** oppure **minorenne**
  e affronta un **maschio adulto**
- `1.0` in tutti gli altri casi

Questa regola era nata per dare un bonus nei match considerati più sfavorevoli,
in particolare nei casi **femmina vs maschio adulto** e **minorenne vs maschio adulto**.
"""
)

st.divider()

# ============================================================
# FORM PARAMETRI
# ORDINE: RATING -> MATCHMAKING -> SCORING
# ============================================================

with st.form(key="config_form"):
    st.header("Parametri Rating")
    ratings_inputs: dict[str, Any] = {}

    rating_order = [
        "default_start_rating",
        "k_factor",
        "normal_match_impact",
        "retirement_match_impact",
        "forfeit_match_impact",
    ]

    for key in rating_order:
        if key not in rating_config:
            continue

        default = rating_config[key]
        label = format_label(key)

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

    if "level_start_ratings" in rating_config:
        st.caption(
            f"Valori iniziali per livello (sola lettura): {rating_config['level_start_ratings']}"
        )

    st.header("Parametri Matchmaking")
    matchmaking_inputs: dict[str, Any] = {}

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

    for key in matchmaking_order:
        if key not in matchmaking_config:
            continue

        default = matchmaking_config[key]
        label = format_label(key)

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

    st.header("Parametri Scoring (punti)")
    scoring_inputs: dict[str, Any] = {}

    scoring_order = [
        "max_weight_diff_kg",
        "weight_bonus_per_kg",
        "winner_base_points",
        "loser_base_points",
        "performance_bonus_max",
        "minor_age_threshold",
        "special_bonus_factor",
        "retirement_winner_base_points",
        "retirement_loser_base_points",
        "forfeit_winner_base_points",
        "forfeit_loser_base_points",
    ]

    for key in scoring_order:
        if key not in scoring_config:
            continue

        default = scoring_config[key]
        label = format_label(key)

        if isinstance(default, int) and not isinstance(default, bool):
            scoring_inputs[key] = st.number_input(
                label,
                value=int(default),
                step=1,
                format="%d",
            )
        else:
            scoring_inputs[key] = st.number_input(
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
        "Mostra anteprima mismatch su due atleti campione",
        value=False,
    )

    submit = st.form_submit_button("Salva parametri")
    reset = st.form_submit_button("Ripristina valori default")


if reset:
    reset_to_defaults()
    st.warning("Tutti i parametri sono stati ripristinati ai valori di default.")
    st.stop()


if submit:
    values = {
        "ratings": ratings_inputs,
        "matchmaking": matchmaking_inputs,
        "scoring": scoring_inputs,
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

    load_config()
    config = get_full_config()
    rating_config = config.get("ratings", {})
    matchmaking_config = config.get("matchmaking", {})
    scoring_config = config.get("scoring", {})


if preview:
    session = get_session()
    try:
        athletes: list[Athlete] = list(
            session.scalars(select(Athlete).where(Athlete.active == True)).all()
        )

        if len(athletes) >= 2:
            sample_athletes: list[Athlete] = athletes[:2]

            max_weight_diff = get_typed_value(
                matchmaking_inputs,
                "max_weight_diff_default",
                matchmaking_config["max_weight_diff_default"],
                float,
            )
            max_level_diff = get_typed_value(
                matchmaking_inputs,
                "max_level_diff_default",
                matchmaking_config["max_level_diff_default"],
                int,
            )

            raw_max_age_diff = matchmaking_inputs.get(
                "max_age_diff_default",
                matchmaking_config["max_age_diff_default"],
            )
            max_age_diff = None if raw_max_age_diff is None else int(raw_max_age_diff)

            use_rating = get_typed_value(
                matchmaking_inputs,
                "use_rating_default",
                matchmaking_config["use_rating_default"],
                bool,
            )
            avoid_rematches = get_typed_value(
                matchmaking_inputs,
                "avoid_rematches_default",
                matchmaking_config["avoid_rematches_default"],
                bool,
            )
            same_sex_only = get_typed_value(
                matchmaking_inputs,
                "same_sex_only_default",
                matchmaking_config["same_sex_only_default"],
                bool,
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