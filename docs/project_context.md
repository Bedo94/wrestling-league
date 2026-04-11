# Project Context

## Obiettivo funzionale del software

`wrestling_league` è una web app Streamlit per gestire una wrestling league interna tra studenti.

Funzionalità principali note:

- gestione atleti
- gestione eventi
- registrazione incontri
- scoring
- classifiche
- rating dinamico
- matchmaking automatico con revisione manuale

Filosofia del progetto:

- semplicità d’uso
- trasparenza delle regole
- flessibilità dei parametri nel tempo
- evitare logiche “black box”

---

## Stato attuale sintetico

Dal contesto del progetto risultano già implementati:

- atleti con `level` e `rating`
- eventi
- incontri
- scoring C.L.O.E.
- classifiche
- rating dinamico
- matchmaking base

Limiti ancora noti o ricorrenti:

- niente match schedulati
- parte dei parametri è ancora o era storicamente hardcoded in `settings`
- gestione admin non ancora completata
- alcune aree UI sono ancora in evoluzione

---

## Componenti principali

## 1. Gestione atleti

Responsabilità:

- anagrafica atleti
- peso
- livello
- rating
- dati usati da scoring e matchmaking

## 2. Gestione eventi

Responsabilità:

- creazione e consultazione eventi
- collegamento degli incontri agli eventi

## 3. Gestione incontri

Responsabilità:

- registrazione match
- risultato del match
- tipo di vittoria
- dati usati per punteggio e rating

Tipi di vittoria noti:

- punti
- schienamento
- ritiro
- forfait

## 4. Scoring

Lo scoring tiene conto almeno di:

- base risultato
- bonus prestazione
- fattore peso
- bonus speciale

Regole note:

- il forfait deve avere impatto minimo
- il ritiro deve avere impatto ridotto
- il sistema deve premiare il rischio controllato, non solo la parità perfetta

## 5. Rating dinamico

Il rating è di tipo Elo-like.

Caratteristiche note:

- si aggiorna dopo ogni match
- considera i punti classifica ottenuti
- ha impatto ridotto in caso di ritiro o forfait

## 6. Matchmaking

Il matchmaking produce:

- accoppiamenti suggeriti
- tutte le coppie candidate

Fattori noti:

- peso
- livello
- rating
- età
- numero/storico di precedenti

È presente un mismatch index:

- più basso = accoppiamento migliore

---

## Flussi chiave

## Flusso 1: gestione dati sportivi

1. si registrano o aggiornano gli atleti
2. si crea un evento
3. si registrano gli incontri dell’evento
4. gli incontri alimentano scoring, classifiche e rating

## Flusso 2: ranking e rating

1. i match registrati producono punteggi
2. i punteggi alimentano classifiche
3. gli stessi match aggiornano il rating dinamico
4. classifiche e rating vengono mostrati nelle pagine dedicate

## Flusso 3: matchmaking

1. si parte dall’anagrafica atleti e dai dati competitivi
2. il sistema genera accoppiamenti bilanciati
3. gli accoppiamenti sono suggerimenti, non decisioni irrevocabili
4. la revisione manuale resta parte importante del flusso

## Flusso 4: configurazione formule

1. i parametri partono da `src/settings.py`
2. i parametri devono convergere verso gestione configurabile/persistente
3. la UI admin delle formule deve essere coerente con la logica in `src/`
4. cambiare parametri non deve richiedere duplicazioni di formula nelle pagine

## Flusso 5: scelta backend database

1. l’app può lavorare con SQLite locale
2. l’app può lavorare con PostgreSQL remoto
3. la scelta runtime del backend passa da `src/db_runtime.py`
4. la UI di amministrazione DB vive in `pages/0_Database.py`

---

## Vincoli tecnici

## Stack

- Python
- Streamlit
- SQLAlchemy
- SQLite locale
- PostgreSQL remoto

## Vincoli architetturali

- GitHub è la fonte di verità del codice
- le modifiche devono essere incrementali
- non riscrivere file da zero senza reale necessità
- la logica di business deve stare in `src/`
- le pagine in `pages/` devono orchestrare la UI
- parametri numerici e coefficienti non vanno hardcodati nelle pagine
- backend specifico confinato ai moduli DB dedicati
- il progetto deve restare compatibile con `streamlit run` e con packaging futuro
- evitare dipendenza dalla memoria della singola chat

## Vincoli operativi

- quando si lavora con un assistente bisogna partire dai file reali del repo
- la documentazione del repo va trattata come contesto persistente
- `docs/chatgpt/` resta utile e non va rimosso subito
- è consigliato introdurre una sezione `docs/codex/` per il contesto operativo dedicato a Codex
- in caso di discrepanza, prevale sempre il codice reale del repository

---

## Regole di dominio già emerse

Regole note dal contesto attuale:

- match entro una differenza peso controllata
- bonus per differenza peso
- bonus per categorie svantaggiate
- bonus speciale per donna vs uomo adulto
- bonus speciale per minorenne vs uomo adulto
- obiettivo: match equilibrati ma non identici

Interpretazione pratica:

- il sistema non cerca solo parità assoluta
- il sistema premia la gestione controllata del rischio competitivo

---

## Decisioni già prese nel Project

## 1. Modifiche incrementali, non riscritture

Quando si interviene su un file esistente, si estende o si corregge la struttura attuale invece di sostituirla completamente.

## 2. Separazione UI / logica / DB

È una regola forte del progetto:

