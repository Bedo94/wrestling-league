# Rating dinamico

## Cos'è il rating dinamico

Il rating dinamico è una misura quantitativa e in continuo aggiornamento della
forza competitiva di ogni atleta. Differisce dal **level** perché non è
assegnato manualmente e non è stabile nel tempo: il rating si aggiorna dopo
ogni incontro in base ai risultati ottenuti.

## Differenze tra level e rating

- **Level**: categoria assegnata manualmente o federale. Non cambia se non
  quando l'atleta viene promosso o retrocesso. È qualitativo e serve a
  posizionare l'atleta in una fascia iniziale (1–4 nella configurazione
  attuale).
- **Rating**: valore numerico calcolato automaticamente. Parte da un
  **seed iniziale** determinato dal level e viene aggiornato dopo ogni
  match. È dinamico e riflette meglio l'andamento degli atleti nel tempo.

## Seed iniziale

Per evitare che tutti partano dal medesimo punteggio, a ogni level è
associato un punteggio di partenza:contentReference[oaicite:5]{index=5}:

| Level | Rating iniziale |
|------:|----------------:|
|     1 | 900.0          |
|     2 | 1000.0         |
|     3 | 1100.0         |
|     4 | 1200.0         |

Se un atleta non ha level specificato o il level non è presente nel mapping,
viene usato il valore di default (`1000.0`).

## Formula di aggiornamento

Il rating viene ricalcolato passando in rassegna tutti i match in ordine
cronologico (per data dell'evento). Per ciascun match si utilizzano i
seguenti passi:

1. **Rating correnti**: si recuperano i rating attuali degli atleti A e B.
2. **Punteggio atteso**: si stima, secondo una logica Elo, quanto ci si
   aspetta che ogni atleta ottenga in base ai rating correnti:
