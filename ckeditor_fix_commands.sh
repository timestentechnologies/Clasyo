#!/bin/bash
# CKEditor CDN Fix - Template was loading old version from CDN

echo "Starting CKEditor CDN fix..."

# Step 1: Activate virtual environment
source /home3/opulentl/virtualenv/schoolsaas/3.13/bin/activate

# Step 2: Go to project directory
cd /home3/opulentl/schoolsaas

# Step 3: Collect static files (template updated)
echo "Collecting static files with updated template..."
python manage.py collectstatic --noinput

# Step 4: Restart application (you'll need to do this manually)
echo "=========================================="
echo "CKEditor CDN fix completed!"
echo "=========================================="
echo ""
echo "FIXED: Updated template from CKEditor 4.16.2 to 4.25.1-lts"
echo ""
echo "CRITICAL STEPS:"
echo "1. Restart your web application NOW"
echo "2. Clear browser cache (Ctrl+Shift+Del)"
echo "3. Test lesson plan form - security warning should be GONE"
echo ""
echo "The template was loading old version from CDN - now fixed!"
