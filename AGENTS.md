# AGENTS.md

## Scopo del progetto

`wrestling_league` è una web app Streamlit per gestire una wrestling league interna tra studenti.

Obiettivi funzionali principali:

- gestione atleti
- gestione eventi
- registrazione incontri
- scoring trasparente e configurabile
- classifiche
- rating dinamico
- matchmaking automatico con revisione manuale

Il progetto privilegia semplicità d’uso, regole esplicite e modifiche incrementali.

Riferimenti di priorità per Codex:

1. file locali del progetto
2. repository Git corrente
3. documentazione persistente nel repo
4. solo in mancanza di quanto sopra, informazioni esterne pertinenti

GitHub resta la fonte di verità del codice condiviso.

---

## Come orientarsi nel repository

Ordine consigliato di lettura quando inizi un task:

1. `AGENTS.md`
2. `docs/project_context.md`
3. documentazione rilevante in `docs/`, `docs/chatgpt/`, `docs/codex/`
4. moduli di dominio coinvolti in `src/`
5. pagina Streamlit coinvolta in `pages/`
6. eventuali moduli helper UI importati dalla pagina

Non assumere che la memoria della chat contenga tutto il contesto corretto: il contesto persistente vive nel repository.

---

## Architettura in breve

### Separazione dei livelli

- `pages/` contiene le pagine Streamlit
- `src/` contiene logica di business, accesso ai dati, formule e servizi
- `docs/` contiene documentazione tecnica e contesto persistente
- `docs/chatgpt/` resta una fonte di contesto storica utile
- `docs/codex/` contiene il contesto operativo dedicato a Codex

Regola chiave:

- le pagine Streamlit devono orchestrare UI e chiamare funzioni di servizio
- la logica di business non deve vivere nelle pagine

### Convenzione pratica sui moduli UI

Questa convenzione è importante per leggere il progetto correttamente:

- `*_page_ui.py` = orchestratore della pagina / composizione della schermata
- `*_ui.py` = helper o componenti riusabili, soprattutto tabelle e frammenti di UI condivisi

Nota:

- `*_ui.py` non ha ancora un ruolo architetturale definitivo e stabile
- non forzare ora una tassonomia più rigida del necessario
- in futuro i file in `src/` potranno essere riorganizzati in sottocartelle

### Componenti di dominio principali

- atleti
- eventi
- incontri
- scoring
- classifiche
- rating dinamico
- matchmaking

### Componenti tecnici chiave

- `src/scoring.py` → calcolo punti classifica
- `src/ratings.py` → rating dinamico stile Elo
- `src/pairing.py` → matchmaking
- `src/settings.py` → parametri di default
- `src/formula_config_service.py` → parametri persistenti/configurabili
- `src/database.py` → infrastruttura DB
- `src/db_runtime.py` → selezione runtime del backend DB
- `pages/0_Database.py` → UI di scelta backend / operazioni DB

---

## Stack tecnologico

- Python
- Streamlit
- SQLAlchemy
- SQLite locale
- PostgreSQL remoto

Vincoli tecnici già assunti:

- il software deve funzionare con backend locale e remoto
- la scelta del backend deve passare da `src/db_runtime.py`
- il progetto deve restare compatibile sia con `streamlit run` sia con packaging futuro tramite PyInstaller
- le variabili d’ambiente e la configurazione vanno lette a runtime, non hardcodate

---

## Struttura delle cartelle

La struttura esatta va sempre verificata nel progetto locale o nella repository Git corrente.

Struttura minima attesa dal contesto:

```text
src/
pages/
docs/
docs/chatgpt/
docs/codex/