# Roadmap e TODO

L'applicazione è una Web app Streamlit che ora può lavorare sia con un database **SQLite locale** sia con un **PostgreSQL remoto**, grazie al meccanismo di selezione runtime in `pages/0_Database.py` e `src/db_runtime.py`. Alcune funzionalità sono già operative, altre sono in via di perfezionamento o pianificate.

## Già implementato

- setup progetto Python / Streamlit
- database SQLite con SQLAlchemy e creazione automatica all’avvio
- **supporto a database PostgreSQL remoto**, selezionabile tramite la pagina “Database” (con import/export di snapshot SQLite o Excel)
- pagina atleti
- pagina eventi
- pagina incontri
- scoring sperimentale
- classifica aggregata
- rating dinamico (Elo‑like)
- matchmaking assistito
- parametri centralizzati in `src/settings.py`

## Da rifinire a breve

- **Migliorare l’affidabilità del backend PostgreSQL** (gestione errori di connessione, supporto host/porta custom).
- **Interfaccia utente**: uniformare testi e migliorare l’usabilità dopo l’introduzione della pagina Database.
- **Taratura ritiro/forfait**: ulteriori calibrazioni per scoring e rating.
- **Mostrare dettagli**: breakdown di weight factor, performance bonus e mismatch nella UI avanzata.
- **Pulizia codice**: separare meglio la logica di servizio dalla presentazione.

## Prossimi step consigliati

1. **Gestione utenti e autenticazione**
   - Implementare un sistema di login con tre ruoli principali:
     - **Admin**: può configurare il backend, modificare parametri, esportare il database e gestire utenti.
     - **Operatore gara**: può gestire atleti, eventi e match ma non modificare parametri globali o il backend.
     - **Cliente/ospite**: può consultare classifiche e statistiche senza modificare i dati.
   - Utilizzare un sistema di autenticazione (username/password, JWT, OAuth) e proteggere le pagine in base al ruolo.

2. **Packaging locale**
   - Preparare uno script di build con **PyInstaller** per creare un eseguibile (Windows/macOS/Linux). L’eseguibile deve poter leggere `DATABASE_URL` e configurare il backend tramite la pagina Database.

3. **Deploy su cloud**
   - Configurare un workflow di deployment (Heroku, Render, VPS o Docker) per pubblicare l’app. In questa modalità usare **solo PostgreSQL** e impostare le variabili d’ambiente `DATABASE_URL` e secret.
   - Valutare l’uso di container Docker per standardizzare l’ambiente.

4. **Gestione team avanzata**
   - Normalizzare la struttura delle squadre in una tabella e aggiungere filtri/ordinamenti per team.

5. **Status degli incontri**
   - Introdurre gli stati `scheduled` e `completed` nel modello `Match` per gestire match programmati e giocati.

6. **Editing degli incontri**
   - Permettere la modifica di match esistenti (esito, punteggi, pesi) mantenendo lo storico.

7. **Filtri classifica avanzati**
   - Aggiungere filtri per peso, periodo temporale, stile o fascia d’età; introdurre classifiche pound‑for‑pound.

8. **Preset federali e parametri**
   - Salvare e ricaricare configurazioni di parametri (categorie U20, Senior, fasce di peso); creare una pagina admin per modificare `SCORING_SETTINGS`, `RATINGS_SETTINGS` e `MATCHMAKING_SETTINGS` salvando i valori nel database.

9. **Documentazione utente**
   - Separare la documentazione tecnica da quella per allenatori/utenti. Fornire una guida rapida su avvio, scelta del database, accesso (quando disponibile l’auth) e interpretazione delle classifiche.

## Evoluzioni di medio periodo

- **Area admin protetta**: gestione completa degli utenti, backup e ricalcolo globale.
- **Parametri nel database**: spostare i dizionari di settings in tabelle con log delle modifiche.
- **Versionamento e ricalcolo**: memorizzare la versione dei parametri per ogni match e fornire funzioni di ricalcolo.
- **Export e statistiche avanzate**: report CSV/PDF, rating offensivo/difensivo, progression chart, analisi per team.
- **Login federato**: integrare provider esterni (Google, federazioni) per la gestione delle credenziali.
- **Supporto multi‑stile**: classifiche separate per stile (greco‑romana, libera, ecc.) e comparazioni pound‑for‑pound.

## Debiti tecnici noti

- Mancanza di migrazioni DB (uso diretto di `create_all`) – sostituire con Alembic per il supporto a PostgreSQL.
- Modello `team` non normalizzato (attualmente solo un campo testuale).
- Il modello `Match` rappresenta prevalentemente incontri completati; serve separare i match programmati.
- Logica admin non separata – la distinzione dei ruoli è solo concettuale finché non si implementa l’autenticazione.
- Validazioni di business semplificate (es. pesi, limiti età) da approfondire.

## Scelte da confermare in futuro

- Formula definitiva del rating (K adattivo, decadimento temporale, differenziazione per stile).
- Formula definitiva dell’indice mismatch.
- Utilizzo del peso reale registrato o del `default_weight`.
- Logica di gestione forfait e ritiro (punteggio minimo garantito o penalità ulteriore).
- Struttura finale di serie/divisioni/promozioni.