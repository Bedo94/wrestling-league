# Wrestling League App

Applicazione web in Python per gestire una league interna di lotta ispirata al formato C.L.O.E. (Campionato di Lotta Olimpica Experience).

## Obiettivo

L'app serve a organizzare giornate di incontri tra studenti e atleti in modo semplice, gratuito e trasparente, con particolare attenzione a:

- abbinamenti equilibrati tra atleti dello stesso livello;
- tolleranza di peso controllata;
- classifica progressiva su più giornate;
- punteggi che tengano conto della differenza di peso e di altri fattori compensativi;
- promozione e retrocessione tra serie.

## Contesto

L'idea nasce dal regolamento C.L.O.E., pensato per favorire esperienza agonistica graduale per i principianti e incontri più impegnativi per atleti più esperti. Il campionato prevede serie, assenza di categorie di peso rigide, tolleranza massima di ±10 kg, bonus/malus legati alla differenza di peso e una maggiorazione aggiuntiva per donne e minorenni che affrontano uomini seniores. Il testo di partenza è il PDF `CLOE spiegazione.pdf` allegato al progetto.

## Obiettivi del software

### Obiettivi funzionali

- Registrare atleti, livello, peso e stile di lotta.
- Gestire iscrizione a una singola edizione della league.
- Assegnare o modificare la serie di appartenenza.
- Salvare proposte di match e loro accettazione/rifiuto.
- Registrare il risultato sportivo del match.
- Calcolare punti classifica tenendo conto delle regole C.L.O.E.
- Mostrare classifiche per serie e cronologia match.
- Supportare promozioni e retrocessioni tra edizioni.

### Obiettivi non funzionali

- Utilizzo gratuito per organizzazione interna studentesca.
- Semplicità d'uso da browser locale.
- Facile estensione delle formule di punteggio.
- Persistenza dei dati locale con SQLite.
- Codice leggibile e modulare.

## Stack tecnico iniziale

- **Frontend / UI**: Streamlit
- **Persistenza**: SQLite
- **Analisi dati**: pandas
- **Linguaggio**: Python 3.11+
- **Versioning**: Git + GitHub

## Struttura prevista del progetto

```text
wrestling-league/
│
├── app.py
├── README.md
├── RULES.md
├── REQUIREMENTS.md
├── requirements.txt
├── .gitignore
├── data/
│   └── league.db
├── src/
│   ├── db.py
│   ├── schema.py
│   ├── scoring.py
│   ├── ranking.py
│   ├── pairing.py
│   └── utils.py
└── pages/
    ├── 1_Atleti.py
    ├── 2_Eventi.py
    ├── 3_Incontri.py
    ├── 4_Classifiche.py
    └── 5_Accoppiamenti.py
```

## Milestone iniziale

La prima versione utile del progetto non deve ancora avere bracket grafici.

### MVP v0.1

- inserimento atleti;
- inserimento eventi/giornate;
- registrazione match;
- correzione risultati;
- classifica aggiornata automaticamente.

## Avvio locale (bozza)

### Opzione con `venv`

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

### Opzione con `uv`

```bash
uv venv
.venv\Scripts\activate
uv pip install -r requirements.txt
streamlit run app.py
```

## Stato del progetto

Il progetto è in fase di definizione dei requisiti e del regolamento operativo. La formula di punteggio sarà implementata in modo configurabile, perché il PDF fornisce i principi generali ma non specifica ogni dettaglio numerico necessario per automatizzare tutti i casi.
