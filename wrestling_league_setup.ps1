<#
    Questo script PowerShell automatizza l'installazione degli strumenti
    necessari per contribuire allo sviluppo del progetto **wrestling‑league**.

    Requisiti:
    - Windows 10/11 con l'utility **winget** installata e disponibile nel PATH.
    - Esecuzione del terminale PowerShell con privilegi di amministratore.

    Il progetto richiede Python >= 3.14. Tutte le dipendenze di terze parti
    (Streamlit, SQLAlchemy, pandas, ecc.) vengono installate più avanti
    tramite `uv sync` usando il file `pyproject.toml` del progetto.

    I comandi di installazione usano l'opzione `-e` (exact) per riferirsi
    ai pacchetti ufficiali. È possibile omettere l'opzione se non è
    strettamente necessaria.

    Dopo aver eseguito questo script, è possibile clonare il repository,
    sincronizzare l'ambiente Python con `uv` e avviare l'applicazione.

    Nota: se alcuni pacchetti sono già installati, `winget` li lascerà invariati.
#>

# Installa Python 3.14 (necessario per il progetto)
winget install -e --id Python.Python.3.14

# Installa Git (strumenti a linea di comando)
winget install -e --id Git.Git

# Installa TortoiseGit (client Git con interfaccia grafica per Windows)
winget install -e --id TortoiseGit.TortoiseGit

# Installa Visual Studio Code (IDE)
winget install -e --id Microsoft.VisualStudioCode

# Installa DB Browser for SQLite (strumento grafico per gestire database SQLite)
winget install -e --id DBBrowserForSQLite.DBBrowserForSQLite

# Installa uv (gestore rapido di pacchetti Python e ambienti virtuali)
winget install -e --id astral-sh.uv

# --- Azioni opzionali ---
# Le righe sottostanti possono essere scommentate per clonare il repository
# e configurare l’ambiente Python per il progetto.

# Posizionarsi in una cartella dove salvare i progetti
# cd "C:\percorso\al\tuo\workspace"

# Clona il repository wrestling-league da GitHub
# git clone https://github.com/Bedo94/wrestling-league.git

# Entra nella cartella del progetto
# cd wrestling-league

# Sincronizza l'ambiente Python utilizzando uv
# uv sync

# Avvia l'applicazione Streamlit
# uv run streamlit run app.py