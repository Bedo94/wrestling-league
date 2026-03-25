# Wrestling League

Web app in Python/Streamlit per gestire una league di lotta ispirata al concetto C.L.O.E.:
- anagrafica atleti
- eventi / giornate
- incontri
- scoring sperimentale
- classifiche filtrabili
- rating dinamico
- matchmaking assistito

## Stato attuale
Il progetto è in fase di sperimentazione. Le formule di scoring, rating e matchmaking sono volutamente centralizzate e pensate per essere rese configurabili in una futura area admin.

## Stack
- Python
- Streamlit
- SQLAlchemy
- SQLite
- pandas
- Git / GitHub
- uv oppure venv + pip

## Struttura principale
- `app.py`: entrypoint Streamlit
- `pages/`: pagine dell'app
- `src/models.py`: modelli database
- `src/database.py`: engine/session SQLite
- `src/init_db.py`: creazione automatica tabelle
- `src/scoring.py`: logica punti classifica
- `src/ratings.py`: rating dinamico
- `src/pairing.py`: matchmaking assistito
- `src/settings.py`: parametri centralizzati
- `docs/`: documentazione di progetto

## Documentazione
- `docs/01_idea_e_obiettivi.md`
- `docs/02_stack_e_setup.md`
- `docs/03_architettura.md`
- `docs/04_modello_dati.md`
- `docs/05_scoring.md`
- `docs/06_rating_dinamico.md`
- `docs/07_matchmaking.md`
- `docs/08_classifiche_e_filtri.md`
- `docs/09_roadmap_e_todo.md`
- `docs/10_admin_e_configurazione_futura.md`

## Avvio rapido
Con `uv`:

```powershell
uv sync
uv run streamlit run app.py
```

Con `venv + pip`:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

## Nota sul database
L'app inizializza automaticamente il database all'avvio se il file SQLite non esiste ancora.

## Nota sulla documentazione
La documentazione descrive sia le regole attualmente implementate sia le parti ancora in valutazione.

## Uso con ChatGPT

Questo progetto può essere sviluppato usando ChatGPT come assistente.

Documentazione:
- docs/chatgpt/CHATGPT_WORKFLOW.md

Flusso:
- codice su GitHub
- ChatGPT usato come assistente
- modifiche sempre applicate localmente
