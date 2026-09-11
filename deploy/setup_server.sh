#!/usr/bin/env bash
# ==============================================================================
# Automated Server Setup for Oracle Cloud (Ubuntu 22.04 / 24.04 LTS)
# ==============================================================================
set -e

echo ">>> [1/7] Updating system packages..."
sudo apt update && sudo apt upgrade -y

echo ">>> [2/7] Installing required system packages (Python, Nginx, Redis, Git, Build tools)..."
sudo apt install -y python3 python3-pip python3-venv python3-dev \
    build-essential libssl-dev libffi-dev \
    nginx redis-server git curl ufw \
    pkg-config default-libmysqlclient-dev

echo ">>> [3/7] Configuring Oracle Cloud Ubuntu Firewall (iptables + ufw)..."
# Oracle Cloud Ubuntu includes strict iptables rules by default.
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo netfilter-persistent save || sudo apt install -y iptables-persistent && sudo netfilter-persistent save

# Also allow in UFW
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable

echo ">>> [4/7] Ensuring Redis is enabled and running..."
sudo systemctl enable redis-server
sudo systemctl restart redis-server

echo ">>> [5/7] Creating project directories..."
mkdir -p /home/ubuntu/schoolsaas/staticfiles
mkdir -p /home/ubuntu/schoolsaas/media
mkdir -p /home/ubuntu/schoolsaas/logs

echo ">>> [6/7] Setting permissions..."
sudo chown -R ubuntu:www-data /home/ubuntu/schoolsaas
sudo chmod -R 775 /home/ubuntu/schoolsaas/media
sudo chmod -R 775 /home/ubuntu/schoolsaas/staticfiles

echo ">>> [7/7] Basic server setup complete!"
echo "Next steps:"
echo "1. Clone your repository to /home/ubuntu/schoolsaas (or copy files)"
echo "2. Create the virtualenv: python3 -m venv /home/ubuntu/schoolsaas/venv"
echo "3. Run: bash /home/ubuntu/schoolsaas/deploy/deploy.sh"
