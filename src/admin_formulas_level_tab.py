from __future__ import annotations

from typing import Any

import streamlit as st

from src.admin_formulas_shared import (
    apply_pending_reset,
    queue_group_reset,
    render_flash_message,
    render_group_inputs,
    set_flash_message,
)
from src.formula_config_service import (
    get_full_config,
    reset_group_to_defaults,
    save_group_parameters,
)
from src.level_evaluation_ui import render_level_assistant


def render_level_evaluation_tab() -> None:
    config = get_full_config()
    level_config: dict[str, Any] = config.get("level_evaluation", {})

    apply_pending_reset("level_evaluation", "level_eval")

    st.subheader("Formula valutazione livello consigliato")

    st.info(
        """
Questa formula non assegna automaticamente il livello dell'atleta.

Serve come **supporto decisionale** per stimare un **livello consigliato**
in base a esperienza, numero di incontri e risultati ottenuti.
"""
    )

    st.markdown(
        r"""
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

    with st.expander("Interpretazione intuitiva dei parametri"):
        st.markdown(
            """
### Esperienza pratica
- `years_component` misura l'anzianità di pratica
- cresce con gli anni, ma si ferma al limite `years_cap`

### Esperienza agonistica
- `matches_component` misura quanta esperienza reale di gara ha accumulato l'atleta
- cresce con il numero di incontri, ma si ferma al limite `matches_cap`

### Risultati sportivi
- `medals_component` misura il valore dei risultati ottenuti
- i `medals_points` dipendono sia dal tipo di medaglia sia dal livello della competizione
- anche questa componente è limitata da `medals_cap`

### Pesi delle componenti
- `years_weight`, `matches_weight` e `medals_weight` decidono quanto incide ciascuna area nel risultato finale

### Soglie finali
L'indice esperienza viene trasformato in livello consigliato tramite le soglie:
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

    with st.expander("Parametri valutazione livello", expanded=False):
        with st.form("level_evaluation_form"):
            level_inputs = render_group_inputs(level_config, level_order, "level_eval")

            col1, col2 = st.columns(2)
            save_clicked = col1.form_submit_button("Salva parametri valutazione livello")
            reset_clicked = col2.form_submit_button("Ripristina default valutazione livello")

    if save_clicked:
        save_group_parameters("level_evaluation", level_inputs)
        set_flash_message(
            "success",
            "Parametri valutazione livello salvati correttamente.",
            target="level_evaluation",
        )
        st.rerun()

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