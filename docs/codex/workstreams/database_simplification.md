# database_simplification

## Scopo

Semplificare la struttura del database di `wrestling_league` mantenendo solo dati grezzi/fattuali nel DB e spostando il più possibile i dati derivati e le elaborazioni nei servizi applicativi.

## Stato

active

## Contesto stabile

- Il database deve contenere solo dati grezzi o fattuali.
- Dati derivati da formule, come rating o scoring persistiti, non devono essere salvati nel DB.
- Le tabelle dell’app possono mostrare dati elaborati, ma tali dati devono essere calcolati dai servizi.
- Le modifiche devono essere incrementali e coerenti con l’architettura attuale.
- La separazione UI / logica / DB va mantenuta.

## Decisioni già prese

### 1. Filosofia DB

- il database deve contenere solo dati grezzi/fattuali
- non voglio salvare nel DB dati derivati dalle formule come rating o scoring persistiti
- le tabelle dell’app possono mostrare dati elaborati, ma questi devono essere calcolati dai servizi

### 2. Token nei match

- una sola colonna nel match:
  `token_used_by = None | "athlete_a" | "athlete_b"`
- se è `None`, nessun token è stato usato
- il conteggio dei token residui non va salvato nel DB: lo calcola l’app

- durante il refactor incrementale:
  - il layer applicativo puÃ² giÃ  usare `token_used_by` come semantica interna
  - `token_spender_id` puÃ² restare temporaneamente nel DB come dettaglio tecnico per persistenza e sync

### 3. Livelli atleti

- nel DB salvo solo `assigned_level`
- in UI voglio mostrare:
  - `assigned_level`
  - `suggested_level` (derivato dagli incontri / rating)
  - rating mostrato nella pagina atleti ma non salvato nel DB
- il matchmaking usa `assigned_level` solo nella fase iniziale quando non ci sono abbastanza incontri
- dopo quella fase, il matchmaking si basa su rating + altri parametri, non più sul livello assegnato
- se l’operatore cambia `assigned_level` dopo molti incontri, questo non deve alterare retroattivamente rating, scoring o storia competitiva

### 4. Formule

- voglio abbandonare la gestione attuale troppo complessa con tabelle granulari di versioning parametri
- preferisco una sola tabella di revisioni per ambiente
- ogni revisione salva il file formula completo come TOML nel campo testo (`config_text`)
- le anteprime e i test non devono creare versioni
- solo quando l’utente è soddisfatto deve poter premere qualcosa tipo `Versiona e attiva`
- il rollback deve creare una nuova revisione che copia una revisione precedente, non semplicemente riattivare una vecchia riga

### 5. Tabella formule desiderata

- una sola tabella tipo `formula_revisions`
- per ambiente (`league_local`, `league_remote`, `test_local`, `test_remote`)
- con campi concettuali tipo:
  - id
  - environment_name
  - revision_number
  - is_active
  - label
  - note
  - source_revision_id
  - config_format
  - config_text
  - config_hash
  - created_at
  - created_by

## Stato attuale

- La struttura attuale del DB va letta dal codice reale del repo prima di proporre modifiche.
- La gestione attuale delle formule è percepita come troppo complessa.
- Esiste già un layer DB con supporto sia SQLite sia PostgreSQL e le modifiche devono restare compatibili con entrambi.
- Va evitata una migrazione concettuale “big bang” se è possibile introdurre la semplificazione per passi.

- I modelli applicativi non includono piu `athletes.rating` ne `matches.points_a/points_b`.
- I database nuovi creati dai modelli correnti nascono gia senza queste colonne legacy.
- I database esistenti possono ancora contenerle: il runtime le segnala come legacy, ma non le usa piu.
- Per le formule, la persistenza attiva e ora concentrata in `formula_revisions`.
- La pagina admin formule puo usare una bozza locale in sessione per prove e anteprime,
  ma il database salva solo revisioni complete.
- Il wiring iniziale delle formule puo appoggiarsi all'ambiente DB gia attivo
  (`league_local` / `league_remote`) senza introdurre un runtime separato.
- La serializzazione delle revisioni formule deve restare autosufficiente a runtime:
  evitare dipendenze opzionali non garantite nell'ambiente locale.

## Strategia corrente di cleanup schema

- PostgreSQL:
  - cleanup fisico manuale esplicito con `ALTER TABLE ... DROP COLUMN IF EXISTS ...`
  - nessuna rimozione automatica silenziosa al bootstrap
- SQLite:
  - percorso consigliato non distruttivo: nuovo file DB pulito + sincronizzazione dei dati grezzi
  - si evita per ora una migrazione automatica fragile basata su rewrite tabellare
- il bootstrap dell'app deve limitarsi a:
  - creare tabelle mancanti
  - segnalare drift di schema
  - segnalare la presenza di colonne legacy

## File coinvolti

Da verificare nel codice reale del repo, ma questo workstream riguarda tipicamente:

- `src/models.py`
- `src/database.py`
- `src/db_runtime.py`
- `src/formula_config_service.py`
- eventuali moduli di scoring/rating che oggi leggono dati persistiti
- pagine admin/database/formule che dipendono dai modelli correnti

## Assunzioni da verificare

- Quali dati derivati siano oggi effettivamente persistiti nel DB.
- Quanto la UI dipenda da campi o tabelle che andrebbero rimossi o semplificati.
- Se esistano già migrazioni o bootstrap che dovranno essere adattati.
- Come è modellata oggi la parte formule e versioning.
- Se il concetto di ambiente formula esista già o vada introdotto.

## Rischi / attenzione

- Evitare di rompere la compatibilità tra SQLite e PostgreSQL.
- Evitare di spostare logica di calcolo nel layer DB.
- Evitare una migrazione distruttiva senza un percorso incrementale chiaro.
- Verificare sempre l’impatto dei cambi su UI, servizi e dati esistenti.
- Non introdurre versioning formule più complesso di quello necessario.

- Non cristallizzare helper o compatibilita legacy oltre il necessario:
  dopo la validazione della nuova struttura e la migrazione finale del vecchio DB reale,
  il codice temporaneo di supporto alla legacy va rimosso.

## Prossimo passo consigliato

- Leggere i modelli attuali e ricostruire la mappa delle tabelle realmente coinvolte.
- Distinguere chiaramente:
  - dati fattuali da mantenere nel DB
  - dati derivati da spostare nei servizi
  - strutture formule da semplificare
- Proporre una roadmap incrementale per:
  1. modelli dati
  2. servizi che leggono/scrivono
  3. UI amministrativa
  4. eventuali migrazioni

## Prompt di ripartenza per Codex

Leggi `AGENTS.md`, `docs/project_context.md` e questo file.
Usa prima i file locali del progetto come riferimento principale.
Se il locale non basta e te lo chiedo esplicitamente, puoi consultare anche la repository GitHub o fonti online pertinenti.
Poi leggi i file davvero coinvolti nel layer DB e proponi modifiche concrete, graduali e coerenti con queste decisioni architetturali, file per file, senza riscrivere da zero e mantenendo separazione UI / logica / DB.
