@echo off
echo ===================================================
echo   Starting Clasyo / SchoolSaaS Local Server...
echo ===================================================
echo.

if not exist "venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found!
    echo Please run setup.bat first to set up the environment and install packages.
    echo.
    pause
    exit /b 1
)

call venv\Scripts\activate.bat

echo Server is starting at http://127.0.0.1:8000
echo Press Ctrl+C in this window to stop the server.
echo.

:: Automatically open default browser after a brief delay
start "" http://127.0.0.1:8000

python manage.py runserver
