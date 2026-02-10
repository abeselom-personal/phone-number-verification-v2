@echo off
REM LNNTÉ Phone Number Verifier - Windows Launcher
REM Double-click this file to run the application

cd /d "%~dp0"

REM Check if virtual environment exists
if exist "venv\Scripts\python.exe" (
    echo Starting LNNTÉ Verifier...
    venv\Scripts\python.exe main.py
) else (
    echo Virtual environment not found.
    echo Please run setup.bat first to install dependencies.
    pause
)
