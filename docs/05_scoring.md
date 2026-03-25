# Scoring

## Obiettivo
Calcolare i punti classifica di un singolo incontro in modo coerente con la logica sperimentale della league.

## Principi adottati
- la vittoria conta più della sconfitta
- i punti tecnici del match contano, ma in modo proporzionato
- affrontare un atleta più pesante deve dare vantaggio
- donne e minorenni contro uomini seniores ricevono un bonus specifico
- match non realmente combattuti devono pesare meno

## Tipi di vittoria gestiti
- `Punti`
- `Schienamento`
- `Ritiro`
- `Forfait`

## Struttura logica del calcolo
Per ogni atleta il punteggio del match è costruito così:

1. **base risultato**
2. **bonus prestazione**
3. applicazione di **fattore peso**
4. applicazione di **fattore speciale**

## Formula attuale
### Struttura generale
```text
punti_finali = (base_risultato + bonus_prestazione) × fattore_peso × fattore_speciale
```

## Base risultato
### Match normali (`Punti`, `Schienamento`)
- vincitore = 2.0
- sconfitto = 1.0

### `Ritiro`
Valori ridotti rispetto a un match pieno.

Attuale configurazione:
- vincitore = 1.2
- sconfitto = 0.3

### `Forfait`
Valori molto ridotti.

Attuale configurazione:
- vincitore = 0.5
- sconfitto = 0.0

## Bonus prestazione
Il bonus prestazione non somma i punti tecnici in modo 1:1.

Si usa una quota normalizzata sul totale dei punti del match.

```text
bonus_prestazione = (punti_tecnici_atleta / punti_tecnici_totali_match) × bonus_massimo
```

Attuale configurazione:
- `bonus_massimo = 0.5`

Per `Forfait` il bonus prestazione è forzato a `0`.

## Fattore peso
Il fattore peso aumenta o diminuisce il punteggio in base alla differenza di peso.

Attuale configurazione:
- `+5%` per ogni kg di svantaggio
- `-5%` per ogni kg di vantaggio
- limite match ammesso: `±10 kg`

Formula logica:
```text
fattore_peso = 1 + (peso_avversario - proprio_peso) × 0.05
```

Con clamp tra `0.5` e `1.5`.

## Fattore speciale
Si applica quando:
- atleta femmina contro uomo senior
- atleta minorenne contro uomo senior

Attuale configurazione:
- bonus speciale = `1.30`

## Parametri configurabili
Tutti i parametri sono centralizzati in `src/settings.py`.

## Note importanti
- Lo scoring è sperimentale e potrà cambiare
- Le modifiche future dovranno idealmente essere pilotate da un pannello admin
- I dati grezzi del match restano nel DB, quindi i punti classifica possono essere ricalcolati
