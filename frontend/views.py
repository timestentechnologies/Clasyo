from django.shortcuts import render, redirect
from django.views.generic import TemplateView, View
from django.contrib import messages
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.conf import settings
import os
import pdfkit
from subscriptions.models import SubscriptionPlan
from .models import PricingPlan, FAQ, PageContent, ContactMessage


class HomeView(TemplateView):
    """Homepage view"""
    template_name = 'frontend/home.html'


class AboutView(TemplateView):
    """About page view"""
    template_name = 'frontend/about.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['about_content'] = PageContent.objects.filter(page='about', is_active=True).first()
        context['faqs'] = FAQ.objects.filter(is_active=True, category='About').order_by('order')
        return context


class ContactView(View):
    """Contact page view with form handling"""
    template_name = 'frontend/contact.html'
    
    def get(self, request):
        contact_info = PageContent.objects.filter(page='contact', is_active=True).first()
        faqs = FAQ.objects.filter(is_active=True, category='Contact').order_by('order')
        return render(request, self.template_name, {
            'contact_info': contact_info,
            'faqs': faqs
        })
    
    def post(self, request):
        # Handle contact form submission
        name = request.POST.get('name')
        email = request.POST.get('email')
        phone = request.POST.get('phone', '')
        subject = request.POST.get('subject')
        message = request.POST.get('message')
        
        if name and email and subject and message:
            ContactMessage.objects.create(
                name=name,
                email=email,
                phone=phone,
                subject=subject,
                message=message
            )
            messages.success(request, 'Thank you for your message! We will get back to you soon.')
            return redirect('frontend:contact')
        else:
            messages.error(request, 'Please fill in all required fields.')
            return redirect('frontend:contact')


class PricingView(TemplateView):
    """Pricing page view"""
    template_name = 'frontend/pricing.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['plans'] = PricingPlan.objects.filter(is_active=True).order_by('order', 'price')
        context['faqs'] = FAQ.objects.filter(is_active=True, category='Pricing').order_by('order')
        return context


class FAQView(TemplateView):
    """FAQ page view"""
    template_name = 'frontend/faq.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get all active FAQs grouped by category
        faqs = FAQ.objects.filter(is_active=True).order_by('category', 'order')
        
        # Group FAQs by category
        faq_categories = {}
        for faq in faqs:
            if faq.category not in faq_categories:
                faq_categories[faq.category] = []
            faq_categories[faq.category].append(faq)
        
        context['faq_categories'] = faq_categories
        return context


class PrivacyPolicyView(TemplateView):
    """Privacy Policy page view"""
    template_name = 'frontend/privacy.html'


class TermsOfServiceView(TemplateView):
    """Terms of Service page view"""
    template_name = 'frontend/terms.html'


class LicenseView(TemplateView):
    """License page view"""
    template_name = 'frontend/license.html'


class DocumentationView(TemplateView):
    """Comprehensive documentation for the School SaaS system"""
    template_name = 'frontend/documentation.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Core Features
        context['core_features'] = [
            {
                'title': 'Multi-tenant Architecture',
                'description': 'Each school gets its own isolated environment with separate database schema',
                'icon': 'layers'
            },
            {
                'title': 'Role-based Access Control',
                'description': 'Different dashboards and permissions for admins, teachers, students, and parents',
                'icon': 'shield'
            },
            {
                'title': 'Academic Management',
                'description': 'Manage academic years, terms, classes, sections, and subjects',
                'icon': 'book-open'
            },
            {
                'title': 'Student Information System',
                'description': 'Comprehensive student profiles, attendance, and performance tracking',
                'icon': 'users'
            },
            {
                'title': 'Examination System',
                'description': 'Create and manage exams, grades, and report cards',
                'icon': 'file-text'
            },
            {
                'title': 'Fee Management',
                'description': 'Track fees, payments, and generate invoices',
                'icon': 'dollar-sign'
            },
            {
                'title': 'Library Management',
                'description': 'Manage books, track issues, and returns',
                'icon': 'book'
            },
            {
                'title': 'Transport Management',
                'description': 'Manage routes, vehicles, and track transportation',
                'icon': 'truck'
            },
            {
                'title': 'Dormitory Management',
                'description': 'Manage hostels, rooms, and boarders',
                'icon': 'home'
            },
            {
                'title': 'Communication Tools',
                'description': 'Messaging, notices, and announcements',
                'icon': 'message-square'
            },
            {
                'title': 'HR & Payroll',
                'description': 'Staff management, attendance, and payroll processing',
                'icon': 'briefcase'
            },
            {
                'title': 'Reports & Analytics',
                'description': 'Generate various reports and analytics',
                'icon': 'bar-chart-2'
            },
        ]
        
        # User Guides
        context['user_guides'] = [
            {
                'role': 'Administrator',
                'description': 'Learn how to manage your school\'s complete setup',
                'sections': [
                    'School Profile Setup',
                    'User Management',
                    'Academic Configuration',
                    'Fee Structure Setup',
                    'System Settings'
                ]
            },
            {
                'role': 'Teacher',
                'description': 'Guide for managing classes and student progress',
                'sections': [
                    'Class Management',
                    'Attendance Recording',
                    'Gradebook Management',
                    'Lesson Planning',
                    'Communication Tools'
                ]
            },
            {
                'role': 'Student',
                'description': 'How to access your academic information',
                'sections': [
                    'Viewing Timetable',
                    'Checking Grades',
                    'Accessing Study Materials',
                    'Submitting Assignments',
                    'Viewing Attendance'
                ]
            },
            {
                'role': 'Parent',
                'description': 'Monitoring your child\'s progress',
                'sections': [
                    'Viewing Child\'s Attendance',
                    'Checking Grades',
                    'Fee Payments',
                    'Communication with Teachers',
                    'Viewing School Notices'
                ]
            }
        ]
        
        # API Documentation
        context['api_endpoints'] = [
            {
                'endpoint': '/api/v1/students/',
                'method': 'GET',
                'description': 'List all students (requires authentication)'
            },
            {
                'endpoint': '/api/v1/attendance/',
                'method': 'POST',
                'description': 'Submit attendance data'
            },
            {
                'endpoint': '/api/v1/grades/',
                'method': 'GET',
                'description': 'Retrieve grade information'
            },
            {
                'endpoint': '/api/v1/fees/',
                'method': 'GET',
                'description': 'Retrieve fee information'
            }
        ]
        
        return context


