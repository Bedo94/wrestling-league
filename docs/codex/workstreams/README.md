# Workstreams

Questa cartella contiene un file per ogni workstream attivo o ricorrente del progetto.

## Perché un file per workstream

Nel progetto si vuole poter continuare lavori diversi in parallelo, ad esempio:

- miglioramento UI
- backend PostgreSQL
- autenticazione e ruoli
- matchmaking
- formule e parametri

Un solo file `handoff_current.md` non basta quando esistono più thread paralleli.

## Regola di utilizzo

Per ogni workstream attivo:

- crea o aggiorna un file dedicato
- usa un nome stabile e leggibile
- conserva lì stato attuale, decisioni, rischi e prossimo punto di ripartenza

Esempi:

- `ui_improvements.md`
- `postgresql_backend.md`
- `auth_roles.md`
- `matchmaking_refinement.md`

## Contenuto minimo di un workstream

Ogni file dovrebbe includere almeno:

- scopo
- contesto stabile
- stato attuale
- file coinvolti
- decisioni già prese
- punti da verificare
- prossimo passo consigliato

## Regola per Codex

Quando inizi o riprendi un thread, chiedi sempre a Codex di leggere:

1. `AGENTS.md`
2. `docs/project_context.md`
3. il file del workstream desiderato
4. i file di codice direttamente coinvolti