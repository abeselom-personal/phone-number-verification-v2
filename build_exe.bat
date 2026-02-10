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
pip install pyinstaller python-dotenv requests pandas openpyxl playwright

echo.
echo Downloading Playwright Chromium browser...
python -m playwright install chromium

echo.
echo Building executable...
pyinstaller --clean lnnte_verifier.spec

echo.
echo Copying browsers to dist folder...
if exist "%USERPROFILE%\AppData\Local\ms-playwright" (
    xcopy "%USERPROFILE%\AppData\Local\ms-playwright" "dist\browsers\" /E /I /Y
    echo Browsers copied successfully!
) else (
    echo WARNING: Playwright browsers not found.
    echo The app will work in API mode only.
)

echo.
echo ============================================================
echo BUILD COMPLETE!
echo ============================================================
echo.
echo Output: dist\LNNTE_Verifier.exe
echo.
echo To distribute:
echo 1. Zip the entire 'dist' folder
echo 2. Share with users
echo.
pause
