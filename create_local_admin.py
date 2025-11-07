#!/usr/bin/env python
"""Create a local superadmin user for development"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_saas.settings')
django.setup()

from accounts.models import User

# Create superadmin
email = 'admin@local.com'
password = 'admin123'

if User.objects.filter(email=email).exists():
    print(f'User {email} already exists!')
else:
    user = User.objects.create_superuser(
        email=email,
        first_name='Admin',
        last_name='User',
        password=password,
        role='superadmin'
    )
    print(f'✅ Superadmin created successfully!')
    print(f'Email: {email}')
    print(f'Password: {password}')
    print(f'Login at: http://127.0.0.1:8000/accounts/login/')
