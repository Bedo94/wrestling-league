# Admin e configurazione futura

## Obiettivo
Permettere agli amministratori di modificare parametri del sistema senza toccare il codice.

## Motivazione
Il progetto è ancora sperimentale.

Per questo:
- le formule non sono definitive
- i pesi del matchmaking potrebbero cambiare
- i parametri dello scoring potrebbero cambiare
- il rating potrebbe essere ricalibrato

## Strategia attuale
I parametri sono centralizzati in `src/settings.py`.

Questo è il primo passo per renderli modificabili più avanti.

## Parametri già centralizzati
### Scoring
- soglia massima peso
- bonus peso per kg
- punti base vittoria/sconfitta
- bonus massimo prestazione
- soglia minorenne
- bonus speciale
- punti base per ritiro
- punti base per forfait

### Matchmaking
- differenza peso massima di default
- peso della componente peso
- peso della componente level
- divisore rating
- peso della componente età
- penalità rematch
- soglie di default level / età

## Evoluzione prevista
### Fase 1
Parametri centralizzati in file Python.

### Fase 2
Pagina admin con form Streamlit per modificarli.

### Fase 3
Parametri salvati nel database.

### Fase 4
Versionamento dei parametri:
- chi ha cambiato cosa
- quando
- valore precedente
- valore nuovo

## Requisiti per farlo bene
- autenticazione / autorizzazione admin
- distinzione netta tra dati grezzi e dati derivati
- funzione di ricalcolo globale
- log modifiche

## Dati che devono essere ricalcolabili
- punti classifica derivati
- rating dinamico
- suggerimenti matchmaking
- eventuali metriche pound-for-pound

## Principio importante
Le formule non devono essere spiegate in modo pesante nella UI principale.

La UI principale deve essere leggera.

Le regole dettagliate devono vivere:
- nella documentazione
- in una futura pagina info
- in una futura pagina admin

### Rating
- seed iniziali per level
- default start rating
- K factor
- peso dei match normali
- peso dei match per ritiro
- peso dei match per forfait
