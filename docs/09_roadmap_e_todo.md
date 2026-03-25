# Roadmap e TODO

Questo documento traccia lo stato di avanzamento del progetto e le attività
previste. L'applicazione è una Web app Streamlit con database SQLite per la
gestione di una lega di lotta. Alcune funzionalità sono già operative,
altre sono in via di perfezionamento.

## Già implementato

- setup progetto Python / Streamlit
- database SQLite con SQLAlchemy e creazione automatica all'avvio
- pagina atleti
- pagina eventi
- pagina incontri
- scoring sperimentale
- classifica aggregata
- rating dinamico (Elo-like)
- matchmaking assistito
- parametri centralizzati in `src/settings.py`

## Da rifinire a breve

- **Taratura di ritiro e forfait**: il rating e lo scoring riducono già l'impatto
  di questi match, ma i valori potrebbero essere ulteriormente calibrati.
- **Interfaccia utente**: migliorare la selezione/scrittura del team, uniformare
  i testi e rendere più chiare le pagine.
- **Mostrare dettagli**: fornire un breakdown dei punti (weight factor,
  performance bonus, ecc.) e dell'indice mismatch nella UI avanzata,
  mantenendo la schermata principale snella.
- **Pulizia codice**: separare meglio la logica di servizio dalla
  presentazione e centralizzare eventuali controlli di business.

## Prossimi step consigliati

1. **Status degli incontri**: introdurre gli stati `scheduled` e `completed`.
   Il matchmaking dovrebbe poter generare match programmati da confermare.
2. **Editing degli incontri**: permettere di modificare gli incontri
   esistenti (esito, punteggi, pesi, ecc.) tramite l'interfaccia.
3. **Gestione team**: normalizzare la struttura delle squadre in tabella
   dedicata e aggiungere filtri/ordinamenti per team.
4. **Filtri classifica avanzati**: aggiungere filtri per categoria di peso,
   periodo temporale, stile o fascia d'età.
5. **Preset federali**: permettere di salvare e ricaricare configurazioni
   di parametri in base alle categorie ufficiali.
6. **Pagina admin parametri**: creare un'interfaccia Streamlit che consenta
   di modificare `SCORING_SETTINGS`, `RATINGS_SETTINGS` e
   `MATCHMAKING_SETTINGS` senza cambiare codice.
7. **Documentazione utente**: separare la documentazione tecnica da
   quella per gli utenti/allenatori, includendo una guida rapida.
8. **Deployment condiviso**: predisporre il deploy dell'app su un
   server pubblico (ad esempio su Heroku, Render o un VPS) con
   database centralizzato.
   - **Database PostgreSQL**: sostituire l'SQLite locale con un PostgreSQL
     condiviso per consentire l'utilizzo multi‑utente tramite link.
   - **Migrazione dati**: predisporre script di migrazione del database e
     utilizzare SQLAlchemy per supportare entrambi i back‑end.
   - **Sicurezza e autenticazione**: aggiungere un layer di autenticazione
     per proteggere l'area amministrativa e i dati.

## Evoluzioni di medio periodo

- **Area admin protetta**: gestione degli utenti, diritti di modifica
  parametri e ricalcolo globale dei punteggi.
- **Parametri nel database**: spostare i dizionari di settings in una
  tabella, con log delle modifiche (chi, quando, valore precedente e
  nuovo).
- **Versionamento e ricalcolo**: memorizzare la versione dei parametri
  applicata a ciascun match e fornire una funzione per rigenerare i
  punteggi quando cambiano le regole.
- **Export e statistiche**: esportare i dati in CSV/PDF, generare
  reportistica avanzata e statistiche (rating offensivo/difensivo,
  progression chart, ecc.).
- **Autenticazione utenti**: introdurre login per atleti, allenatori e
  amministratori, eventualmente integrando sistemi OAuth o JWT.

## Debiti tecnici noti

- assenza di migrazioni DB (utilizzo diretto di `create_all`) – da
  sostituire con Alembic o simili quando si passerà a PostgreSQL
- modello `team` non normalizzato (attualmente solo un campo testuale)
- il modello `Match` rappresenta prevalentemente incontri completati;
  bisognerà separare la gestione dei match pianificati
- logica admin non ancora separata dalla logica utente
- validazioni di business semplificate (es. pesi, limiti età) da
  approfondire

## Scelte da confermare in futuro

- formula definitiva del rating (K adattivo, decadimento temporale,
  differenziazione per stile)
- formula definitiva dell'indice mismatch (ponderazione delle componenti
  e soglie di rifiuto)
- utilizzo del peso reale registrato o del `default_weight`
- logica esatta di gestione forfait e ritiro (es. punteggio minimo
  garantito o penalità ulteriore)
- struttura finale di serie/divisioni/promozioni