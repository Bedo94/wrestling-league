# ui_improvements

## Scopo

Continuare il miglioramento della UI del progetto mantenendo leggere le pagine Streamlit, riusabili i componenti condivisi e coerente la distinzione tra orchestratori pagina e helper UI.

## Stato

active

## Contesto stabile

- `*_page_ui.py` è l’orchestratore della pagina.
- `*_ui.py` è oggi un contenitore pragmatico di componenti, tabelle o helper riusabili.
- Non va fatta ora una riorganizzazione massiva di `src/` in sottocartelle durante task ordinari.
- Le pagine Streamlit devono restare orchestration layer, non contenere logica di business.
- Le convenzioni UI devono essere riusabili ma senza introdurre framework interni inutilmente pesanti.

## Stato attuale

- Il progetto ha già avviato una modularizzazione della UI tramite file dedicati.
- Le tabelle sono un punto importante di riuso e leggibilità.
- Ci sono state iterazioni sul comportamento della visibilità colonne e sulla compattezza dei controlli associati alle tabelle.
- È emersa attenzione al comportamento delle tabelle nelle pagine formule, classifiche e accoppiamenti.
- È emerso un bug visivo per cui l’ultima colonna di alcune tabelle può risultare tagliata; una soluzione desiderabile è una distribuzione più robusta dello spazio disponibile senza hardcodare l’ultima colonna.

## File coinvolti

Da verificare nel codice reale del repo, ma il workstream riguarda tipicamente:

- pagine Streamlit di classifiche, formule, accoppiamenti
- orchestratori `*_page_ui.py`
- helper/componenti `*_ui.py`
- eventuali componenti tabellari riusabili

## Decisioni già prese

- Non riscrivere le pagine da zero.
- Non spostare ora i file UI in nuove cartelle solo per ordine.
- Privilegiare patch piccole e miglioramenti locali.
- Mantenere la documentazione delle tab formule coerente con la struttura delle altre tab.
- Non introdurre cambiamenti di comportamento non strettamente necessari se peggiorano la prevedibilità per l’utente.

## Assunzioni da verificare

- Quali moduli tabellari sono oggi davvero condivisi tra più pagine.
- Quali pagine usano già orchestratori `*_page_ui.py`.
- Se esiste già un componente centrale per la gestione responsive delle colonne.

## Rischi / attenzione

- Evitare di spostare logica di business in codice UI.
- Evitare refactor grafici troppo ampi mentre si correggono problemi specifici.
- Evitare duplicazioni di logica tabellare in più pagine.
- Verificare sempre che modifiche UI non cambino comportamenti attesi senza motivo.

## Prossimo passo consigliato

- Ricostruire dai file reali quali sono gli helper UI attualmente usati dalle pagine principali.
- Individuare il punto più centralizzato in cui migliorare la gestione della larghezza colonne.
- Proporre una patch incrementale che migliori il layout tabellare senza cambiare l’architettura.

## Prompt di ripartenza per Codex

Leggi `AGENTS.md`, `docs/project_context.md` e questo file.
Poi apri i file UI coinvolti nel workstream e proponi modifiche incrementali per migliorare riuso e robustezza delle tabelle, senza riscrivere da zero e senza spostare logica di business fuori da `src/`.