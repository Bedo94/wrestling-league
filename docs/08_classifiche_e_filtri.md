# Classifiche e filtri

## Obiettivo
Mostrare una classifica generale, filtrabile e versatile.

## Principio adottato
Non si salvano categorie rigide nel database.

Si salvano dati grezzi continui:
- data di nascita
- sesso
- stile
- peso di riferimento
- risultati dei match

Poi la classifica viene filtrata e vista in modi diversi.

## Dati mostrati in classifica
- posizione
- atleta
- team
- stile
- sesso
- età
- peso di riferimento
- level
- rating
- incontri
- vittorie
- sconfitte
- punti classifica totali
- media punti
- punti tecnici fatti
- punti tecnici subiti
- differenza punti tecnici

## Filtri attuali
- stile
- sesso
- età
- peso di riferimento
- level
- stato attivo
- solo atleti con match

## Filosofia dei filtri
### Età
L'età viene derivata dalla data di nascita.

### Peso
Il filtro peso attuale usa `default_weight`.

### Level
Il level è utile per vedere gruppi omogenei iniziali.

### Rating
Il rating è visibile per trasparenza ma non è ancora un filtro principale in tutte le viste.

## Perché non usare subito categorie federali rigide
L'obiettivo del progetto è anche consentire letture non standard:
- filtri liberi
- viste sperimentali
- letture pound-for-pound

## Evoluzioni possibili
- preset età federali (U20, U23, Senior...)
- preset peso federali
- filtro per team
- modalità pound-for-pound
- classifica per stile con ranking separati
