# Admin e configurazione futura

## Obiettivo

Consentire agli amministratori di gestire e configurare il sistema senza intervenire sul codice. Oltre a modificare i parametri di scoring, rating e matchmaking, l’area amministrativa dovrà permettere di scegliere il backend del database (SQLite locale o PostgreSQL remoto), gestire gli utenti e i relativi ruoli e supervisionare il deploy dell’app.

## Motivazione

L’utilizzo di un database remoto apre la strada a un uso **multi‑utente** e richiede una governance più completa. Pertanto:

- le formule e i pesi potrebbero cambiare;
- i parametri dello scoring potrebbero essere ricalibrati;
- il rating potrebbe essere ricalcolato;
- la selezione del database deve essere sicura;
- serve un sistema di autenticazione che distingua i privilegi degli utenti.

## Strategia attuale

- I parametri sono centralizzati in `src/settings.py`.
- La scelta del backend avviene tramite la pagina “Database” e `src/db_runtime.py`.
- Non esiste ancora un sistema di autenticazione; chiunque accede all’app può modificare tutto.

Questa base consente comunque di estendere facilmente il progetto con un pannello admin e login.

## Parametri già centralizzati

### Scoring
- soglia massima peso;
- bonus peso per kg;
- punti base vittoria/sconfitta;
- bonus massimo prestazione;
- soglia minorenne;
- bonus speciale;
- punti base per ritiro;
- punti base per forfait.

### Matchmaking
- differenza peso massima di default;
- peso della componente peso;
- peso della componente level;
- divisore rating;
- peso della componente età;
- penalità rematch;
- soglie di default level/età;
- opzioni di default per usare il rating e per evitare i rematch.

### Rating
- seed iniziali per level;
- default start rating;
- K factor;
- peso dei match normali;
- peso dei match per ritiro;
- peso dei match per forfait.

### Backend database
- modalità `sqlite` con path locale da creare o caricare;
- modalità `postgresql` con URL di connessione fornito dall’utente;
- variabili di sessione per ricordare la scelta;
- esportazione del database attivo (snapshot SQLite ed Excel).

## Evoluzione prevista

### Fase 1 – Configurazioni in file Python (completata)
Parametri in `src/settings.py`, backend scelto via variabili d’ambiente o pagina “Database”.

### Fase 2 – Pagina admin parametrica
Creare una pagina Streamlit riservata agli **admin** che permetta di:
- modificare i parametri di scoring, rating e matchmaking con input dinamici;
- salvare/ricaricare preset di parametri (es. categorie federali);
- scegliere il backend e avviare backup (download SQLite, export Excel);
- gestire gli utenti (creare account, assegnare ruoli, bloccare/sbloccare).

### Fase 3 – Parametri e utenti nel database
Spostare i dizionari di settings e la configurazione del backend in tabelle dedicate (`FormulaParameter`, `users`, `roles`). Ogni modifica deve essere registrata con:
- **chi** l’ha effettuata;
- **quando**;
- **valore precedente** e **valore nuovo**.

### Fase 4 – Autenticazione e autorizzazione
Introdurre un sistema di login (username/password, JWT, OAuth) e gestire sessioni e ruoli:

- **Admin**: accede a tutte le funzionalità (parametri, backend, export, gestione utenti).
- **Operatore gara**: gestisce atleti, eventi e match; attiva il calcolo di punti e rating; non può cambiare parametri globali né il backend.
- **Cliente/ospite**: consulta le classifiche e le statistiche senza modificare nulla.

### Fase 5 – Versionamento e ricalcolo
Quando parametri e configurazioni sono nel database, versionare ogni modifica e fornire funzioni per ricalcolare punteggi e rating con un set di parametri selezionato.

## Requisiti per farlo bene

- **Autenticazione/autorizzazione** sicura (password cifrate o provider esterni).
- **Gestione ruoli** centralizzata e non sparsa nel codice.
- **Separazione dati grezzi/derivati** per consentire ricalcoli.
- **Funzione di ricalcolo globale** quando cambiano parametri o backend.
- **Backup e export** sempre disponibili per gli admin.
- **Gestione backend** persistente e sicura (non mostrare le password in chiaro).
- **Distribuzione**: supporto all’eseguibile locale e al deploy cloud con configurazioni distinte.

## Dati che devono essere ricalcolabili

- **Punti classifica** (scoring).
- **Rating dinamico** (ratings).
- **Indice mismatch e pairing** (pairing).
- **Metriche sperimentali** (pound‑for‑pound, ecc.).

Ogni volta che cambiano parametri o backend bisogna rigenerare i dati derivati.

## Principio importante

Le formule e le configurazioni non devono appesantire la UI principale. L’interfaccia per gli utenti e gli operatori deve restare snella; i dettagli tecnici vivono nella documentazione, in una pagina informativa e nella futura sezione amministrativa protetta.