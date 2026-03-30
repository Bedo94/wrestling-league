# Istruzioni per ChatGPT

Queste istruzioni definiscono come ChatGPT deve interagire con il progetto
`wrestling_league` quando agisce come assistente di sviluppo.  Rappresentano
regole operative che aiutano a mantenere coerenza, qualità del codice e rispetto
dell’architettura.

## Principi generali

1. **Non riscrivere da zero** – le modifiche devono essere **incrementali**.  Se un
   file esiste già, evita di sostituirlo completamente; aggiungi solo ciò che
   serve e mantieni la struttura esistente.
2. **Separa UI e logica** – la logica di business, il calcolo di punteggi, il
   matchmaking e l’accesso ai dati devono risiedere nei moduli di `src/`.  Le
   pagine Streamlit (`pages/`) devono solo orchestrare l’interfaccia e chiamare
   le funzioni di servizio.
3. **Configura tramite parametri** – tutti i valori numerici (soglie, bonus,
   coefficienti) devono essere definiti in `src/settings.py` o nella tabella
   `FormulaParameter` via `formula_config_service.py`.  Non hardcodare numeri
   nelle pagine o nei servizi.
4. **Supporto a due back‑end** – l’app deve funzionare sia con **SQLite locale**
   (per prototipi e uso personale) sia con **PostgreSQL remoto** (per l’uso
   condiviso).  Utilizza `src/db_runtime.py` per applicare la scelta del
   database.  Non introdurre logica specifica per uno dei due back‑end al di
   fuori di `database.py` e `db_runtime.py`.
5. **Futuri ruoli utente** – tieni conto che verrà implementato un sistema di
   autenticazione con ruoli (admin, operatore gara, cliente).  Le funzioni
   amministrative (come la scelta del backend, l’esportazione dei dati e la
   modifica dei parametri) dovranno essere protette e visibili solo agli admin.
6. **Packaging e deploy** – il codice deve rimanere compatibile sia con
   l’esecuzione tramite `streamlit run` sia con la creazione di un eseguibile
   locale tramite PyInstaller.  Le variabili d’ambiente e i parametri devono
   essere letti in fase di avvio e non codificati staticamente.
7. **Non accedere a internet** – in questo progetto l’assistente non deve
   eseguire ricerche sul web.  Tutte le informazioni necessarie provengono dai
   file del repository GitHub e dai documenti in `docs/`.

## Flusso di lavoro raccomandato

1. **Leggi la documentazione** – prima di proporre modifiche, leggi i file
   pertinenti in `docs/` e `docs/chatgpt/` per capire la logica esistente e le
   convenzioni.
2. **Consulta il codice** – se l’utente chiede di modificare o estendere una
   funzionalità, apri i file coinvolti con l’API GitHub e analizza le funzioni
   esistenti.  Evita di duplicare il codice; riutilizza funzioni dove possibile.
3. **Proponi modifiche puntuali** – spiega quali file verranno modificati e
   perché.  Implementa la modifica attraverso patch mirate e mantieni coerenti
   le importazioni.
4. **Aggiorna la documentazione** – dopo aver modificato il codice, verifica se
   è necessario aggiornare i file in `docs/` o in questa cartella.  Mantieni
   sempre sincronizzate le formule, i parametri e i moduli descritti.
5. **Prepara al deploy** – se stai implementando funzionalità relative al
   database remoto o al packaging, assicurati che l’app possa essere avviata
   sia in locale (SQLite) sia in remoto (PostgreSQL) senza modificare il codice.

## Elementi chiave del progetto

- **Scoring** – calcolo dei punti classifica basato su risultato del match,
  bonus di prestazione, fattore di peso e fattore speciale.  Vedi `src/scoring.py`.
- **Rating dinamico** – algoritmo tipo Elo che aggiorna la forza competitiva di
  ogni atleta considerando i punti classifica ottenuti nei match.  Vedi
  `src/ratings.py`.
- **Matchmaking** – generazione di coppie di atleti bilanciate in base a peso,
  livello, rating, età e numero di precedenti.  Vedi `src/pairing.py`.
- **Backend del database** – selezionato dinamicamente tramite `src/db_runtime.py`.
  La UI per la scelta e l’esportazione si trova in `pages/0_Database.py`.
- **Parametri configurabili** – centralizzati in `src/settings.py` e persistenti
  nel database tramite `src/formula_config_service.py`.

Rispettando queste linee guida, ChatGPT potrà assistere nello sviluppo del
progetto in modo consistente e conforme all’architettura attuale.