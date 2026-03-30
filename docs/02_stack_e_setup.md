# Stack, strumenti e setup

## Linguaggi e librerie
- **Python**: linguaggio principale.
- **Streamlit**: interfaccia web per CRUD e tabelle.
- **SQLAlchemy**: accesso ORM / database.
- **SQLite**: database locale semplice e portabile.
- **PostgreSQL**: database remoto utilizzato per l'uso condiviso e multi‑utente.
- **pandas**: per tabelle e aggregazioni semplici.

## Tool di sviluppo
- **VS Code**: IDE consigliata.
- **Git**: versionamento locale.
- **GitHub**: repository remoto e collaborazione.
- **uv**: gestione dipendenze e avvio progetto consigliati.
- **PyInstaller**: (opzionale) per generare un eseguibile locale.

## Perché questa scelta
### Streamlit
Scelto perché:
- rapido da usare;
- ottimo per CRUD, filtri e tabelle;
- facile da far girare su più PC;
- adatto a prototipi che poi diventano strumenti veri.

### SQLite
Scelto perché:
- semplice;
- zero configurazione server;
- perfetto per prototipo e uso locale;
- facile da sostituire più avanti con altro DB se necessario.

### PostgreSQL
Aggiunto per:
- consentire un **database centralizzato e condivisibile** da più PC;
- maggiore robustezza e concorrenza rispetto a SQLite;
- compatibilità con servizi di hosting e cloud.

Il progetto può lavorare in **due modalità**:
- **SQLite locale**: crea automaticamente `data/league.db` se non esiste;
- **PostgreSQL remoto**: l'URL di connessione deve essere fornito (es. `postgresql+psycopg://utente:password@host:5432/dbname`). Un’apposita pagina Streamlit (“Database”) permette di scegliere e configurare il backend in fase di esecuzione.

### SQLAlchemy
Scelto perché:
- mantiene il modello dati pulito;
- prepara bene a future evoluzioni (supporta sia SQLite sia PostgreSQL);
- evita SQL sparso nelle pagine.

## Setup rapido
### Con uv
```powershell
uv sync
uv run streamlit run app.py