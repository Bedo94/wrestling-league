# Requisiti del sistema

Questo documento raccoglie i requisiti funzionali e non funzionali dell'app, derivati dal PDF C.L.O.E. e dalle esigenze emerse durante la progettazione.

## 1. Visione del prodotto

Realizzare una web app gratuita per gestire una league interna di lotta con:

- registrazione atleti;
- gestione eventi e incontri;
- calcolo classifica con logica C.L.O.E.;
- supporto a serie, stile di lotta e bonus/malus per squilibrio competitivo.

## 2. Attori

### 2.1 Organizzatore
Può creare edizioni, inserire atleti, proporre match, registrare risultati e correggere errori.

### 2.2 Atleta
Può essere iscritto a una o più edizioni e disputare gli incontri proposti per la propria serie.

### 2.3 Commissione Arbitrale
Ruolo logico che propone gli abbinamenti e valida i match accettati.

## 3. Requisiti funzionali

### RF-01 - Gestione atleti
Il sistema deve permettere di creare, visualizzare, modificare e disattivare un atleta.

Campi minimi:
- nome;
- cognome o nickname;
- sesso;
- data di nascita o flag minorenne;
- stile di lotta;
- peso di riferimento;
- livello;
- curriculum agonistico sintetico;
- serie assegnata;
- stato attivo/inattivo.

### RF-02 - Gestione edizioni
Il sistema deve permettere di creare un'edizione del campionato con:
- nome;
- data inizio/fine;
- note;
- numero massimo di buoni match;
- parametri di punteggio applicati a quell'edizione.

### RF-03 - Iscrizione atleta a edizione
Il sistema deve permettere di iscrivere un atleta a una specifica edizione e assegnarlo a una serie.

### RF-04 - Gestione serie
Il sistema deve permettere di definire più serie e associare ogni atleta iscritto a una sola serie per edizione.

### RF-05 - Gestione buoni match
Il sistema deve tracciare il numero di buoni match assegnati, usati, rifiutati e residui per ciascun atleta ed edizione.

### RF-06 - Proposta match
Il sistema deve permettere all'organizzatore di proporre un incontro tra due atleti e salvarne lo stato:
- proposto;
- accettato;
- rifiutato;
- disputato;
- annullato.

### RF-07 - Validazione match
Il sistema deve verificare automaticamente che:
- i due atleti appartengano alla stessa serie;
- i due atleti abbiano lo stesso stile di lotta;
- la differenza di peso non superi 10 kg;
- l'incontro sia consentito dai parametri dell'edizione.

### RF-08 - Registrazione risultato
Il sistema deve permettere di registrare:
- punteggio reale atleta A;
- punteggio reale atleta B;
- vincitore sportivo;
- metodo di vittoria opzionale;
- peso effettivo al momento del match;
- note.

### RF-09 - Calcolo bonus/malus peso
Il sistema deve calcolare bonus e malus legati alla differenza di peso.

Vincoli iniziali:
- 1 kg di svantaggio = +5% per l'atleta più leggero;
- 10 kg di svantaggio = +50% per l'atleta più leggero.

### RF-10 - Calcolo bonus donne/minorenni
Il sistema deve poter applicare una maggiorazione del 30% quando donne o minorenni affrontano uomini seniores.

### RF-11 - Calcolo punti classifica
Il sistema deve calcolare i punti classifica del match separando:
- risultato sportivo reale;
- punteggio tecnico reale;
- punteggio corretto per classifica;
- bonus/malus applicati.

### RF-12 - Classifiche
Il sistema deve mostrare classifiche per edizione e per serie con almeno:
- posizione;
- atleta;
- punti classifica;
- match disputati;
- vittorie;
- sconfitte;
- punti tecnici segnati;
- differenza peso media affrontata.

### RF-13 - Storico
Il sistema deve conservare lo storico di match, classifiche e serie per ogni edizione.

### RF-14 - Correzione risultati
Il sistema deve permettere di modificare un match già registrato e ricalcolare la classifica.

### RF-15 - Promozione e retrocessione
Il sistema deve supportare promozione e retrocessione tra serie al termine di un'edizione.

### RF-16 - Tracciabilità del calcolo
Per ogni match il sistema dovrebbe mostrare una spiegazione sintetica del calcolo punteggio, utile per trasparenza e debugging.

## 4. Requisiti non funzionali

### RNF-01 - Costo
La soluzione deve essere gratuita o a costo nullo per uso interno studentesco.

### RNF-02 - Facilità d'uso
L'interfaccia deve essere semplice e usabile da browser senza installare software lato atleta.

### RNF-03 - Manutenibilità
La logica di punteggio deve essere isolata dalla UI per permettere modifiche future.

### RNF-04 - Persistenza
I dati devono essere salvati localmente in SQLite nella prima versione.

### RNF-05 - Portabilità
L'app deve poter girare su Windows in sviluppo locale.

### RNF-06 - Auditabilità
Ogni modifica importante ai risultati dovrebbe essere registrata o almeno facilmente ricostruibile.

## 5. Requisiti aperti da definire

I seguenti punti non sono completamente specificati nel PDF e dovranno essere decisi prima del codice definitivo:

1. formula esatta dei punti classifica per vittoria e sconfitta;
2. regola esatta di composizione tra bonus peso e bonus 30%;
3. numero definitivo di buoni match per edizione;
4. criteri oggettivi di assegnazione iniziale della serie;
5. regole di promozione/retrocessione;
6. tie-breaker in classifica;
7. gestione dei rifiuti ai match;
8. eventuale supporto a più stili oltre libera e greco.

## 6. Priorità MVP

Per la prima versione, la priorità è:

1. atleti;
2. edizioni;
3. match;
4. calcolo punteggio;
5. classifica;
6. correzione risultati.

Bracket grafici, notifiche e condivisione pubblica possono arrivare dopo.
