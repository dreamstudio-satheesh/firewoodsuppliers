@echo off
REM Firewood Billing — Windows launcher
cd /d "%~dp0"
if not exist "venv" (
    python -m venv venv
    call venv\Scripts\activate.bat
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate.bat
)
pythonw main.py
