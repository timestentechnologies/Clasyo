Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "  Starting Clasyo / SchoolSaaS Local Server...     " -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path "venv\Scripts\Activate.ps1")) {
    Write-Host "[ERROR] Virtual environment not found!" -ForegroundColor Red
    Write-Host "Please run .\setup.ps1 or double-click setup.bat first." -ForegroundColor Yellow
    pause
    exit 1
}

& .\venv\Scripts\Activate.ps1

Write-Host "Server starting at http://127.0.0.1:8000" -ForegroundColor Green
Start-Process "http://127.0.0.1:8000"

python manage.py runserver
