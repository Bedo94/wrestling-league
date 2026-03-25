# Architettura del progetto

## Struttura cartelle
```text
wrestling_league/
├── app.py
├── README.md
├── requirements.txt
├── pyproject.toml
├── data/
│   └── league.db
├── pages/
│   ├── 1_Atleti.py
│   ├── 2_Eventi.py
│   ├── 3_Incontri.py
│   ├── 4_Classifiche.py
│   └── 5_Accoppiamenti.py
└── src/
    ├── __init__.py
    ├── athletes.py
    ├── database.py
    ├── events.py
    ├── init_db.py
    ├── levels.py
    ├── matches.py
    ├── models.py
    ├── pairing.py
    ├── ratings.py
    ├── reference_data.py
    ├── scoring.py
    └── settings.py
```

## Separazione delle responsabilità
### `pages/`
Contiene solo UI e orchestrazione.
Non dovrebbe contenere formule o logica persistente importante.

### `src/models.py`
Definisce le tabelle del database.

### `src/database.py`
Gestisce engine SQLAlchemy e sessioni.

### `src/init_db.py`
Crea le tabelle se non esistono.

### `src/scoring.py`
Calcola i punti classifica per i singoli match.

### `src/ratings.py`
Ricalcola il rating dinamico partendo dai match registrati.

### `src/pairing.py`
Costruisce coppie candidate e seleziona gli accoppiamenti suggeriti.

### `src/settings.py`
Centralizza tutti i parametri configurabili.

## Flusso dati semplificato
1. L'utente inserisce dati tramite Streamlit
2. La pagina chiama funzioni in `src/`
3. I moduli `src/` leggono/scrivono nel DB
4. Scoring, rating e classifiche vengono calcolati sui dati salvati

## Principio fondamentale
I dati grezzi devono restare separati dai dati derivati.

### Dati grezzi
- atleti
- eventi
- incontri
- punteggi tecnici del match
- stile
- sesso
- data di nascita
- peso del match

### Dati derivati
- punti classifica del match
- rating dinamico
- classifica aggregata
- indice mismatch
- suggerimenti di pairing

## Motivo di questa scelta
Se cambiano le formule:
- i dati grezzi restano validi
- i dati derivati si possono ricalcolare
