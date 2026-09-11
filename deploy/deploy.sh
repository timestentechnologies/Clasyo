#!/usr/bin/env bash
# ==============================================================================
# Project Deployment & Update Script for School SaaS
# ==============================================================================
set -e

PROJECT_DIR="/home/ubuntu/schoolsaas"
VENV_DIR="$PROJECT_DIR/venv"

cd "$PROJECT_DIR"

echo ">>> [1/6] Activating virtual environment..."
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi
source "$VENV_DIR/bin/activate"

echo ">>> [2/6] Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo ">>> [3/6] Running database migrations..."
python manage.py migrate --noinput

echo ">>> [4/6] Collecting static files..."
python manage.py collectstatic --noinput

echo ">>> [5/6] Setting up systemd & Nginx configurations..."
sudo cp "$PROJECT_DIR/deploy/daphne.service" /etc/systemd/system/daphne.service
sudo cp "$PROJECT_DIR/deploy/celery.service" /etc/systemd/system/celery.service
sudo cp "$PROJECT_DIR/deploy/nginx.conf" /etc/nginx/sites-available/schoolsaas

sudo ln -sf /etc/nginx/sites-available/schoolsaas /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

sudo systemctl daemon-reload

echo ">>> [6/6] Restarting services..."
sudo systemctl enable daphne celery nginx
sudo systemctl restart daphne
sudo systemctl restart celery
sudo nginx -t && sudo systemctl restart nginx

echo "========================================================"
echo "Deployment completed successfully!"
echo "Daphne status: $(sudo systemctl is-active daphne)"
echo "Celery status: $(sudo systemctl is-active celery)"
echo "Nginx status:  $(sudo systemctl is-active nginx)"
echo "========================================================"
