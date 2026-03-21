# Regole di campionato - modello C.L.O.E.

Questo documento traduce il PDF descrittivo del C.L.O.E. in regole operative per l'applicazione. Quando il PDF non specifica un dettaglio implementativo, il punto viene marcato come **Da definire**.

## 1. Scopo del campionato

Il campionato nasce come formato progressivo per incontri amichevoli/Open Mats, con due obiettivi:

- aiutare i principianti a fare esperienza agonistica in modo graduale;
- offrire sfide più impegnative agli atleti più esperti.

## 2. Struttura generale

- Il campionato è organizzato per **edizioni periodiche**.
- Ogni edizione produce una **classifica generale**.
- La classifica è divisa in **serie** (ad esempio Serie 1, Serie 2, Serie 3).
- Gli atleti si incontrano solo con avversari della **stessa serie**.
- Gli atleti possono salire o scendere di serie in base ai risultati maturati.

## 3. Stile di lotta

- La classifica generale non è separata per età, peso o stile.
- Tuttavia, un atleta affronta soltanto avversari che condividono il **medesimo stile di lotta**.
- Esempi di stile: lotta libera, greco-romana.

## 4. Iscrizione e collocamento iniziale

- All'iscrizione, ogni atleta viene assegnato a una serie.
- Per gli atleti nuovi iscritti a campionato già iniziato, il posizionamento iniziale può dipendere dal **curriculum agonistico**.
- **Da definire:** criteri oggettivi per assegnare la serie iniziale.

## 5. Buoni match

- Ogni atleta riceve **3 o 4 buoni match** per edizione.
- I buoni match possono essere spesi accettando le proposte della Commissione Arbitrale.
- L'atleta può accettare o rifiutare il match proposto.
- **Da definire:** numero esatto di buoni per edizione, gestione di buoni non usati e regole di rifiuto.

## 6. Regola sul peso

- Non esistono categorie di peso rigide.
- Ogni match è valido solo se la differenza tra i due atleti rientra nella tolleranza massima di **±10 kg** rispetto al proprio peso.
- Esempio: un atleta di 60 kg può affrontare atleti tra 50 kg e 70 kg.

## 7. Effetto della differenza di peso

### 7.1 Principio generale

L'atleta più leggero riceve un vantaggio nei punti di classifica e nei punti segnati in gara. L'atleta più pesante riceve una riduzione corrispondente.

### 7.2 Punteggio globale di classifica

- Se un atleta accetta un avversario più pesante, il suo punteggio globale viene maggiorato.
- La maggiorazione si applica sia in caso di vittoria sia in caso di sconfitta.
- L'atleta più pesante vede ridursi il punteggio acquisito.
- Il testo descrive il punteggio dell'atleta più pesante come basato su un valore "di base doppio rispetto al perdente", ma non formalizza la formula completa.
- **Da definire:** formula esatta per punti classifica di vincitore e perdente.

### 7.3 Punti tecnici del match

- Anche i punti segnati durante il match sono maggiorati o ridotti in base alla differenza di peso.
- La variazione è proporzionale alla disparità di peso.
- Regola esplicita: **1 kg di svantaggio = +5%** ai punti dell'atleta più leggero.
- Regola esplicita: **10 kg di svantaggio = +50%** ai punti dell'atleta più leggero.
- L'incremento o la riduzione si applica al punteggio da usare nella classifica globale, mentre la vittoria sportiva del singolo incontro resta determinata dal punteggio tradizionale sul tappeto.

## 8. Donne e minorenni contro uomini seniores

- Donne e minorenni possono accettare di gareggiare contro uomini seniores.
- In questi casi si applica una **maggiorazione del 30%**.
- La maggiorazione vale sia in caso di vittoria sia in caso di sconfitta.
- Restano comunque attive anche le regole già previste per la differenza di peso.
- **Da definire:** se il bonus del 30% si applica solo all'atleta svantaggiato oppure anche come malus speculare all'altro atleta.

## 9. Determinazione della vittoria del match

- La vittoria del singolo incontro avviene in modo tradizionale, cioè per maggioranza di punti reali segnati sul tappeto.
- Le eventuali maggiorazioni o riduzioni servono per la classifica e non cambiano il vincitore sportivo del match.

## 10. Classifica

La classifica deve tener conto almeno di:

- vittorie e sconfitte;
- punti tecnici reali segnati;
- bonus/malus per differenza di peso;
- bonus per donne/minorenni contro uomini seniores;
- serie di appartenenza.

- **Da definire:** tie-breaker ufficiali in caso di pari punteggio.
- **Da definire:** modalità esatta di promozione e retrocessione tra serie.

## 11. Vincoli da implementare nell'app

L'app deve impedire o segnalare:

- match tra atleti di serie diverse;
- match tra stili diversi;
- match oltre la tolleranza di 10 kg;
- calcolo classifica senza dati minimi richiesti.

## 12. Parametri configurabili consigliati

Per evitare di fissare regole troppo rigide nel codice, i seguenti valori dovrebbero essere configurabili:

- numero di serie;
- numero di buoni match per edizione;
- percentuale bonus per kg di svantaggio;
- bonus massimo differenza peso;
- bonus donne/minorenni contro uomini seniores;
- punti base vittoria e sconfitta;
- soglie di promozione/retrocessione.
