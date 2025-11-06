#!/usr/bin/env python
"""
Script to create all Django app structures for the School Management System
"""
import os
from pathlib import Path

# Define all apps with their configurations
APPS = {
    'fees': {
        'verbose_name': 'Fee Management',
        'models': ['FeeGroup', 'FeeType', 'FeeMaster', 'FeeDiscount', 'FeeCollection', 'FeeInvoice']
    },
    'examinations': {
        'verbose_name': 'Examination System',
        'models': ['ExamType', 'Exam', 'ExamSchedule', 'ExamAttendance', 'MarksGrade', 'ExamResult']
    },
    'online_exam': {
        'verbose_name': 'Online Examination',
        'models': ['QuestionBank', 'OnlineExam', 'ExamQuestion', 'StudentExam', 'ExamAnswer']
    },
    'homework': {
        'verbose_name': 'Homework Management',
        'models': ['Homework', 'HomeworkSubmission', 'HomeworkEvaluation']
    },
    'human_resource': {
        'verbose_name': 'Human Resource',
        'models': ['Department', 'Designation', 'Staff', 'StaffAttendance', 'Payroll', 'Salary']
    },
    'leave_management': {
        'verbose_name': 'Leave Management',
        'models': ['LeaveType', 'LeaveApplication', 'LeaveBalance']
    },
    'communication': {
        'verbose_name': 'Communication',
        'models': ['Notice', 'Event', 'Message', 'EmailTemplate', 'SMSTemplate']
    },
    'chat': {
        'verbose_name': 'Chat System',
        'models': ['ChatRoom', 'ChatMessage', 'ChatParticipant']
    },
    'library': {
        'verbose_name': 'Library Management',
        'models': ['BookCategory', 'Book', 'LibraryMember', 'BookIssue', 'Fine']
    },
    'inventory': {
        'verbose_name': 'Inventory Management',
        'models': ['ItemCategory', 'Item', 'Supplier', 'ItemStore', 'ItemIssue', 'ItemSell']
    },
    'transport': {
        'verbose_name': 'Transport Management',
        'models': ['Route', 'Vehicle', 'Driver', 'TransportAssignment']
    },
    'dormitory': {
        'verbose_name': 'Dormitory Management',
        'models': ['Dormitory', 'RoomType', 'Room', 'RoomAllocation']
    },
    'attendance': {
        'verbose_name': 'Attendance System',
        'models': ['StudentAttendance', 'SubjectAttendance', 'AttendanceReport']
    },
    'lesson_plan': {
        'verbose_name': 'Lesson Planning',
        'models': ['Lesson', 'Topic', 'LessonPlan']
    },
    'certificates': {
        'verbose_name': 'Certificates & ID Cards',
        'models': ['CertificateTemplate', 'StudentCertificate', 'IDCardTemplate', 'StudentIDCard']
    },
    'reports': {
        'verbose_name': 'Reports',
        'models': ['ReportTemplate', 'CustomReport']
    },
    'frontend': {
        'verbose_name': 'Frontend CMS',
        'models': ['Page', 'Menu', 'News', 'Gallery', 'Course', 'Testimonial']
    },
    'superadmin': {
        'verbose_name': 'Super Admin',
        'models': []
    },
}


def create_app_structure(app_name, config):
    """Create complete app structure"""
    app_dir = Path(app_name)
    app_dir.mkdir(exist_ok=True)
    
    print(f"Creating {app_name} app...")
    
    # Create __init__.py
    (app_dir / '__init__.py').write_text('')
    
    # Create apps.py
    apps_content = f'''from django.apps import AppConfig


class {app_name.replace('_', ' ').title().replace(' ', '')}Config(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = '{app_name}'
    verbose_name = '{config["verbose_name"]}'
'''
    (app_dir / 'apps.py').write_text(apps_content)
    
    # Create models.py
    models_content = '''from django.db import models
from django.utils.translation import gettext_lazy as _


# Add your models here
'''
    (app_dir / 'models.py').write_text(models_content)
    
    # Create admin.py
    admin_content = '''from django.contrib import admin

# Register your models here
'''
    (app_dir / 'admin.py').write_text(admin_content)
    
    # Create views.py
    views_content = '''from django.shortcuts import render
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin

# Create your views here
'''
    (app_dir / 'views.py').write_text(views_content)
    
    # Create urls.py
    urls_content = f'''from django.urls import path
from . import views

app_name = '{app_name}'

urlpatterns = [
    # Add your URL patterns here
]
'''
    (app_dir / 'urls.py').write_text(urls_content)
    
    # Create forms.py
    forms_content = '''from django import forms

# Add your forms here
'''
    (app_dir / 'forms.py').write_text(forms_content)
    
    # Create migrations directory
    migrations_dir = app_dir / 'migrations'
    migrations_dir.mkdir(exist_ok=True)
    (migrations_dir / '__init__.py').write_text('')
    
    print(f"✓ Created {app_name} app structure")


def main():
    print("Creating Django app structures...")
    print("=" * 60)
    
    base_dir = Path(__file__).parent
    os.chdir(base_dir)
    
    for app_name, config in APPS.items():
        create_app_structure(app_name, config)
    
    print("=" * 60)
    print("✓ All app structures created successfully!")
    print("\nNext steps:")
    print("1. Add the apps to TENANT_APPS or SHARED_APPS in settings.py")
    print("2. Implement models in each app")
    print("3. Run migrations")
    print("4. Implement views and templates")


if __name__ == '__main__':
    main()
