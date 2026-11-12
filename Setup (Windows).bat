@echo off
setlocal EnableDelayedExpansion
rem ===========================================================================================
rem  OoT Remake Randomizer - first-time setup for Windows
rem
rem  Double-click this once. It:
rem    1. installs Python 3.14 for your Windows user if you don't have Python 3.14 or newer
rem       (with winget if it's available, otherwise the official installer from python.org),
rem    2. installs the Python packages the randomizer and the item tracker need (requirements.txt),
rem    3. makes double-clicking .py / .pyw files run them with Python (for your user only).
rem  Nothing needs administrator rights. Run it again after downloading a new randomizer version.
rem ===========================================================================================
cd /d "%~dp0"
title OoT Remake Randomizer setup
set "PYVER=3.14.0"
set "PYARGS=/quiet InstallAllUsers=0 PrependPath=1 Include_launcher=1 InstallLauncherAllUsers=0 AssociateFiles=1 Include_pip=1 Include_test=0"

echo OoT Remake Randomizer setup
echo ===========================
echo.

rem ---- 1. Find or install Python 3.14 or newer -------------------------------------------
call :find_python
if defined PY goto :have_python

echo [1/3] Python 3.14 or newer was not found. Installing Python %PYVER% for your user...
echo.
where winget >nul 2>nul
if errorlevel 1 goto :download
echo Trying winget...
winget install --exact --id Python.Python.3.14 --scope user --silent --accept-package-agreements --accept-source-agreements --override "%PYARGS%"
call :find_python
if defined PY goto :installed

:download
set "ARCH=amd64"
if /i "%PROCESSOR_ARCHITECTURE%"=="ARM64" set "ARCH=arm64"
set "URL=https://www.python.org/ftp/python/%PYVER%/python-%PYVER%-%ARCH%.exe"
set "INSTALLER=%TEMP%\python-%PYVER%-%ARCH%.exe"
echo Downloading %URL%
curl.exe -L --fail -o "%INSTALLER%" "%URL%"
if errorlevel 1 goto :download_failed
echo Running the Python installer. This takes a minute and no window opens...
"%INSTALLER%" %PYARGS%
del "%INSTALLER%" >nul 2>nul
call :find_python
if not defined PY goto :not_visible

:installed
echo Installed Python %PYVER%.

:have_python
echo [1/3] Using Python: !PY!
echo.

rem ---- 2. Install the packages ------------------------------------------------------------
echo [2/3] Installing the randomizer's packages from requirements.txt...
!PY! -m pip install --upgrade pip >nul 2>nul
!PY! -m pip install --upgrade -r requirements.txt
if errorlevel 1 goto :pip_failed
echo.

rem ---- 3. Let .py / .pyw files open with Python ---------------------------------------------
echo [3/3] Making .py and .pyw files open with Python, for your Windows user...
set "PYDIR="
!PY! -c "import sys, os; print(os.path.dirname(sys.executable))" > "%TEMP%\ootr_pydir.txt" 2>nul
set /p PYDIR=<"%TEMP%\ootr_pydir.txt"
del "%TEMP%\ootr_pydir.txt" >nul 2>nul
if not exist "!PYDIR!\pythonw.exe" goto :no_pythonw
reg add "HKCU\Software\Classes\.py" /ve /d "Python.File" /f >nul
reg add "HKCU\Software\Classes\.pyw" /ve /d "Python.NoConFile" /f >nul
reg add "HKCU\Software\Classes\Python.File\shell\open\command" /ve /d "\"!PYDIR!\python.exe\" \"%%1\" %%*" /f >nul
reg add "HKCU\Software\Classes\Python.NoConFile\shell\open\command" /ve /d "\"!PYDIR!\pythonw.exe\" \"%%1\" %%*" /f >nul
echo Done. If double-clicking ootr_remake.pyw still opens another app, right-click it, choose
echo "Open with", then "Choose another app", pick Python and tick "Always".
goto :finished

:no_pythonw
echo Skipped: pythonw.exe wasn't found in "!PYDIR!".
echo You can still start the randomizer with "Start Randomizer (Windows).bat".

:finished
echo.
echo ===========================================================================================
echo  Setup finished. Start the randomizer by double-clicking "Start Randomizer (Windows).bat"
echo  or ootr_remake.pyw.
echo ===========================================================================================
echo.
pause
exit /b 0

:download_failed
echo.
echo The download failed. Check your internet connection, or install Python 3.14 yourself from
echo https://www.python.org/downloads/ - tick "Add python.exe to PATH" - and run this file again.
goto :fail

:not_visible
echo.
echo Python was installed, but this window can't see it yet.
echo Close this window and double-click "Setup (Windows).bat" again.
goto :fail

:pip_failed
echo.
echo Installing the packages failed. The messages above say why; often there is no internet connection.
goto :fail

:fail
echo.
pause
exit /b 1

rem ---- helpers --------------------------------------------------------------------------------
rem find_python: sets PY to a command that runs Python 3.14 or newer, or leaves it empty
:find_python
set "PY="
call :try py -3.14
if not defined PY call :try py -3
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Launcher\py.exe" call :try "%LOCALAPPDATA%\Programs\Python\Launcher\py.exe" -3.14
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python314\python.exe" call :try "%LOCALAPPDATA%\Programs\Python\Python314\python.exe"
if not defined PY call :try python
exit /b 0

:try
%* -c "import sys; sys.exit(0 if sys.version_info >= (3, 14) else 1)" >nul 2>nul
if not errorlevel 1 set "PY=%*"
exit /b 0
