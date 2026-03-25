# Uso di ChatGPT nel progetto

## Obiettivo

Usare ChatGPT come assistente allo sviluppo senza perdere controllo sul codice.

## Regola fondamentale

👉 Il codice sorgente è su GitHub  
👉 ChatGPT NON è la fonte del codice

## Come lavorare

### 1. Aprire una nuova chat
- entra nel Project
- crea nuova chat
- incolla START_NEW_CHAT_PROMPT

### 2. Lavorare su una modifica

- copia il file dal progetto locale
- incollalo nella chat
- descrivi cosa vuoi cambiare

Esempio:

"Questo è il file pairing.py attuale.  
Voglio migliorare il matchmaking aggiungendo X.  
Mantieni struttura esistente."

### 3. Applicare modifiche

- copia codice suggerito
- incollalo nel file locale
- testa

### 4. Salvare

```bash
git add .
git commit -m "descrizione"
git push