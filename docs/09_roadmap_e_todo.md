# Roadmap e TODO

## Già implementato
- setup progetto Python / Streamlit
- database SQLite con SQLAlchemy
- creazione automatica DB all'avvio
- pagina atleti
- pagina eventi
- pagina incontri
- scoring base sperimentale
- classifica aggregata
- rating dinamico
- matchmaking assistito
- parametri centralizzati in settings

## Da rifinire a breve
- pesare meglio rating nei casi `Ritiro` e `Forfait`
- migliorare UI team selezionabile/scrivibile
- pulizia finale testi UI
- revisione continua formule mismatch
- revisione continua formule scoring

## Prossimi step consigliati
1. distinzione match `scheduled` vs `completed`
2. creazione da matchmaking a incontro programmato
3. editing incontri esistenti
4. gestione team più strutturata
5. filtri classifica più avanzati
6. preset categorie federali
7. pagina admin parametri
8. documentazione utente e amministratore separate

## Evoluzioni di medio periodo
- area admin protetta
- parametri salvati nel DB
- storico modifiche ai parametri
- ricalcolo rating/scoring on demand
- export PDF / CSV
- statistiche avanzate
- autenticazione utenti
- deployment condiviso

## Debiti tecnici noti
- assenza migrazioni DB vere
- `team` non normalizzato
- `Match` rappresenta soprattutto match completati
- logica admin non ancora separata
- poche validazioni business avanzate

## Scelte da confermare in futuro
- formula definitiva del rating
- formula definitiva mismatch
- peso reale da usare nel matchmaking
- logica esatta di gestione forfait e ritiro
- struttura finale serie / divisioni / promozioni
