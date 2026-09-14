@echo off
REM ==============================================================================
REM VoiceInk Windows Packaging Script
REM Builds standalone VoiceInk.exe using PyInstaller
REM ==============================================================================

echo [VoiceInk] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in system PATH.
    echo Please install Python 3.10+ from python.org and check "Add Python to PATH".
    pause
    exit /b 1
)

cd /d "%~dp0"

echo [VoiceInk] Setting up Windows virtual environment...
if not exist ".venv" (
    python -m venv .venv
)

call .venv\Scripts\activate.bat

echo [VoiceInk] Installing / updating required dependencies...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pyinstaller

echo [VoiceInk] Building Windows executable with PyInstaller...
pyinstaller --clean -y VoiceInk_win.spec

if errorlevel 1 (
    echo [ERROR] Build failed! Please inspect output above.
    pause
    exit /b 1
)

echo.
echo ==============================================================================
echo [SUCCESS] VoiceInk Windows application built successfully!
echo Executable location: %~dp0dist\VoiceInk\VoiceInk.exe
echo ==============================================================================
echo.
pause
