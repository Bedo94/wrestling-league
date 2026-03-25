# Matchmaking

## Obiettivo

Il modulo di matchmaking suggerisce coppie di atleti per i prossimi incontri
basandosi su criteri di equilibrio e compatibilità. Non impone i match:
presenta una classifica di accoppiamenti e lascia all'utente la decisione
finale.

## Logica generale

L'algoritmo segue due fasi:

1. **Generazione delle coppie candidate** – tutte le combinazioni di atleti
   che rispettano una serie di vincoli rigidi.
2. **Selezione greedy** – a partire dalle coppie ordinate per indice di
   mismatch (dal più basso al più alto), seleziona le migliori disponibili
   evitando di riutilizzare lo stesso atleta.

## Vincoli rigidi

Una coppia è considerata valida se soddisfa tutte le seguenti condizioni:

- **Atleti distinti**: un atleta non può essere accoppiato con sé stesso.
- **Stesso stile**: entrambi praticano lo stesso stile di lotta.
- **Differenza di peso limitata**: `|peso_A − peso_B|` non supera
  `max_weight_diff` (di default 10 kg).
- **Differenza di level limitata**: `|level_A − level_B|` non supera
  `max_level_diff` (di default 2).
- **Differenza di età limitata**: se `max_age_diff` è impostato, la
  differenza d'età calcolata alla data dell'evento non deve superarla.
- **Stesso sesso** (opzionale): se attivato, vengono generati solo match
  tra atleti dello stesso sesso.

Il parametro `use_rating` controlla se la differenza di rating viene
considerata nell'indice di mismatch e `avoid_rematches` permette di
penalizzare o ignorare gli incontri già avvenuti:contentReference[oaicite:8]{index=8}.

## Calcolo dell'indice di mismatch

Per ogni coppia candidata si calcola un **indice di mismatch**, che
rappresenta una penalità cumulativa. Più è alto l'indice, più i due atleti
sono considerati incompatibili. L'indice attuale è la somma di cinque
componenti:

mismatch_index = peso_component + level_component + rating_component + age_component + rematch_penalty


Le componenti sono definite come segue, con i valori di default tratti da
`MATCHMAKING_SETTINGS`:

| Componente         | Formula                                                          | Fattore    |
|--------------------|------------------------------------------------------------------|-----------:|
| **Peso**           | `peso_component = |peso_A − peso_B| × weight_factor`             | `3.0`     |
| **Level**          | `level_component = |level_A − level_B| × level_factor`           | `8.0`     |
| **Rating**         | `rating_component = |rating_A − rating_B| / rating_divisor`      | divisore `20.0` |
| **Età**            | `age_component = |età_A − età_B| × age_factor`                   | `1.0`     |
| **Rematch**        | `rematch_penalty = (#precedenti) × rematch_penalty`             | `15.0`    |

* `weight_factor`, `level_factor`, `age_factor` e `rematch_penalty` sono
  coefficienti moltiplicativi. Un fattore più alto implica che la
  differenza corrispondente pesa di più nell'indice totale.
* `rating_divisor` è usato come divisore: la differenza di rating è
  normalizzata dividendo per 20 in modo che, ad esempio, 100 punti di
  distacco corrispondano a 5 punti di mismatch.
* Il numero di precedenti è il numero di incontri già disputati tra i due
  atleti; se i rematch devono essere evitati, ogni precedente aggiunge una
  penalità fissa (`15.0`).

Grazie a questo schema lineare l'indice di mismatch è facilmente
interpretabile: la coppia con indice più basso è quella più equilibrata:contentReference[oaicite:9]{index=9}.

## Selezione delle coppie suggerite

Una volta calcolato il mismatch per tutte le coppie candidate, l'algoritmo
procede così:

1. **Ordinamento**: le coppie vengono ordinate per `mismatch_index`. In
   caso di parità si ordinano in base alla differenza di peso, poi al
   level e infine al rating.
2. **Greedy pick**: si scorre l'elenco e si selezionano le coppie una alla
   volta, saltando quelle che coinvolgono atleti già abbinati. Questa
   procedura massimizza il numero di match suggeriti mantenendo basso il
   mismatch.
3. **Leftovers**: gli atleti non accoppiati restano disponibili e
   potranno essere abbinati manualmente o in ulteriori round.

Il risultato della funzione `select_greedy_pairings` è quindi un elenco di
coppie suggerite e un elenco di atleti rimasti senza accoppiamento.

## Parametri configurabili

Tutti i coefficienti e le soglie utilizzate (differenza di peso massima,
fattore peso, fattore level, divisore rating, fattore età,
penalità rematch, soglie predefinite, ecc.) sono definiti nel dizionario
`MATCHMAKING_SETTINGS` in `src/settings.py`. Esempi:

- `max_weight_diff_default = 10.0`
- `weight_factor = 3.0`
- `level_factor = 8.0`
- `rating_divisor = 20.0`
- `age_factor = 1.0`
- `rematch_penalty = 15.0`
- `max_level_diff_default = 2`
- `max_age_diff_default = 8`
- `use_rating_default = True`
- `avoid_rematches_default = True`
- `same_sex_only_default = False`

Tutti questi parametri possono essere modificati per calibrare le
proposte di matchmaking. Una futura pagina amministrativa consentirà di
modificarli senza intervento sul codice.

## Evoluzioni possibili

Il matchmaking attuale è volutamente semplice e trasparente. Possibili
sviluppi futuri includono:

- **Pianificazione degli incontri**: trasformare le coppie suggerite in match
  programmati con stato `scheduled` o `completed`.
- **Uso del peso reale**: considerare il peso effettivamente registrato
  all'ultimo evento piuttosto che il `default_weight`.
- **Preset federali**: applicare automaticamente soglie e fattori diversi in
  base alle categorie ufficiali.
- **Penalità e fattori configurabili**: rendere modificabili via UI i
  coefficienti del mismatch in base alle esigenze della lega.

Il sistema è pensato per essere espandibile mantenendo la leggibilità del
calcolo e la centralizzazione dei parametri.

