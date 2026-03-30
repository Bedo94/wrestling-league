# Architettura del progetto

## Struttura cartelle

    wrestling_league/
    ├── app.py
    ├── README.md
    ├── requirements.txt
    ├── pyproject.toml
    ├── data/
    │   └── league.db           # database SQLite di default
    ├── pages/                  # interfaccia Streamlit
    │   ├── 0_Database.py       # selezione backend (SQLite/PostgreSQL) e export dati
    │   ├── 1_Atleti.py         # CRUD atleti
    │   ├── 2_Eventi.py         # CRUD eventi/giornate
    │   ├── 3_Incontri.py       # inserimento risultati match
    │   ├── 4_Classifiche.py    # classifica filtrabile
    │   └── 5_Accoppiamenti.py  # suggerimenti di matchmaking
    ├── src/
    │   ├── __init__.py
    │   ├── athletes.py         # servizi operazioni atleti
    │   ├── database.py         # gestione engine e sessioni SQLAlchemy
    │   ├── db_runtime.py       # selezione runtime del database (SQLite/PostgreSQL)
    │   ├── events.py           # servizi operazioni eventi
    │   ├── export_service.py   # esportazione database in SQLite o Excel
    │   ├── formula_config_service.py # caricamento/salvataggio configurazioni formule
    │   ├── init_db.py          # creazione tabelle
    │   ├── levels.py           # definizione dei livelli e rating iniziali
    │   ├── matches.py          # servizi operazioni incontri
    │   ├── models.py           # modelli ORM (includono anche FormulaParameter)
    │   ├── pairing.py          # calcolo candidature e indice mismatch
    │   ├── ratings.py          # ricalcolo rating dinamico
    │   ├── reference_data.py   # dati di riferimento (es. stili, team)
    │   ├── scoring.py          # calcolo punti classifica
    │   ├── settings.py         # parametri centralizzati
    │   └── utils.py            # funzioni ausiliarie
    └── docs/                   # documentazione
        └── …

Rispetto alle versioni precedenti, la struttura include alcuni componenti nuovi per supportare il **database remoto** e l’esportazione dei dati. Le principali novità sono:

* **pages/0_Database.py** – pagina Streamlit che consente di selezionare il backend del database (SQLite locale o PostgreSQL remoto), caricare un file `.db` esistente e esportare le tabelle in formato SQLite o Excel. L’accesso a questa pagina dovrebbe essere limitato agli utenti con ruolo di amministratore.
* **src/db_runtime.py** – modulo che gestisce la configurazione dinamica del database. Mantiene in sessione la scelta dell’utente (sqlite o postgresql) e l’URL del database remoto, configura l’engine SQLAlchemy tramite `src/database.py` e inizializza le tabelle quando necessario.
* **src/export_service.py** – fornisce funzioni per esportare il database attivo in due formati:
  * **SQLite** – utile per backup locali o per trasferire i dati da PostgreSQL a un file locale;
  * **Excel** – genera un file `.xlsx` con tutte le tabelle, comodo per analisi manuali.
* **src/formula_config_service.py** – servizio che carica e salva i parametri di scoring, rating e matchmaking nel database (tabella `FormulaParameter`). Questo modulo prepara il terreno per una futura pagina amministrativa dedicata alla configurazione delle formule.

## Separazione delle responsabilità

`pages/` contiene esclusivamente i componenti dell’interfaccia utente. Ogni file rappresenta una pagina Streamlit. La pagina 0 permette di configurare il backend e di esportare i dati; le altre pagine gestiscono atleti, eventi, incontri, classifiche e accoppiamenti. La logica applicativa è delegata ai moduli in `src/`.

`src/database.py` centralizza la creazione e la configurazione dell’engine SQLAlchemy. Se non è definita una variabile d’ambiente `DATABASE_URL`, viene utilizzato un path SQLite predefinito (`data/league.db`). Espone funzioni come `configure_database()` per reimpostare l’engine e `get_database_url()` per verificare quale database è attivo.

`src/db_runtime.py` incapsula la logica di runtime switching del database. Offre funzioni per: determinare la modalità iniziale (SQLite o PostgreSQL) in base all’URL di connessione; salvare e applicare la scelta dell’utente in sessione Streamlit; inizializzare il database e le tabelle se necessario; restituire informazioni sull’attuale backend, mascherando eventuali password.

`src/export_service.py` permette di esportare il database attivo in formato SQLite e Excel. L’esportazione è controllata dall’interfaccia utente e accessibile solo agli amministratori. Lo snapshot SQLite esporta il DB remoto in un file portabile; l’export Excel crea un report multi‑foglio con tutte le tabelle.

`src/formula_config_service.py` gestisce la lettura e la persistenza dei parametri delle formule. I parametri sono salvati nella tabella `FormulaParameter` del database. In futuro, una pagina admin permetterà di modificarli senza cambiare il codice.

Altri moduli rimangono invariati rispetto alla documentazione precedente: `scoring.py` si occupa del calcolo dei punti classifica, `ratings.py` aggiorna il rating dinamico, e `pairing.py` genera le coppie di atleti e calcola l’indice di mismatch. Tali moduli non dipendono dal tipo di database in uso; interagiscono solo tramite SQLAlchemy.

## Flusso dei dati

1. **Selezione del database** – all’avvio dell’app o tramite la pagina “Database”, l’utente (solitamente l’admin) sceglie se utilizzare SQLite o PostgreSQL. Il modulo `db_runtime.py` applica la scelta configurando `database.py` e creando le tabelle se necessario.
2. **Inserimento e modifica dati** – le pagine `1_Atleti`, `2_Eventi` e `3_Incontri` permettono di inserire anagrafica, giornate e risultati. Queste pagine richiamano funzioni di `src/athletes.py`, `src/events.py` e `src/matches.py` che interagiscono con il modello ORM e salvano i record nel database attivo.
3. **Calcolo dei dati derivati** – quando si salvano gli incontri o cambiano i parametri, `scoring.py` e `ratings.py` calcolano punti classifica e rating dinamici. Il modulo `pairing.py` utilizza questi dati per generare suggerimenti di accoppiamenti equilibrati.
4. **Esportazione e backup** – tramite la pagina “Database”, l’admin può esportare un snapshot SQLite o un file Excel del database corrente. Questo è utile per backup, trasferimenti tra database o analisi offline.

## Principi fondamentali

* **Separazione tra dati grezzi e derivati** – i dati di base (atleti, eventi, match, punteggi tecnici) sono conservati come tali; i dati derivati (punti classifica, rating, indice mismatch) sono ricalcolati quando necessario. Questo permette di modificare le formule e ricalcolare i risultati senza perdere lo storico.
* **Configurabilità** – tutti i parametri rilevanti (scoring, rating, matchmaking) sono centralizzati in `src/settings.py` o salvati nel database tramite `formula_config_service.py`. La scelta del backend è mantenuta in sessione Streamlit.
* **Estensibilità** – l’architettura modulare facilita l’aggiunta di nuove funzionalità come l’autenticazione degli utenti, il packaging come eseguibile locale e il deploy in cloud. Ogni nuovo modulo dovrebbe seguire il principio di non dipendere direttamente dall’UI di Streamlit ma passare attraverso `src/`.