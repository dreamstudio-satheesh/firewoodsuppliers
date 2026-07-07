@echo off
REM Firewood Billing — Build standalone EXE for Windows
REM Requires Python + PyInstaller installed
cd /d "%~dp0"
if not exist "venv" (
    python -m venv venv
    call venv\Scripts\activate.bat
    pip install -r requirements.txt
    pip install pyinstaller
) else (
    call venv\Scripts\activate.bat
)
echo Building FirewoodBilling.exe ...
pyinstaller --noconsole --onefile --name FirewoodBilling ^
    --add-data "assets;assets" ^
    --icon assets\icon.ico ^
    main.py
echo.
echo Done! EXE is in dist\FirewoodBilling.exe
pause
