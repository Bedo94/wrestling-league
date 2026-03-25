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
