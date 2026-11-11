@echo off
rem Installs the Python packages the randomizer needs (listed in requirements.txt).
rem Double-click this once after installing Python, and again after updating the randomizer.
cd /d "%~dp0"
echo Installing OoT Remake Randomizer requirements...
echo.
where py >nul 2>nul
if %errorlevel%==0 (
    py -3 -m pip install --upgrade -r requirements.txt
) else (
    python -m pip install --upgrade -r requirements.txt
)
echo.
if %errorlevel%==0 (
    echo Done. You can close this window and double-click ootr_remake.pyw.
) else (
    echo Something went wrong. Make sure Python 3.14 or newer is installed
    echo and that "Add python.exe to PATH" was ticked during setup.
)
echo.
pause