- UI nelle pagine Streamlit
- logica e servizi in `src/`
- dettagli DB confinati ai moduli dedicati

## 3. Parametri centralizzati

I valori numerici non devono essere sparsi.

Percorsi ammessi:

- `src/settings.py`
- persistenza configurabile tramite `formula_config_service.py` e tabella dedicata

## 4. Supporto doppio backend come requisito reale

SQLite e PostgreSQL non sono varianti opzionali temporanee: il progetto deve continuare a supportarli entrambi.

## 5. Convenzione attuale sui moduli UI

Convenzione pratica emersa nel progetto:

- `*_page_ui.py` = orchestratore della pagina
- `*_ui.py` = helper riusabili, componenti e tabelle condivisibili

Questa convenzione è utile per leggere il codice, ma non va irrigidita oltre il necessario.

## 6. Per ora non forzare una riorganizzazione massiva delle cartelle

Nelle chat del Project è emersa l’idea di creare sottocartelle dedicate in `src/`, ma la decisione operativa attuale è di non spostare ancora in massa i file durante task ordinari. La riorganizzazione futura è attesa, ma va affrontata come task esplicito.

## 7. `docs/chatgpt/` resta valido

La documentazione usata finora per ChatGPT non va eliminata subito.
La strategia consigliata è affiancarla con documenti dedicati a Codex, non sostituirla in blocco.

## 8. VS Code è l’editor corrente

VS Code è l’editor usato attualmente.
Non è una scelta architetturale rigida, ma è una buona assunzione pratica per configurazioni iniziali.

## 9. I ruoli utente sono una direzione già prevista

La futura autenticazione a ruoli è considerata parte dell’evoluzione del progetto.

Almeno due ruoli sono già emersi:

- admin
- user

Conseguenze attese:

- la pagina formule deve essere trattata come funzionalità amministrativa
- l’accesso alla pagina database è ancora da definire con precisione

---

## Zone del codice concettualmente centrali

I moduli più “centrali” per capire il progetto sono:

- `src/scoring.py`
- `src/ratings.py`
- `src/pairing.py`
- `src/settings.py`
- `src/formula_config_service.py`
- `src/database.py`
- `src/db_runtime.py`
- `pages/0_Database.py`

Questi file contengono o influenzano regole trasversali.
Le modifiche qui vanno pensate con cautela.

---

## Backlog e direzioni evolutive note

Priorità alte già emerse:

- migliorare gestione forfait / ritiro
- introdurre match schedulati
- migliorare matchmaking

Priorità medie:

- pagina admin
- parametri modificabili via UI / persistenza

Direzioni future:

- dashboard più avanzata
- export dati
- API
- autenticazione e ruoli
- riorganizzazione di `src/` in sottocartelle più navigabili

---

## Continuità del lavoro tra PC diversi

Esigenza esplicita del progetto:

- poter riprendere sviluppo da macchine diverse senza dipendere dalla memoria di una singola chat

Strategia consigliata:

- usare GitHub come fonte di verità del codice
- usare documentazione nel repo come memoria persistente del contesto
- usare file di workstream in `docs/codex/workstreams/` per conservare stato di lavoro, decisioni recenti e prossimi passi

In pratica, la continuità cross-PC deve vivere nel repository, non solo nella cronologia della chat.

---

## Dubbi aperti / da chiarire

## 1. Autenticazione

È chiaro che il progetto andrà verso un sistema di login con ruoli, ma restano da definire:

- implementazione tecnica esatta
- libreria o approccio da usare
- granularità dei permessi

## 2. Accesso alla pagina database

La pagina formule è da trattare come area amministrativa.

Per la pagina database resta aperto il dubbio se:

- limitarla agli admin
- consentire almeno alcune operazioni locali anche agli user
- separare funzioni innocue da funzioni amministrative

## 3. Match schedulati

La funzionalità è nel backlog, ma va ancora definito:

- modello dati
- flusso UI
- relazione con eventi e matchmaking

## 4. Stato della parametrizzazione completa

L’obiettivo è avere parametri configurabili e persistenti, ma va confermato quanto della formula sia già migrato fuori da `settings.py` e quanto no.

## 5. Organizzazione futura dei moduli UI e di `src/`

È prevista una futura riorganizzazione in sottocartelle, ma non è ancora definita la mappa finale.

## 6. Elenco preciso dei file del repo

L’elenco esatto delle cartelle e dei file va sempre verificato leggendo il progetto locale o la repository Git corrente.
Questo documento non deve inventare una mappa completa se non è stata confermata dal codice reale.

---

## Come leggere rapidamente il progetto in una nuova sessione

Ordine consigliato:

1. `AGENTS.md`
2. `docs/project_context.md`
3. eventuale documentazione in `docs/codex/`
4. `src/scoring.py`
5. `src/ratings.py`
6. `src/pairing.py`
7. `src/db_runtime.py`
8. la pagina Streamlit coinvolta dal task
9. eventuali moduli helper/importati direttamente dalla pagina

Questo ordine tende a minimizzare lettura inutile e a portare subito nei punti di maggiore densità logica.

---

## Nota finale

Quando il codice reale e questo documento divergono, prevale sempre il codice reale del repository.

Quando il codice è ambiguo ma la direzione architetturale è chiara, seguire prima:

1. separazione UI / logica / DB
2. modifiche incrementali
3. parametri centralizzati
4. supporto doppio backend
5. documentazione aggiornata
6. continuità del contesto nel repository