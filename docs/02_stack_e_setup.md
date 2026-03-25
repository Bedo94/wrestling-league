# Stack, strumenti e setup

## Linguaggi e librerie
- **Python**: linguaggio principale
- **Streamlit**: interfaccia web
- **SQLAlchemy**: accesso ORM / database
- **SQLite**: database locale semplice e portabile
- **pandas**: tabelle e aggregazioni semplici

## Tool di sviluppo
- **VS Code**: IDE consigliata
- **Git**: versionamento locale
- **GitHub**: repository remoto e collaborazione
- **uv**: gestione dipendenze e avvio progetto consigliati

## Perché questa scelta
### Streamlit
Scelto perché:
- rapido da usare
- ottimo per CRUD, filtri e tabelle
- facile da far girare su più PC
- adatto a prototipi che poi diventano strumenti veri

### SQLite
Scelto perché:
- semplice
- zero configurazione server
- perfetto per prototipo e uso locale
- facile da sostituire più avanti con altro DB se necessario

### SQLAlchemy
Scelto perché:
- mantiene il modello dati pulito
- prepara bene a future evoluzioni
- evita SQL sparso nelle pagine

## Setup rapido
### Con uv
```powershell
uv sync
uv run streamlit run app.py
```

### Con venv + pip
```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

## Ambiente consigliato
- Windows 11
- terminale integrato VS Code
- progetto aperto dalla root `wrestling_league`
- interprete Python del progetto `.venv`

## Note operative
- il database SQLite viene creato automaticamente se non esiste
- il file `.venv/` non va versionato
- il file `data/league.db` non va versionato

## Convenzioni di lavoro
- una feature per commit quando possibile
- logica database e calcolo in `src/`
- UI Streamlit in `pages/`
- parametri centralizzati in `src/settings.py`
