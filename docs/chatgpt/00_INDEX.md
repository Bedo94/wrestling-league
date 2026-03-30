# Indice dei documenti ChatGPT

Questa cartella contiene documenti destinati a **ChatGPT** per aiutarlo a comprendere
la struttura del progetto e a generare risposte contestuali durante lo sviluppo.
Questi file non sono pensati per gli utenti finali, ma come guida per l’assistente.

## Come utilizzare questi file

* I file in `docs/` sono la documentazione tecnica del progetto e vengono
  condivisi con gli sviluppatori e gli utenti esperti.
* I file in `docs/chatgpt/` servono invece a dare a ChatGPT il contesto
  necessario a rispondere correttamente alle domande su questa repository.
* Quando apri una nuova chat su questo progetto, specifica sempre di usare
  i file in `docs/chatgpt/` come fonte di verità.

## Indice dei file

* **00_INDEX.md** – questo indice.
* **01_idea_e_obiettivi.md** – descrizione dell’idea iniziale e degli obiettivi del progetto.
* **02_stack_e_setup.md** – descrizione dello stack tecnologico e delle modalità di setup,
  aggiornata per includere il supporto a PostgreSQL remoto e la possibilità di creare
  un eseguibile locale o deploy in cloud.
* **03_architettura.md** – struttura attuale del progetto con spiegazione dei moduli,
  inclusi i nuovi componenti per la selezione del database e l’esportazione dei dati.
* **04_scoring.md** – dettagli sulle formule di scoring, sui fattori di peso e bonus speciali.
* **05_rating_dinamico.md** – descrizione del rating dinamico, con i seed iniziali
  per livello e la formula Elo‑like utilizzata per gli aggiornamenti.
* **06_matchmaking.md** – spiegazione dell’algoritmo di matchmaking e delle componenti
  dell’indice di mismatch.
* **09_roadmap_e_todo.md** – pianificazione delle attività e roadmap aggiornata.
* **10_admin_e_configurazione_futura.md** – guida alla futura sezione amministrativa,
  gestione utenti e configurazioni via UI.

Questi file verranno aggiornati via via che il progetto si evolve.  In caso di
dubbio, consulta sempre il codice sorgente su GitHub e i documenti più recenti in
`docs/`.