def generate_pdf_documentation(request):
    """Generate PDF version of the documentation using pdfkit"""
    try:
        # Get the context data
        context = DocumentationView().get_context_data()
        
        # Render the HTML template
        html_string = render_to_string('frontend/documentation_pdf.html', context)
        
        # Configure pdfkit options
        options = {
            'page-size': 'A4',
            'margin-top': '20mm',
            'margin-right': '20mm',
            'margin-bottom': '20mm',
            'margin-left': '20mm',
            'encoding': 'UTF-8',
            'no-outline': None,
            'quiet': ''
        }
        
        # Generate PDF
        pdf = pdfkit.from_string(html_string, False, options=options)
        
        # Create HTTP response with PDF
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = 'filename="school_saas_documentation.pdf"'
        return response
        
    except Exception as e:
        return HttpResponse(f'Error generating PDF: {str(e)}', status=500)


class SchoolRegistrationView(View):
    """School registration with 7-day trial"""
    
    def post(self, request):
        from tenants.models import School
        from accounts.models import User
        from subscriptions.models import Subscription
        from datetime import timedelta
        from django.utils import timezone
        from django.contrib.auth import login
        
        try:
            # Get form data
            first_name = request.POST.get('first_name')
            last_name = request.POST.get('last_name')
            email = request.POST.get('email')
            phone = request.POST.get('phone', '')
            password = request.POST.get('password')
            password2 = request.POST.get('password2')
            
            school_name = request.POST.get('school_name')
            school_slug = request.POST.get('school_slug')
            school_email = request.POST.get('school_email')
            school_phone = request.POST.get('school_phone', '')
            school_address = request.POST.get('school_address', '')
            city = request.POST.get('city', '')
            country = request.POST.get('country', 'Kenya')
            postal_code = request.POST.get('postal_code', '')
            
            # Validation
            if password != password2:
                messages.error(request, 'Passwords do not match!')
                return redirect('frontend:home')
            
            if User.objects.filter(email=email).exists():
                messages.error(request, 'Email already registered!')
                return redirect('frontend:home')
            
            if School.objects.filter(slug=school_slug).exists():
                messages.error(request, 'School slug already taken. Please choose another.')
                return redirect('frontend:home')
            
            # Create School
            trial_end = timezone.now() + timedelta(days=7)
            school = School.objects.create(
                name=school_name,
                slug=school_slug,
                email=school_email,
                phone=school_phone,
                address=school_address,
                city=city,
                country=country,
                postal_code=postal_code,
                is_active=True,
                is_trial=True,
                trial_end_date=trial_end
            )
            
            # Create Admin User
            user = User.objects.create_user(
                email=email,
                first_name=first_name,
                last_name=last_name,
                phone=phone,
                role='admin',
                is_active=True,
                password=password
            )
            
            # Auto login
            login(request, user)
            
            messages.success(
                request, 
                f'Welcome to Clasyo! Your 7-day free trial has started. '
                f'You can access your dashboard at /school/{school_slug}/'
            )
            
            # Redirect to school dashboard
            from django.urls import reverse
            return redirect('core:dashboard', school_slug=school.slug)
            
        except Exception as e:
            messages.error(request, f'Registration failed: {str(e)}')
            return redirect('frontend:home')
