# Scoring

## Obiettivo

Lo scoring assegna punti classifica agli atleti per ogni incontro. L'obiettivo non è
solo premiare la vittoria, ma anche riconoscere la difficoltà del match
(differenza di peso, eventuale bonus speciale) e la prestazione tecnica.

## Struttura del calcolo

Per ciascun atleta viene calcolato un punteggio finale sommando una parte
additiva (base risultato + bonus prestazione) e moltiplicando per due
moltiplicatori (fattore peso e fattore speciale):

$punti\_finali = (base\_risultato + bonus\_prestazione) × fattore\_peso × fattore\_speciale$


Questa formula garantisce che la vittoria e la prestazione siano la base,
ma che le condizioni di svantaggio (peso o categoria protetta) possano
amplificarne il valore:contentReference[oaicite:0]{index=0}.

## Base risultato

La base risultato dipende dal tipo di vittoria e dal fatto che l'atleta sia
vincitore o sconfitto. I valori attuali provengono dal file di configurazione
`src/settings.py` e sono:

| Tipo di match      | Vincitore | Sconfitto |
|--------------------|-----------|-----------|
| Normale (`Punti` o `Schienamento`) | 2.0       | 1.0       |
| `Ritiro`           | 1.2       | 0.3       |
| `Forfait`          | 0.5       | 0.0       |

Un ritiro (match interrotto dall'avversario) vale meno di un match completo,
e un forfait (assenza o mancata presentazione) vale ancora di meno:contentReference[oaicite:1]{index=1}. Se il
match si chiude per forfait, il bonus prestazione è azzerato per entrambi.

## Bonus prestazione

Il bonus prestazione valorizza i punti tecnici accumulati dagli atleti
durante l'incontro senza premiare in modo eccessivo chi domina. Viene
calcolato come quota dei punti totali del match moltiplicata per il
**bonus massimo** configurato:

bonus_prestazione = (raw_score_atleta / (raw_score_atleta + raw_score_avversario)) × bonus_massimo


Dove `bonus_massimo` vale `0.5`. Se la somma dei punti tecnici è zero o
l'incontro è vinto per forfait, `bonus_prestazione` è pari a `0.0`:contentReference[oaicite:2]{index=2}.

Questo meccanismo premia la prestazione tecnica proporzionalmente, ma non
permette a un singolo match di stravolgere la classifica: il bonus massimo
aggiunge al più mezzo punto alla base risultato.

## Fattore peso

Il fattore peso modifica il punteggio in base allo svantaggio o vantaggio
peso dell'atleta rispetto all'avversario. La differenza di peso è limitata
a ±10 kg; se questa soglia viene superata il sistema solleva un errore.

Il fattore è calcolato con la formula lineare:

fattore_peso = 1 + (peso_avversario − peso_proprio) × 0.05


Se l'atleta pesa meno dell'avversario, il fattore aumenta di 5 % per ogni
chilogrammo di svantaggio; se pesa di più, diminuisce di 5 % per chilogrammo
di vantaggio. Per evitare eccessi, il valore viene **clampato** fra
`0.5` e `1.5`:contentReference[oaicite:3]{index=3}:

* `fattore_peso < 0.5` ⇒ arrotondato a `0.5`
* `fattore_peso > 1.5` ⇒ arrotondato a `1.5`

Questo significa che il punteggio di un atleta molto più leggero potrà al
massimo raddoppiare (1.5×) e quello di un atleta molto più pesante potrà al
massimo dimezzarsi (0.5×).

## Fattore speciale

Il fattore speciale è pensato per tutelare categorie considerate svantaggiate.
Si applica quando si verificano entrambe le condizioni:

* L'avversario è un **uomo senior**, cioè sesso "Maschio" e maggiore di
  18 anni al momento dell'evento.
* L'atleta è **donna** o **minorenne**.

Quando queste condizioni sono vere, al punteggio dell'atleta viene
applicato un moltiplicatore pari a `1.30`:contentReference[oaicite:4]{index=4}. Altrimenti il fattore è `1.0`.
Il calcolo dell'età si basa sulla data dell'evento e sulla data di nascita.

## Calcolo completo

Di seguito un riepilogo dell'algoritmo implementato in `src/scoring.py`:

1. **Validazione peso**: se la differenza di peso tra gli atleti supera la soglia
   di `10.0` kg viene sollevato un errore.
2. **Base risultato**: ottenuta in base al tipo di vittoria (`Punti`,
   `Schienamento`, `Ritiro`, `Forfait`) e al fatto che l'atleta sia
   vincitore o sconfitto.
3. **Bonus prestazione**: calcolato come quota dei punti tecnici sul totale,
   moltiplicato per il bonus massimo (`0.5`). Forfait ⇒ bonus a `0.0`.
4. **Fattore peso**: calcolato in base ai pesi e clampato fra `0.5` e `1.5`.
5. **Fattore speciale**: applicato (1.30) solo per donne o minorenni contro uomini
   seniores.
6. **Punteggio finale**: sommati base e bonus, poi moltiplicati per fattori
   peso e speciale.

Ogni valore numerico utilizzato (bonus per kg, punti base, soglie, fattori
speciali, ecc.) è definito nel dizionario `SCORING_SETTINGS` dentro
`src/settings.py` per facilitare futuri aggiustamenti.

## Esempio numerico

Supponiamo un match normale fra l'atleta A (70 kg) e l'atleta B (75 kg),
vinto da A per punti tecnici 7–3. Gli atleti hanno entrambi più di 18 anni
e A è di sesso maschile, quindi non c'è bonus speciale.

* **Base risultato**: A vince ⇒ 2.0; B perde ⇒ 1.0.
* **Bonus prestazione**: i punti totali sono 10;
  A ottiene `(7/10) × 0.5 = 0.35`; B ottiene `(3/10) × 0.5 = 0.15`.
* **Fattore peso**: A pesa 70 kg e affronta un avversario da 75 kg, quindi
  `fattore_peso_A = 1 + (75 − 70) × 0.05 = 1.25`.
  B pesa di più, quindi `fattore_peso_B = 1 + (70 − 75) × 0.05 = 0.75`.
* **Fattore speciale**: nessuna condizione ⇒ 1.0 per entrambi.
* **Punteggi finali**:
  * A: `(2.0 + 0.35) × 1.25 × 1.0 = 2.94` ⇒ 2.94 punti classifica
  * B: `(1.0 + 0.15) × 0.75 × 1.0 = 0.86` ⇒ 0.86 punti classifica

Come si vede, lo svantaggio di peso di A aumenta il suo punteggio, mentre B
ne subisce l'effetto opposto.

## Parametri configurabili

Tutti i valori utilizzati nelle formule (punti base, bonus massimo,
bonus per kilogrammo, soglie età, fattori, ecc.) sono centralizzati in
`src/settings.py` e possono essere modificati per calibrare lo scoring.

Il progetto prevede una futura **area amministrativa** che permetterà di
aggiornare questi parametri tramite l'interfaccia Web senza modificare il
codice sorgente. Quando i parametri cambiano, i punteggi possono essere
ricalcolati a partire dai dati grezzi dei match.
