@echo off
echo ===================================================
echo   Clasyo / SchoolSaaS - Initial Machine Setup
echo ===================================================
echo.

:: 1. Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not found in your system PATH!
    echo Please install Python (3.12, 3.13, or 3.14) and ensure "Add Python to PATH" is checked.
    echo.
    pause
    exit /b 1
)

echo [1/5] Checking virtual environment...
if not exist "venv" (
    echo Creating virtual environment in .\venv ...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
) else (
    echo Virtual environment already exists.
)

echo.
echo [2/5] Activating virtual environment...
call venv\Scripts\activate.bat

echo.
echo [3/5] Upgrading pip and installing requirements...
python -m pip install --upgrade pip
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [WARNING] Some dependencies had warnings or issues during install.
)

echo.
echo [4/5] Checking configuration...
if not exist ".env" (
    echo [NOTICE] No .env file found in project root.
    echo Please copy your .env file from your other machine to this folder!
) else (
    echo .env configuration file detected.
)

echo.
echo [5/5] Applying database migrations...
python manage.py migrate

echo.
echo ===================================================
echo   Setup Complete!
echo   To start the server anytime, simply double-click run.bat
echo ===================================================
echo.
pause
