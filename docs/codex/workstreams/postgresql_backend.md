# postgresql_backend

## Scopo

Rendere robusto il supporto al backend PostgreSQL remoto, mantenendo compatibilità con SQLite locale e rispettando la selezione runtime del database tramite `src/db_runtime.py`.

## Stato

active

## Contesto stabile

- Il progetto deve funzionare sia con SQLite locale sia con PostgreSQL remoto.
- La logica specifica del backend deve restare confinata a `database.py` e `db_runtime.py`.
- La UI di scelta backend e operazioni database vive in `pages/0_Database.py`.
- In futuro le funzionalità amministrative dovranno essere protette da ruoli, ma il modello finale dei permessi non è ancora definito.

## Stato attuale

- È stato riportato un caso in cui, dopo un tentativo fallito di connessione a PostgreSQL, il rollback sembrava funzionare.
- In un tentativo successivo, la connessione a un PostgreSQL di test non ha mostrato i contenuti remoti attesi ma quelli del database locale `league.db`.
- È stato poi riportato un errore di connessione con riferimento a un parametro di startup non supportato, in particolare `statement_timeout`, su una configurazione con pooler.
- Questo stato va verificato contro il codice reale corrente del repo.

## File coinvolti

Da verificare nel codice reale del repo, ma questo workstream riguarda tipicamente:

- `src/database.py`
- `src/db_runtime.py`
- `pages/0_Database.py`
- eventuali helper di bootstrap del database
- eventuali moduli che riusano sessioni o engine

## Decisioni già prese

- Non introdurre logica PostgreSQL-specifica fuori dai moduli DB dedicati.
- Non rompere il funzionamento con SQLite locale.
- La scelta del backend deve essere chiara e coerente a runtime.
- Le modifiche devono essere incrementali e con impatto minimo.

## Assunzioni da verificare

- Dove viene mantenuto lo stato del backend attivo.
- Se esiste caching di engine o sessioni che sopravvive a tentativi di attivazione falliti.
- Se alcuni parametri di connessione vengono passati automaticamente anche quando il provider remoto non li supporta.
- Se la UI mostra sempre in modo affidabile quale backend è realmente attivo.

## Rischi / attenzione

- Regressioni nella selezione runtime del backend.
- Stato incoerente tra backend visualizzato e backend effettivamente usato.
- Persistenza involontaria di sessioni/engine locali dopo un fallimento remoto.
- Fix troppo specifici per un provider che riducono la portabilità del supporto PostgreSQL.

## Prossimo passo consigliato

- Tracciare il flusso completo di attivazione backend dalla UI fino alla creazione di engine/sessioni.
- Verificare dove viene deciso il fallback dopo un errore.
- Identificare la fonte del parametro di startup non supportato e valutare una soluzione confinata al layer DB.
- Migliorare la visibilità dello stato del backend attivo, se necessario.

## Prompt di ripartenza per Codex

Leggi `AGENTS.md`, `docs/project_context.md` e questo file.
Poi apri i file del layer database coinvolti e ricostruisci il flusso di attivazione del backend, cercando una patch incrementale che corregga incoerenze tra fallback locale e attivazione PostgreSQL senza introdurre logica specifica fuori dal layer DB.