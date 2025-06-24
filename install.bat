@echo off
REM This script sets up the Hassaniya Normalizer application.

REM Check for Python
python --version 2>NUL
if %errorlevel% neq 0 (
    echo Python is not installed or not in PATH.
    echo Please install Python 3.9+ and add it to your PATH.
    pause
    exit /b 1
)

REM Create a virtual environment
echo Creating virtual environment...
python -m venv .venv

REM Activate the virtual environment and install dependencies
echo Activating virtual environment and installing dependencies...
call .venv\Scripts\activate.bat

REM Install dependencies
pip install -e .[web]

echo.
echo Setup complete. You can now run the application using the run-ui.ps1 script.
pause