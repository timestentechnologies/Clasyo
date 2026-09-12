Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "  Clasyo / SchoolSaaS - Initial Machine Setup" -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Check Python
try {
    $pyVer = python --version 2>&1
    Write-Host "[OK] Python detected: $pyVer" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Python is not found in your system PATH!" -ForegroundColor Red
    pause
    exit 1
}

# 2. Check/create venv
Write-Host "`n[1/5] Checking virtual environment..." -ForegroundColor Yellow
if (-not (Test-Path "venv")) {
    Write-Host "Creating virtual environment in .\venv ..."
    python -m venv venv
} else {
    Write-Host "Virtual environment already exists."
}

# 3. Activate venv
Write-Host "`n[2/5] Activating virtual environment..." -ForegroundColor Yellow
& .\venv\Scripts\Activate.ps1

# 4. Install dependencies
Write-Host "`n[3/5] Upgrading pip and installing requirements..." -ForegroundColor Yellow
python -m pip install --upgrade pip
pip install -r requirements.txt

# 5. Check .env
Write-Host "`n[4/5] Checking configuration..." -ForegroundColor Yellow
if (-not (Test-Path ".env")) {
    Write-Host "[NOTICE] No .env file found in project root. Please copy your .env file here!" -ForegroundColor Yellow
} else {
    Write-Host "[OK] .env configuration file detected." -ForegroundColor Green
}

# 6. Apply migrations
Write-Host "`n[5/5] Applying database migrations..." -ForegroundColor Yellow
python manage.py migrate

Write-Host "`n===================================================" -ForegroundColor Green
Write-Host "  Setup Complete!" -ForegroundColor Green
Write-Host "  To start the server, run .\run.ps1 or double-click run.bat" -ForegroundColor Green
Write-Host "===================================================" -ForegroundColor Green
