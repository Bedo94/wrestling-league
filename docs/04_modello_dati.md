# Modello dati

## Athlete
Campi principali:
- `id`
- `first_name`
- `last_name`
- `nickname`
- `team`
- `birth_date`
- `sex`
- `style`
- `level`
- `default_weight`
- `rating`
- `active`

## Significato dei campi chiave
### `level`
Stima iniziale manuale del livello tecnico.

Scala attuale:
- 1 = Principiante
- 2 = Base
- 3 = Intermedio
- 4 = Avanzato

Uso previsto:
- supporto iniziale ai matchup
- filtro leggibile nelle classifiche
- seed iniziale del rating

### `rating`
Indicatore dinamico calcolato automaticamente dal sistema.

Uso previsto:
- affinare i matchup
- leggere la forza competitiva osservata nel tempo
- base futura per viste tipo pound-for-pound

### `default_weight`
Peso di riferimento dell'atleta.

Uso previsto:
- filtri classifiche
- base matchmaking
- riferimento iniziale quando non è ancora disponibile un peso più specifico

## Event
Campi principali:
- `id`
- `name`
- `event_date`
- `notes`

Uso:
- raggruppare incontri
- fornire data di riferimento
- permettere letture storiche coerenti

## Match
Campi principali:
- `id`
- `event_id`
- `athlete_a_id`
- `athlete_b_id`
- `style`
- `weight_a`
- `weight_b`
- `level_a`
- `level_b`
- `raw_score_a`
- `raw_score_b`
- `winner_id`
- `win_type`
- `points_a`
- `points_b`
- `notes`

## Perché salvare snapshot nel match
Nel match vengono salvati anche:
- peso dei due atleti
- level dei due atleti
- stile del match

Questo evita che modifiche future all'anagrafica cambino la lettura storica dei match già disputati.

## Team
Attualmente il team è un campo testuale sull'atleta.

Evoluzione possibile:
- tabella dedicata `teams`
- anagrafica team
- filtri e report per team
