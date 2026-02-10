@echo off
REM LNNTÉ Phone Number Verifier - Setup Script for Windows
REM Run this script once to set up the application

echo ============================================
echo LNNTÉ Phone Number Verifier - Setup
echo ============================================
echo.

cd /d "%~dp0"

REM Check for Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH.
    echo Please install Python 3.9 or later from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

echo [1/4] Creating virtual environment...
python -m venv venv
if errorlevel 1 (
    echo ERROR: Failed to create virtual environment.
    pause
    exit /b 1
)

echo [2/4] Activating virtual environment...
call venv\Scripts\activate.bat

echo [3/4] Installing Python dependencies...
pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies.
    pause
    exit /b 1
)

echo [4/4] Installing Playwright browsers...
playwright install chromium
if errorlevel 1 (
    echo ERROR: Failed to install Playwright browsers.
    pause
    exit /b 1
)

echo.
echo ============================================
echo Setup complete!
echo ============================================
echo.
echo To run the application:
echo   1. Double-click "run.bat"
echo   OR
echo   2. Run: venv\Scripts\python.exe main.py
echo.
pause
