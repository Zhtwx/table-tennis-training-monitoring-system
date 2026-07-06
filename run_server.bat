@echo off
title Table Tennis Training Monitoring System

set "PROJECT_DIR=%~dp0"
set "PYTHON_EXE=%PROJECT_DIR%.venv\Scripts\python.exe"

echo Starting Table Tennis Training Monitoring System...
echo Web URL: http://localhost:5000
echo.

if not exist "%PYTHON_EXE%" (
    echo [ERROR] Project virtual environment was not found:
    echo %PYTHON_EXE%
    echo.
    echo Run these commands in the project folder:
    echo python -m venv .venv
    echo python -m pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

"%PYTHON_EXE%" -c "import flask" >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Flask is not installed in this project's .venv.
    echo.
    echo Run this command:
    echo "%PYTHON_EXE%" -m pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

cd /d "%PROJECT_DIR%"
"%PYTHON_EXE%" app.py
pause
