#!/usr/bin/env bash
# Exit on error
set -o errexit

# Install dependencies
pip install -r requirements.txt

# Run master database migrations, then all provisioned tenant databases
python manage.py migrate --noinput
python manage.py migrate_tenants

# Collect static files
python manage.py collectstatic --no-input

