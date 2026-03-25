@echo off
setlocal EnableExtensions EnableDelayedExpansion
title Setup completo wrestling-league

echo.
echo ============================================
echo   Setup completo wrestling-league
echo ============================================
echo.

:: Riavvia come amministratore se necessario
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Richiedo i permessi di amministratore...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

:: Verifica winget
where winget >nul 2>&1
if %errorlevel% neq 0 (
    echo ERRORE: winget non e' disponibile su questo PC.
    echo Apri Microsoft Store / App Installer oppure aggiorna Windows.
    echo.
    pause
    exit /b 1
)

set "REPO_URL=https://github.com/Bedo94/wrestling-league.git"
set "DEFAULT_ROOT=%USERPROFILE%\Desktop\Progetti"

echo Cartella base dove creare o aggiornare il progetto:
echo [Invio] usa la cartella predefinita:
echo %DEFAULT_ROOT%
echo.
set /p "WORK_ROOT=Percorso cartella base: "

if not defined WORK_ROOT set "WORK_ROOT=%DEFAULT_ROOT%"

if not exist "%WORK_ROOT%" (
    echo Creo la cartella:
    echo %WORK_ROOT%
    mkdir "%WORK_ROOT%" >nul 2>&1
)

if not exist "%WORK_ROOT%" (
    echo ERRORE: impossibile creare la cartella base.
    echo.
    pause
    exit /b 1
)

set "PROJECT_DIR=%WORK_ROOT%\wrestling-league"

echo.
echo --------------------------------------------
echo Installazione strumenti
echo --------------------------------------------
call :install_pkg "Python 3.14" "Python.Python.3.14"
call :install_pkg "Git" "Git.Git"
call :install_pkg "TortoiseGit" "TortoiseGit.TortoiseGit"
call :install_pkg "Visual Studio Code" "Microsoft.VisualStudioCode"
call :install_pkg "DB Browser for SQLite" "DBBrowserForSQLite.DBBrowserForSQLite"
call :install_pkg "uv" "astral-sh.uv"

echo.
echo Aggiorno l'ambiente della sessione...
call :refresh_path

echo.
echo --------------------------------------------
echo Setup repository
echo --------------------------------------------

if exist "%PROJECT_DIR%\.git" (
    echo Repository gia' presente:
    echo %PROJECT_DIR%
    echo Eseguo git pull...
    git -C "%PROJECT_DIR%" pull
    if errorlevel 1 (
        echo.
        echo ATTENZIONE: git pull non riuscito.
        echo Controlla eventuali modifiche locali o conflitti.
        echo.
    )
) else (
    if exist "%PROJECT_DIR%" (
        echo.
        echo ATTENZIONE: la cartella esiste ma non contiene una repository Git:
        echo %PROJECT_DIR%
        echo.
        echo Rinomina o svuota la cartella e rilancia questo file.
        echo.
        pause
        exit /b 1
    )

    echo Clono la repository:
    echo %REPO_URL%
    git clone "%REPO_URL%" "%PROJECT_DIR%"
    if errorlevel 1 (
        echo.
        echo ERRORE: clone non riuscito.
        echo.
        pause
        exit /b 1
    )
)

echo.
echo --------------------------------------------
echo Sincronizzazione ambiente Python
echo --------------------------------------------
pushd "%PROJECT_DIR%"
uv sync
if errorlevel 1 (
    echo.
    echo ERRORE: uv sync non riuscito.
    echo Controlla la connessione internet o i messaggi sopra.
    popd
    echo.
    pause
    exit /b 1
)
popd

echo.
echo --------------------------------------------
echo Setup completato
echo --------------------------------------------
echo Progetto pronto in:
echo %PROJECT_DIR%
echo.
echo Prossimi passi consigliati:
echo 1. Apri la cartella in VS Code
echo 2. Avvia l'app con:
echo    uv run streamlit run app.py
echo.

choice /C SAE /N /M "Premi S per avviare Streamlit, A per aprire la cartella, E per uscire: "
if errorlevel 3 goto :end_ok
if errorlevel 2 goto :open_folder
if errorlevel 1 goto :start_streamlit

goto :end_ok

:open_folder
start "" "%PROJECT_DIR%"
goto :end_ok

:start_streamlit
start "wrestling-league-streamlit" cmd /k "cd /d ""%PROJECT_DIR%"" && uv run streamlit run app.py"
goto :end_ok

:install_pkg
set "PKG_LABEL=%~1"
set "PKG_ID=%~2"
echo.
echo [Installazione] %PKG_LABEL%
winget install -e --id %PKG_ID% --accept-source-agreements --accept-package-agreements
if errorlevel 1 (
    echo ATTENZIONE: winget ha restituito un errore per %PKG_LABEL%.
    echo Se il tool e' gia' installato, puoi ignorare il messaggio.
)
goto :eof

:refresh_path
for %%P in (
    "%ProgramFiles%\Git\cmd"
    "%ProgramFiles%\Git\bin"
    "%LocalAppData%\Programs\Python\Python314"
    "%LocalAppData%\Programs\Python\Python314\Scripts"
    "%USERPROFILE%\.local\bin"
    "%LocalAppData%\Programs\Microsoft VS Code\bin"
) do (
    if exist %%~P (
        echo %PATH% | find /I "%%~P" >nul
        if errorlevel 1 set "PATH=!PATH!;%%~P"
    )
)
goto :eof

:end_ok
echo.
echo Operazione terminata.
echo.
pause
exit /b 0
