# Matchmaking

## Obiettivo
Suggerire accoppiamenti ragionevolmente equilibrati, senza rendere il sistema una scatola nera.

## Filosofia
Il matchmaking non impone automaticamente i match.

La prima versione:
- genera coppie valide
- stima una compatibilità
- propone gli accoppiamenti migliori
- lascia all'utente la decisione finale

## Vincoli rigidi attuali
Una coppia è valida solo se:
- i due atleti sono diversi
- condividono lo stesso stile
- la differenza di peso non supera la soglia scelta
- la differenza di level non supera la soglia scelta
- la differenza di età non supera la soglia scelta, se impostata
- se richiesto, appartengono allo stesso sesso

## Evento di riferimento
L'evento selezionato definisce la data del pairing.

Logica attuale:
- età calcolata alla data di quell'evento
- storico considerato solo fino a quell'evento

## Coppie candidate
Sono tutte le coppie valide che rispettano i vincoli minimi.

## Accoppiamenti suggeriti
Sono la proposta finale del sistema.

La selezione avviene con approccio greedy:
1. ordina le coppie candidate dal mismatch più basso al più alto
2. prende la migliore disponibile
3. esclude i due atleti già usati
4. continua finché possibile

## Indice mismatch
L'indice mismatch è una penalità di incompatibilità:
- più basso = meglio
- più alto = peggio

## Componenti attuali del mismatch
- componente peso
- componente level
- componente rating
- componente età
- penalità rematch

## Parametri attuali
Centralizzati in `src/settings.py`:
- fattore peso
- fattore level
- divisore rating
- fattore età
- penalità rematch
- soglie di default

## Perché i dettagli numerici non sono mostrati troppo in UI
Le formule sono ancora sperimentali.

La UI principale deve restare leggera.

La documentazione e in futuro una pagina admin descriveranno e governeranno i parametri.

## Evoluzioni previste
- salvare accoppiamenti suggeriti come match programmati
- supportare status `scheduled / completed`
- usare ultimo peso reale invece di default_weight in alcune modalità
- gestire filtri/preset federali
- rendere i pesi del mismatch modificabili da admin
