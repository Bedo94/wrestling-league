# auth_roles

## Scopo

Progettare e implementare in modo incrementale il sistema di autenticazione e ruoli del progetto `wrestling_league`, mantenendo la compatibilità con l’architettura attuale e senza introdurre una riscrittura trasversale non necessaria.

## Stato

proposed

## Contesto stabile

- Il progetto prevede almeno due ruoli: `admin` e `user`.
- Le funzionalità amministrative dovranno essere protette e visibili solo agli admin.
- La pagina delle formule è da considerare area amministrativa.
- L’accesso alla pagina database è ancora da definire con precisione.
- L’app deve restare compatibile sia con esecuzione `streamlit run` sia con packaging futuro.
- Le modifiche devono restare incrementali e non invasive.

## Stato attuale

- Il progetto non ha ancora una gestione completa di autenticazione e ruoli.
- La distinzione funzionale tra utente standard e amministratore è già stata discussa a livello architetturale.
- La prima esigenza concreta è evitare che uno user veda o usi pagine amministrative come le formule.
- Il comportamento desiderato per la pagina database non è ancora deciso in modo definitivo.

## File coinvolti

Da verificare nel codice reale del repo, ma il workstream riguarda tipicamente:

- entrypoint Streamlit principale
- pagine amministrative
- eventuali moduli di bootstrap UI / session state
- eventuali moduli di configurazione o permessi
- futura documentazione di access control

## Decisioni già prese

- Non introdurre una riscrittura completa dell’app solo per il login.
- Le funzioni admin devono restare isolate e facili da proteggere.
- La pagina formule va trattata come non accessibile agli user.
- La pagina database resta sospesa come decisione di policy.
- La logica di business non deve spostarsi nelle pagine Streamlit.

## Assunzioni da verificare

- Qual è il punto migliore per centralizzare autenticazione e autorizzazione nell’app Streamlit.
- Se conviene una soluzione minimale iniziale oppure una libreria dedicata.
- Quanto facilmente le pagine correnti possono essere nascoste o bloccate in base al ruolo.
- Se esistono già helper di session state riusabili.

## Rischi / attenzione

- Evitare di spargere controlli di ruolo in molte pagine senza un punto centrale.
- Evitare che la UI nasconda funzioni senza proteggere davvero i flussi sottostanti.
- Evitare di introdurre dipendenze eccessive per una prima versione semplice.
- Considerare l’impatto futuro su packaging e su doppio backend.

## Prossimo passo consigliato

- Leggere il flusso di bootstrap dell’app e come vengono mostrate le pagine.
- Individuare il punto più centralizzato per introdurre il concetto di utente corrente e ruolo.
- Proporre una prima implementazione minima che distingua `admin` e `user`.
- Applicare il primo gating sulla pagina formule, lasciando sospesa la policy definitiva sulla pagina database.

## Prompt di ripartenza per Codex

Leggi `AGENTS.md`, `docs/project_context.md` e questo file.
Usa prima i file locali del progetto come riferimento.
Se il locale non basta e te lo chiedo esplicitamente, puoi consultare anche la repository GitHub o fonti online pertinenti.
Poi apri i file coinvolti e proponi una strategia incrementale per introdurre ruoli `admin` e `user`, mantenendo separate UI, logica e DB e senza riscrivere da zero.