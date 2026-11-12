@echo off
setlocal EnableDelayedExpansion
rem ===========================================================================================
rem  OoT Remake Randomizer - start the generator on Windows
rem
rem  Double-click this to open the randomizer. If a package it needs is missing (for example after
rem  downloading a new version), it installs requirements.txt first. If Python itself is missing,
rem  it runs "Setup (Windows).bat".
rem ===========================================================================================
cd /d "%~dp0"
title OoT Remake Randomizer

call :find_python
if defined PY goto :check_packages
echo Python 3.14 or newer isn't installed yet. Starting the setup...
echo.
call "Setup (Windows).bat"
call :find_python
if defined PY goto :check_packages
echo Python still wasn't found. Run "Setup (Windows).bat" and read its messages.
pause
exit /b 1

:check_packages

rem the packages the randomizer imports when it starts
!PY! -c "import raven, openpyxl" >nul 2>nul
if errorlevel 1 (
    echo Installing missing packages from requirements.txt...
    !PY! -m pip install --upgrade -r requirements.txt
    if errorlevel 1 (
        echo.
        echo Installing the packages failed. The messages above say why.
        pause
        exit /b 1
    )
)

rem pythonw runs without a console window, so this window can close straight away
set "PYDIR="
!PY! -c "import sys, os; print(os.path.dirname(sys.executable))" > "%TEMP%\ootr_pydir.txt" 2>nul
set /p PYDIR=<"%TEMP%\ootr_pydir.txt"
del "%TEMP%\ootr_pydir.txt" >nul 2>nul
if exist "!PYDIR!\pythonw.exe" (
    start "" "!PYDIR!\pythonw.exe" "%~dp0ootr_remake.pyw"
) else (
    !PY! "%~dp0ootr_remake.pyw"
    if errorlevel 1 pause
)
exit /b 0

rem ---- helpers --------------------------------------------------------------------------------
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
