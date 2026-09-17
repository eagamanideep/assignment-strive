@echo off
REM One-step setup + launch for Windows. Usage: double-click run.bat, or run it from cmd / PowerShell.
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment...
    py -3 -m venv .venv 2>nul || python -m venv .venv
    if errorlevel 1 (
        echo Python 3.10+ is required. Install it from https://www.python.org/downloads/ and tick "Add python.exe to PATH".
        pause
        exit /b 1
    )
    ".venv\Scripts\python.exe" -m pip install --upgrade pip
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
)

".venv\Scripts\python.exe" -m streamlit run app.py
pause
