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

expected_a = 1 / (1 + 10^((rating_b − rating_a) / 400))
expected_b = 1 − expected_a


La costante 400 è la scala tipica del sistema Elo e può essere
modificata se necessario.
3. **Punteggio reale**: anziché usare un semplice `1` per la vittoria e `0`
per la sconfitta, si sfruttano i punti classifica ottenuti nel match.
Se `points_a` e `points_b` sono i punti classifica dei due atleti (calcolati
con lo scoring), si calcola:contentReference[oaicite:6]{index=6}:

actual_a = points_a / (points_a + points_b)
actual_b = points_b / (points_a + points_b)


Se i punti sono zero (es. match registrato senza punteggio), si
ricade sul modello tradizionale: 1 per il vincitore, 0 per lo sconfitto,
0.5 in caso di pareggio.
4. **Impatto del match**: ogni tipo di match ha un peso diverso nel
calcolo del rating. Attualmente i valori sono:contentReference[oaicite:7]{index=7}:

| Tipo match | impatto |
|-----------|--------:|
| Normale   | 1.0     |
| `Ritiro`  | 0.35    |
| `Forfait` | 0.05    |

Un forfait quasi non influisce sul rating, mentre un ritiro influisce
poco più di un terzo rispetto a un match normale.
5. **Coefficiente K**: definisce quanto velocemente il rating si adatta al
risultato. Il valore attuale è `24.0` ed è costante per tutti gli atleti.
6. **Aggiornamento**: per ciascun atleta si applica la formula:

nuova_rating = rating_corrente + K × impatto × (actual − expected)


Dove `expected` e `actual` sono i valori calcolati ai passi 2 e 3.

L'incremento può essere positivo (l'atleta rende più del previsto) o
negativo (rende meno del previsto). L'impatto riduce o amplifica questo
aggiustamento.

## Proprietà del sistema

- **Ricalcolabile**: dato che il rating è ricostruito processando i match in
ordine cronologico, modificando un risultato passato e rieseguendo il
calcolo si ottiene una nuova classifica coerente.
- **Sensibile alla prestazione**: usare i punti classifica consente di
distinguere vittorie nette da vittorie di misura. Un match serrato
influenzerà poco il rating anche se c'è un vincitore.
- **Configurabile**: tutti i valori di partenza, K, impatti, ecc. sono
definiti nel dizionario `RATINGS_SETTINGS` in `src/settings.py`.

## Limiti e possibili evoluzioni

- **Assenza di decadimento temporale**: attualmente i match di un anno fa
contano quanto quelli recenti. Si potrebbe introdurre un fattore tempo.
- **K fisso**: atleti appena iscritti potrebbero avere K più alto per
stabilizzarsi prima.
- **Pesi diversi per stile**: in futuro si potrebbe calcolare un rating
separato per ciascuno stile (greco‑romana, libero, ecc.).
- **Rating offensivo/difensivo**: oltre al rating complessivo, si potrebbe
stimare la forza offensiva (produzione di punti) e quella difensiva
(capacità di limitare l'avversario).

## Nota sulla sincronizzazione con lo scoring

Il rating dipende dai punti classifica prodotti dallo scoring. Per questo
motivo eventuali modifiche alle formule di punteggio dovranno essere
accompagnate da un ricalcolo completo del rating per mantenere la coerenza.

