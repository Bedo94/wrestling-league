# Rating dinamico

## Cos'è
Il rating dinamico è una misura della forza competitiva osservata dell'atleta nel tempo.

Non sostituisce il `level`.

## Differenza tra level e rating
### Level
- manuale
- iniziale
- qualitativo
- stabile

### Rating
- automatico
- dinamico
- quantitativo
- aggiornato in base ai match

## Idea attuale
Il rating parte da un valore iniziale dipendente dal level e poi viene aggiornato rileggendo tutti i match in ordine cronologico.

## Seed iniziale dal level
Attuale configurazione:
- Level 1 → 900
- Level 2 → 1000
- Level 3 → 1100
- Level 4 → 1200

## Metodo di aggiornamento
Il sistema usa una logica tipo Elo semplificata.

### Passaggi
1. per ogni match prende il rating corrente dei due atleti
2. stima il risultato atteso
3. confronta atteso e risultato reale
4. aggiorna i rating

## Risultato reale usato
Il risultato reale non è solo win/loss, ma è basato sui punti classifica del match:

```text
actual_a = points_a / (points_a + points_b)
actual_b = points_b / (points_a + points_b)
```

Questo permette al rating di riflettere meglio anche match molto combattuti o molto sbilanciati.

## Parametri principali
- `K_FACTOR = 24.0`
- impatto match normale = `1.0`
- impatto `Ritiro` = ridotto
- impatto `Forfait` = quasi nullo o nullo

## Proprietà utili di questa scelta
- rating coerente con il sistema di scoring già adottato
- rating ricalcolabile da zero
- correzione coerente se si modifica un match vecchio

## Limiti attuali
- taratura sperimentale ancora da validare
- non usa ancora decadimento temporale
- non usa ancora strength of schedule avanzata separata

## Evoluzioni possibili
- K factor diverso per nuovi atleti
- peso ridotto di forfait/ritiro sul rating
- rating separato per stile
- rating offensivo/difensivo
- modalità pound-for-pound derivata
