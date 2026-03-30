# Wrestling League – Web App

## Panoramica

Questa applicazione Web consente di gestire una **lega di lotta** amatoriale o professionale.  È costruita con
**Python** e **Streamlit** e utilizza **SQLAlchemy** per l’accesso ai dati.  Il progetto supporta due modalità
di persistencia dei dati:

* **SQLite locale** – per l’utilizzo personale o in rete locale.  Il database viene creato
  automaticamente in `data/league.db` se non esiste.
* **PostgreSQL remoto** – per l’utilizzo condiviso su più PC o nel cloud.  L’app può collegarsi
  a un database remoto impostando la variabile d’ambiente `DATABASE_URL` o configurandolo
  tramite la pagina “Database” dell’interfaccia.

La GUI realizzata con Streamlit permette di inserire atleti, eventi e incontri, calcolare i punti
classifica secondo regole personalizzabili, generare proposte di accoppiamenti bilanciate e
consultare classifiche in tempo reale.  È prevista l’aggiunta di un sistema di autenticazione e
autorizzazione per gestire diversi ruoli utente (admin, operatore gara, cliente).

## Funzionalità principali

* **Gestione atleti** – anagrafica completa con peso, sesso, livello e stile di lotta.
* **Gestione eventi** – creazione di giornate/eventi e definizione delle date.
* **Gestione incontri** – inserimento degli incontri con calcolo automatico dei punti classifica
  (basati su risultato, peso e bonus speciali) e dei punti di prestazione.
* **Classifiche dinamiche** – visualizzazione della classifica in base ai punti classifica e al
  **rating dinamico** (calcolato con un algoritmo simile all’Elo, sensibile alla prestazione
  tecnica).
* **Matchmaking** – suggerimento di coppie di atleti tenendo conto di peso, livello,
  rating, età e storico degli incontri per creare match equilibrati.
* **Supporto al database remoto** – è possibile scegliere tra database locale (SQLite) e remoto
  (PostgreSQL) dalla pagina “Database” di Streamlit.  L’app rileva la stringa `DATABASE_URL`
  e inizializza automaticamente le tabelle necessarie.
* **Esportazione dati** – tramite la pagina “Database” è possibile esportare uno snapshot del
  database attivo in formato SQLite o Excel.
* **Parametri configurabili** – tutti i valori delle formule di scoring, rating e matchmaking
  sono centralizzati in `src/settings.py` e verranno in futuro resi modificabili via interfaccia.

## Installazione

### Prerequisiti

* **Python 3.10** o superiore.
* (Opzionale) **PostgreSQL** per l’utilizzo con database remoto.

### Setup rapido (uso locale con SQLite)

Usando [uv](https://github.com/astral-sh/uv) per installare le dipendenze e avviare l’app:

```bash
uv sync  # installa le dipendenze
uv run streamlit run app.py