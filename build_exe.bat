@echo off
echo ============================================================
echo LNNTE Phone Verifier - Build Script for Windows
echo ============================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ from python.org
    pause
    exit /b 1
)

echo Installing dependencies...
pip install pyinstaller python-dotenv requests pandas openpyxl

echo.
echo Building executable (API mode only)...
pyinstaller --clean lnnte_verifier.spec

echo.
echo ============================================================
echo BUILD COMPLETE!
echo ============================================================
echo.
echo Output: dist\LNNTE_Verifier.exe
echo.
echo To distribute:
echo 1. Copy dist\LNNTE_Verifier.exe
echo 2. Create .env file with your 2captcha API key
echo 3. Share with users
echo.
pause
