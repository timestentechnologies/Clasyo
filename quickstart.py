#!/usr/bin/env python
"""
Quick Start Script for School Management System
This script sets up the database and creates initial data
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_saas.settings')
django.setup()

from django.contrib.auth import get_user_model
from tenants.models import School
from subscriptions.models import SubscriptionPlan
from core.models import AcademicYear
from datetime import date, timedelta

User = get_user_model()

def create_superuser():
    """Create superuser if doesn't exist"""
    if not User.objects.filter(email='admin@school.com').exists():
        User.objects.create_superuser(
            email='admin@school.com',
            password='admin123',
            first_name='Super',
            last_name='Admin',
            role='superadmin'
        )
        print("✓ Superuser created: admin@school.com / admin123")
    else:
        print("✓ Superuser already exists")

def create_subscription_plans():
    """Create default subscription plans"""
    plans = [
        {
            'name': 'Free Trial',
            'slug': 'free-trial',
            'plan_type': 'free_trial',
            'price': 0,
            'billing_cycle': 'monthly',
            'trial_days': 30,
            'max_students': 50,
            'max_teachers': 5,
            'max_staff': 3,
        },
        {
            'name': 'Basic Plan',
            'slug': 'basic',
            'plan_type': 'basic',
            'price': 99,
            'billing_cycle': 'monthly',
            'trial_days': 7,
            'max_students': 100,
            'max_teachers': 20,
            'max_staff': 10,
        },
        {
            'name': 'Standard Plan',
            'slug': 'standard',
            'plan_type': 'standard',
            'price': 299,
            'billing_cycle': 'monthly',
            'trial_days': 14,
            'max_students': 500,
            'max_teachers': 50,
            'max_staff': 20,
        },
        {
            'name': 'Premium Plan',
            'slug': 'premium',
            'plan_type': 'premium',
            'price': 599,
            'billing_cycle': 'monthly',
            'trial_days': 14,
            'max_students': 1000,
            'max_teachers': 100,
            'max_staff': 50,
        },
    ]
    
    for plan_data in plans:
        plan, created = SubscriptionPlan.objects.get_or_create(
            slug=plan_data['slug'],
            defaults=plan_data
        )
        if created:
            print(f"✓ Created plan: {plan.name}")
    
    print(f"✓ Total subscription plans: {SubscriptionPlan.objects.count()}")

def create_demo_school():
    """Create a demo school"""
    trial_plan = SubscriptionPlan.objects.filter(plan_type='free_trial').first()
    
    school, created = School.objects.get_or_create(
        slug='demo-school',
        defaults={
            'name': 'Demo School',
            'email': 'demo@school.com',
            'phone': '+1234567890',
            'address': '123 Education Street',
            'city': 'Education City',
            'state': 'State',
            'country': 'Country',
            'postal_code': '12345',
            'subscription_plan': trial_plan,
            'is_trial': True,
            'trial_end_date': date.today() + timedelta(days=30),
            'is_active': True,
            'is_verified': True,
        }
    )
    
    if created:
        print(f"✓ Created demo school: {school.name}")
        print(f"  Access at: http://localhost:8000/school/demo-school/")
    else:
        print("✓ Demo school already exists")
    
    return school

def create_school_admin(school):
    """Create school admin user"""
    if not User.objects.filter(email='school@demo.com').exists():
        User.objects.create_user(
            email='school@demo.com',
            password='school123',
            first_name='School',
            last_name='Admin',
            role='admin',
            is_active=True
        )
        print("✓ School admin created: school@demo.com / school123")
    else:
        print("✓ School admin already exists")

def create_academic_year():
    """Create current academic year"""
    current_year = date.today().year
    year, created = AcademicYear.objects.get_or_create(
        name=f"{current_year}-{current_year+1}",
        defaults={
            'start_date': date(current_year, 4, 1),
            'end_date': date(current_year+1, 3, 31),
            'is_active': True,
        }
    )
    if created:
        print(f"✓ Created academic year: {year.name}")
    else:
        print("✓ Academic year already exists")

def main():
    print("""
    ╔══════════════════════════════════════════════════════╗
    ║  School Management System - Quick Start Setup       ║
    ╚══════════════════════════════════════════════════════╝
    """)
    
    print("\n1. Creating superuser...")
    create_superuser()
    
    print("\n2. Creating subscription plans...")
    create_subscription_plans()
    
    print("\n3. Creating demo school...")
    school = create_demo_school()
    
    print("\n4. Creating school admin...")
    create_school_admin(school)
    
    print("\n5. Creating academic year...")
    create_academic_year()
    
    print("""
    ╔══════════════════════════════════════════════════════╗
    ║              Setup Complete!                         ║
    ╚══════════════════════════════════════════════════════╝
    
    🎉 Your School Management System is ready!
    
    Access Points:
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    📌 Main Site:        http://localhost:8000
    📌 Admin Panel:      http://localhost:8000/admin
    📌 Demo School:      http://localhost:8000/school/demo-school/
    
    Login Credentials:
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    Super Admin:
      Email: admin@school.com
      Password: admin123
    
    School Admin:
      Email: school@demo.com
      Password: school123
    
    Next Steps:
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    1. Login to admin panel
    2. Explore the demo school
    3. Add students, teachers, and classes
    4. Configure fees and examinations
    5. Customize settings
    
    For help, see README.md
    
    Happy managing! 🎓
    """)

if __name__ == '__main__':
    main()
