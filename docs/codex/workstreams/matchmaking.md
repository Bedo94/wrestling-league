# matchmaking

## Scopo

Continuare l’evoluzione del matchmaking di `wrestling_league` mantenendo coerenza con le regole di dominio attuali, con il rating dinamico e con il principio di match equilibrati ma non identici.

## Stato

active

## Contesto stabile

- Il matchmaking usa dati reali degli atleti.
- L’output deve includere accoppiamenti suggeriti e coppie candidate.
- Il mismatch index va interpretato come: più basso = meglio.
- Il sistema considera almeno peso, livello, rating, età e storico incontri.
- Il livello assegnato serve soprattutto nella fase iniziale, quando non ci sono ancora abbastanza incontri.
- Dopo la fase iniziale, il matchmaking deve basarsi soprattutto su rating e altri parametri competitivi, non sul solo livello assegnato.

## Stato attuale

- Il progetto ha già un matchmaking base.
- Il workstream matchmaking è una priorità alta di backlog.
- Nelle discussioni precedenti è emersa la necessità di mantenere il sistema trasparente e non black-box.
- È desiderata la possibilità di revisione manuale degli accoppiamenti proposti.

## File coinvolti

Da verificare nel codice reale del repo, ma questo workstream riguarda tipicamente:

- `src/pairing.py`
- moduli che costruiscono o mostrano classifiche/rating usati dal pairing
- pagine Streamlit degli accoppiamenti
- eventuali helper UI per tabelle di pairing

## Decisioni già prese

- Non riscrivere il modulo di pairing da zero se bastano miglioramenti incrementali.
- Le regole di dominio devono stare nei moduli di `src/`, non nella pagina.
- Il livello assegnato non deve retroagire in modo improprio sulla storia competitiva.
- Il rating dinamico è parte chiave della fase “matura” del matchmaking.
- La revisione manuale degli accoppiamenti resta importante.

## Assunzioni da verificare

- Quali pesi e coefficienti del mismatch siano già centralizzati in `settings.py` o altrove.
- Quanto il pairing attuale dipenda ancora dal livello assegnato.
- Se esistano già funzioni separate per scoring del pairing e costruzione dell’output tabellare.
- Quali vincoli su età e differenza peso siano applicati nel codice attuale.

## Rischi / attenzione

- Evitare duplicazione delle regole tra UI e `src/pairing.py`.
- Evitare modifiche che rompano l’interpretabilità del mismatch index.
- Evitare di mescolare nel pairing logiche che appartengono a scoring o rating.
- Verificare impatto delle modifiche sulla leggibilità delle tabelle di output.

## Prossimo passo consigliato

- Leggere `src/pairing.py` e i moduli che gli forniscono dati.
- Ricostruire l’uso attuale di livello assegnato, rating, peso, età e storico.
- Identificare il primo miglioramento incrementale più utile.
- Aggiornare la documentazione se cambia la logica decisionale del pairing.

## Prompt di ripartenza per Codex

Leggi `AGENTS.md`, `docs/project_context.md` e questo file.
Usa prima i file locali del progetto come riferimento.
Se il locale non basta e te lo chiedo esplicitamente, puoi consultare anche la repository GitHub o fonti online pertinenti.
Poi apri i file coinvolti e proponi modifiche incrementali al matchmaking, mantenendo il pairing trasparente, spiegabile e coerente con rating, peso, età e storico incontri.