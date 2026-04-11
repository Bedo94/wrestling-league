# Codex Context

Questa cartella contiene il contesto operativo specifico per lavorare con Codex su `wrestling_league`.

## Obiettivo

Ridurre la dipendenza dalla singola chat e permettere di riprendere il lavoro da PC diversi partendo solo da:

- progetto locale aggiornato, se disponibile
- repository Git aggiornata
- documentazione persistente nel repo
- file di workstream aggiornati

## Rapporto con `docs/chatgpt/`

`docs/chatgpt/` resta utile e non va rimosso subito.

Ruolo pratico:

- `docs/chatgpt/` = documentazione storica e contestuale già usata nel progetto
- `docs/codex/` = contesto operativo pensato per Codex, nuove sessioni, workstream paralleli e continuità cross-PC

## Struttura consigliata

- `docs/codex/README.md` → spiega il ruolo della cartella
- `docs/codex/workstreams/README.md` → spiega come gestire thread/workstream
- `docs/codex/workstreams/TEMPLATE.md` → modello base per nuovi workstream
- `docs/codex/workstreams/*.md` → un file per ogni workstream reale

## Regola pratica

Se una decisione è importante per continuare il lavoro in una nuova sessione o su un altro PC, deve finire qui o in un documento stabile del repo, non solo nella chat.