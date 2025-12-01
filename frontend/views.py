from django.shortcuts import render, redirect
from django.views.generic import TemplateView, View
from django.contrib import messages
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.conf import settings
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from io import BytesIO
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
        # Use SubscriptionPlan as the single source of truth for plans
        context['plans'] = SubscriptionPlan.objects.filter(is_active=True).order_by('display_order', 'price')
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
        
        # Core Features - Enhanced with detailed descriptions
        context['core_features'] = [
            {
                'title': 'Multi-tenant Architecture',
                'description': 'Each school gets its own isolated environment with separate database schema, ensuring complete data isolation and security while optimizing resource utilization.',
                'icon': 'layers',
                'details': {
                    'overview': 'Our multi-tenant architecture allows multiple schools to share the same infrastructure while maintaining complete data isolation and security.',
                    'key_features': [
                        'Isolated database schemas for each school',
                        'Shared application layer for efficiency',
                        'Automatic resource scaling',
                        'Data backup and recovery per tenant',
                        'Custom domain support (your-school.clasyo.com)',
                        'SSL certificates for all schools'
                    ],
                    'benefits': [
                        'Cost-effective solution for schools',
                        'Automatic updates and maintenance',
                        'High availability and reliability',
                        'Data security and privacy compliance',
                        'Fast deployment and setup'
                    ],
                    'technical_specs': {
                        'database': 'PostgreSQL with schema isolation',
                        'application': 'Django framework with tenant middleware',
                        'deployment': 'Docker containers with Kubernetes orchestration',
                        'monitoring': '24/7 health checks and performance monitoring'
                    }
                }
            },
            {
                'title': 'Role-based Access Control',
                'description': 'Comprehensive permission system with granular access control for different user roles including administrators, teachers, students, and parents.',
                'icon': 'shield',
                'details': {
                    'overview': 'Advanced RBAC system ensures users only access information and features relevant to their role.',
                    'roles': [
                        {
                            'role': 'Super Administrator',
                            'permissions': 'Full system access, tenant management, system configuration'
                        }
                    ]
                }
            },
            {
                'title': 'Academic Management',
                'description': 'Complete academic structure management with Classes, Sections, Subjects, and Timetables',
                'icon': 'book-open',
                'details': {
                    'overview': 'Comprehensive academic management system supporting CBC and traditional curriculum structures',
                    'key_features': [
                        'Class and Section management',
                        'Subject allocation and scheduling',
                        'Timetable generation',
                        'Teacher assignment',
                        'Academic calendar management',
                        'CBC competency tracking'
                    ],
                    'benefits': [
                        'Streamlined academic operations',
                        'Efficient resource allocation',
                        'Automated scheduling',
                        'CBC compliance',
                        'Better academic planning'
                    ],
                    'modules': [
                        {
                            'module': 'Class Management',
                            'features': ['Create classes/grades', 'Numeric ordering', 'Description support', 'Active status management']
                        },
                        {
                            'module': 'Section Management',
                            'features': ['A, B, C sections', 'Class teacher assignment', 'Room allocation', 'Student capacity limits']
                        },
                        {
                            'module': 'Subject Management',
                            'features': ['Subject creation', 'Code assignment', 'Teacher allocation', 'Credit hours']
                        }
                    ]
                }
            },
            {
                'title': 'Student Information System',
                'description': 'Comprehensive student profiles with admission, attendance, and performance tracking',
                'icon': 'users',
                'details': {
                    'overview': 'Complete student lifecycle management from admission to graduation',
                    'key_features': [
                        'Student admission and enrollment',
                        'Personal information management',
                        'Attendance tracking',
                        'Academic performance records',
                        'Medical information',
                        'Parent/guardian details'
                    ],
                    'benefits': [
                        'Centralized student data',
                        'Easy access to student information',
                        'Comprehensive attendance tracking',
                        'Performance monitoring',
                        'Parent communication'
                    ],
                    'modules': [
                        {
                            'module': 'Student Registration',
                            'features': ['Admission number generation', 'Roll number assignment', 'Personal details', 'Contact information']
                        },
                        {
                            'module': 'Student Categories',
                            'features': ['Category creation', 'Description support', 'Active status management']
                        },
                        {
                            'module': 'Attendance System',
                            'features': ['Daily attendance', 'Monthly reports', 'Attendance analytics', 'Parent notifications']
                        }
                    ]
                }
            },
            {
                'title': 'Examination System',
                'description': 'Comprehensive exam management with online exams, grading, and report cards',
                'icon': 'file-text',
                'details': {
                    'overview': 'Complete examination management supporting both traditional and online assessments',
                    'key_features': [
                        'Exam creation and scheduling',
                        'Online exam support',
                        'Multiple question types',
                        'Grade management',
                        'Report card generation',
                        'Performance analytics'
                    ],
                    'benefits': [
                        'Streamlined exam processes',
                        'Online assessment capabilities',
                        'Automated grading',
                        'Comprehensive reporting',
                        'Performance tracking'
                    ],
                    'modules': [
                        {
                            'module': 'Exam Management',
                            'features': ['Exam types (Midterm, Final, Quiz)', 'Date scheduling', 'Class assignment', 'Subject linking']
                        },
                        {
                            'module': 'Online Exams',
                            'features': ['Multiple choice questions', 'True/False questions', 'Time limits', 'Passing percentage']
                        },
                        {
                            'module': 'Grade Management',
                            'features': ['Grade entry', 'Grade calculation', 'Report cards', 'Transcripts']
                        }
                    ]
                }
            },
            {
                'title': 'Fee Management',
                'description': 'Complete fee structure management with payment tracking and multiple payment methods',
                'icon': 'dollar-sign',
                'details': {
                    'overview': 'Comprehensive fee management system supporting various fee types and payment methods',
                    'key_features': [
                        'Fee structure setup',
                        'Multiple fee categories',
                        'Payment tracking',
                        'Invoice generation',
                        'Payment reminders',
                        'Financial reporting'
                    ],
                    'benefits': [
                        'Automated fee management',
                        'Multiple payment options',
                        'Reduced manual work',
                        'Better financial tracking',
                        'Parent convenience'
                    ],
                    'modules': [
                        {
                            'module': 'Fee Structure',
                            'features': ['Tuition fees', 'Transport fees', 'Library fees', 'Lab fees', 'Sports fees']
                        },
                        {
                            'module': 'Payment Collection',
                            'features': ['Cash payments', 'Card payments', 'Bank transfers', 'Online payments']
                        },
                        {
                            'module': 'Financial Reports',
                            'features': ['Fee collection reports', 'Outstanding fees', 'Payment analytics']
                        }
                    ]
                }
            },
            {
                'title': 'Library Management',
                'description': 'Complete library system with book catalog, issue tracking, and fine management',
                'icon': 'book',
                'details': {
                    'overview': 'Comprehensive library management system for efficient book tracking and management',
                    'key_features': [
                        'Book catalog management',
                        'Issue and return tracking',
                        'Fine calculation',
                        'Inventory management',
                        'Member management',
                        'Reservation system'
                    ],
                    'benefits': [
                        'Efficient library operations',
                        'Better book tracking',
                        'Automated fine calculation',
                        'Member management',
                        'Inventory control'
                    ]
                }
            },
            {
                'title': 'Communication Tools',
                'description': 'Messaging system, notices, announcements, and real-time chat',
                'icon': 'message-square',
                'details': {
                    'overview': 'Multi-channel communication system for effective school-staff-parent communication',
                    'key_features': [
                        'Internal messaging',
                        'Notice board',
                        'Announcements',
                        'Real-time chat',
                        'Email notifications',
                        'SMS integration'
                    ],
                    'benefits': [
                        'Improved communication',
                        'Real-time updates',
                        'Parent engagement',
                        'Staff coordination',
                        'Information dissemination'
                    ]
                }
            },
            {
                'title': 'Human Resource & Payroll',
                'description': 'Staff management, attendance, and payroll processing',
                'icon': 'briefcase',
                'details': {
                    'overview': 'Complete HR management system for school staff and payroll processing',
                    'key_features': [
                        'Staff management',
                        'Attendance tracking',
                        'Leave management',
                        'Payroll processing',
                        'Performance evaluation',
                        'Document management'
                    ],
                    'benefits': [
                        'Efficient HR operations',
                        'Automated payroll',
                        'Leave tracking',
                        'Performance monitoring',
                        'Document organization'
                    ]
                }
            },
            {
                'title': 'Reports & Analytics',
                'description': 'Comprehensive reporting system with PDF generation and data analytics',
                'icon': 'bar-chart-2',
                'details': {
                    'overview': 'Advanced reporting system with PDF generation using ReportLab and data analytics',
                    'key_features': [
                        'Academic reports',
                        'Financial reports',
                        'Attendance reports',
                        'Performance analytics',
                        'PDF generation',
                        'Excel exports'
                    ],
                    'benefits': [
                        'Data-driven decisions',
                        'Comprehensive insights',
                        'Professional reports',
                        'Export capabilities',
                        'Performance tracking'
                    ],
                    'technical_specs': {
                        'pdf_generation': 'ReportLab library',
                        'excel_support': 'OpenPyXL and Pandas',
                        'charting': 'Built-in Django templates',
                        'data_analysis': 'Pandas integration'
                    }
                }
            }
        ]
        
        # User Guides - Enhanced with detailed step-by-step instructions
        context['user_guides'] = [
            {
                'role': 'Super Administrator',
                'description': 'Complete system administration guide for managing multiple schools and platform configuration',
                'sections': [
                    {
                        'title': 'Platform Overview',
                        'steps': [
                            'Access the super admin dashboard at admin.clasyo.com',
                            'Monitor all school tenants from central dashboard',
                            'View system performance metrics and analytics',
                            'Manage platform-wide settings and configurations'
                        ]
                    },
                    {
                        'title': 'School Management',
                        'steps': [
                            'Create new school tenants with custom domains',
                            'Configure school-specific settings and branding',
                            'Manage subscription plans and billing',
                            'Monitor school usage and performance',
                            'Handle school support requests'
                        ]
                    },
                    {
                        'title': 'System Configuration',
                        'steps': [
                            'Configure global system settings',
                            'Manage payment gateways and integrations',
                            'Set up email and SMS gateways',
                            'Configure backup and disaster recovery',
                            'Monitor system health and performance'
                        ]
                    },
                    {
                        'title': 'User Management',
                        'steps': [
                            'Create and manage super admin accounts',
                            'Configure role-based permissions',
                            'Monitor user activity across schools',
                            'Handle security incidents and breaches',
                            'Manage API access and integrations'
                        ]
                    },
                    {
                        'title': 'Billing Management',
                        'steps': [
                            'Configure subscription plans and pricing',
                            'Manage invoicing and payments',
                            'Monitor revenue and financial metrics',
                            'Handle billing disputes and refunds',
                            'Generate financial reports'
                        ]
                    }
                ],
                'common_tasks': [
                    'Adding a new school to the platform',
                    'Configuring payment gateways',
                    'Managing system backups',
                    'Monitoring platform performance',
                    'Handling security incidents'
                ],
                'troubleshooting': [
                    'School login issues',
                    'Payment gateway problems',
                    'System performance optimization',
                    'Database maintenance',
                    'Security breach response'
                ]
            },
            {
                'role': 'School Administrator',
                'description': 'Complete school management guide for administrators to configure and manage their institution',
                'sections': [
                    {
                        'title': 'School Profile Setup',
                        'steps': [
                            'Navigate to Settings → School Profile',
                            'Enter basic school information (name, address, contact)',
                            'Upload school logo and branding materials',
                            'Configure academic calendar and terms',
                            'Set up grading system and assessment criteria',
                            'Configure fee structures and payment methods'
                        ]
                    },
                    {
                        'title': 'Academic Configuration',
                        'steps': [
                            'Create academic years and terms',
                            'Set up classes, sections, and divisions',
                            'Configure subjects and curriculum',
                            'Assign teachers to classes and subjects',
                            'Generate timetables automatically',
                            'Configure examination schedules'
                        ]
                    },
                    {
                        'title': 'User Management',
                        'steps': [
                            'Create user accounts for staff and students',
                            'Assign appropriate roles and permissions',
                            'Configure parent accounts and access',
                            'Manage user permissions and access control',
                            'Monitor user activity and login logs',
                            'Handle password resets and account issues'
                        ]
                    },
                    {
                        'title': 'Student Management',
                        'steps': [
                            'Register new students and assign admission numbers',
                            'Manage student records and personal information',
                            'Assign students to classes and sections',
                            'Track student attendance and performance',
                            'Manage student promotions and transfers',
                            'Generate student reports and certificates'
                        ]
                    },
                    {
                        'title': 'Financial Management',
                        'steps': [
                            'Configure fee structures and payment plans',
                            'Generate invoices and fee statements',
                            'Monitor fee payments and outstanding balances',
                            'Manage scholarships and discounts',
                            'Generate financial reports',
                            'Reconcile bank transactions'
                        ]
                    }
                ],
                'common_tasks': [
                    'Adding new students',
                    'Creating user accounts',
                    'Generating reports',
                    'Managing fee payments',
                    'Configuring academic settings'
                ],
                'best_practices': [
                    'Regular data backup',
                    'User training and support',
                    'Performance monitoring',
                    'Security compliance',
                    'Parent communication'
                ]
            },
            {
                'role': 'Teacher',
                'description': 'Comprehensive guide for teachers to manage classes, track student progress, and communicate with parents',
                'sections': [
                    {
                        'title': 'Class Management',
                        'steps': [
                            'Access assigned classes from dashboard',
                            'View class timetables and schedules',
                            'Manage student attendance daily',
                            'Record student behavior and conduct',
                            'Update class information and announcements',
                            'Monitor class performance metrics'
                        ]
                    },
                    {
                        'title': 'Gradebook Management',
                        'steps': [
                            'Access gradebook for assigned subjects',
                            'Create assignments and assessments',
                            'Enter student grades and scores',
                            'Calculate final grades and GPAs',
                            'Generate progress reports',
                            'Export grade data for analysis'
                        ]
                    },
                    {
                        'title': 'Lesson Planning',
                        'steps': [
                            'Create lesson plans and schedules',
                            'Upload teaching materials and resources',
                            'Share lesson plans with students',
                            'Track lesson completion and coverage',
                            'Collaborate with other teachers',
                            'Access curriculum guidelines and standards'
                        ]
                    },
                    {
                        'title': 'Assessment Management',
                        'steps': [
                            'Create tests and examinations',
                            'Configure grading rubrics and criteria',
                            'Schedule assessment periods',
                            'Monitor student submissions',
                            'Provide feedback and comments',
                            'Analyze assessment results'
                        ]
                    },
                    {
                        'title': 'Communication Tools',
                        'steps': [
                            'Send messages to students and parents',
                            'Post class announcements and notices',
                            'Schedule parent-teacher meetings',
                            'Share student progress updates',
                            'Respond to parent inquiries',
                            'Maintain communication logs'
                        ]
                    }
                ],
                'common_tasks': [
                    'Taking daily attendance',
                    'Entering grades',
                    'Communicating with parents',
                    'Creating lesson plans',
                    'Managing assignments'
                ],
                'tips': [
                    'Use mobile app for quick attendance',
                    'Set up automated grade notifications',
                    'Create reusable lesson templates',
                    'Schedule regular parent updates',
                    'Use data to identify struggling students'
                ]
            },
            {
                'role': 'Student',
                'description': 'Student guide for accessing academic information, submitting assignments, and staying connected with school activities',
                'sections': [
                    {
                        'title': 'Dashboard Navigation',
                        'steps': [
                            'Login to student portal using credentials',
                            'View personalized dashboard with upcoming events',
                            'Check announcements and notices',
                            'Access quick links to common tasks',
                            'View unread messages and notifications',
                            'Monitor academic progress at a glance'
                        ]
                    },
                    {
                        'title': 'Academic Information',
                        'steps': [
                            'View class timetable and schedule',
                            'Check current grades and GPA',
                            'Access assignment deadlines and submissions',
                            'Download study materials and resources',
                            'View attendance records',
                            'Check exam schedules and results'
                        ]
                    },
                    {
                        'title': 'Assignment Management',
                        'steps': [
                            'View assigned tasks and deadlines',
                            'Download assignment requirements',
                            'Submit completed assignments online',
                            'Track submission status and feedback',
                            'View graded assignments and comments',
                            'Manage assignment drafts and files'
                        ]
                    },
                    {
                        'title': 'Communication',
                        'steps': [
                            'Send messages to teachers and administrators',
                            'Participate in class discussions',
                            'Join study groups and forums',
                            'Respond to teacher inquiries',
                            'Access school announcements',
                            'Manage notification preferences'
                        ]
                    },
                    {
                        'title': 'Personal Information',
                        'steps': [
                            'Update personal profile information',
                            'Manage account security settings',
                            'View fee statements and payment history',
                            'Download academic transcripts',
                            'Access library resources',
                            'Manage extracurricular activities'
                        ]
                    }
                ],
                'common_tasks': [
                    'Checking grades',
                    'Submitting assignments',
                    'Viewing timetable',
                    'Communicating with teachers',
                    'Managing profile'
                ],
                'mobile_app_features': [
                    'Push notifications for assignments',
                    'Quick attendance check-in',
                    'Mobile assignment submission',
                    'Instant messaging',
                    'Offline access to materials'
                ]
            },
            {
                'role': 'Parent',
                'description': 'Parent guide for monitoring child\'s academic progress, managing fees, and staying connected with school',
                'sections': [
                    {
                        'title': 'Child Progress Monitoring',
                        'steps': [
                            'Login to parent portal using credentials',
                            'View children\'s academic performance',
                            'Check grades and subject-wise progress',
                            'Monitor attendance patterns',
                            'View teacher comments and feedback',
                            'Access progress reports and transcripts'
                        ]
                    },
                    {
                        'title': 'Fee Management',
                        'steps': [
                            'View fee statements and breakdowns',
                            'Check payment history and receipts',
                            'Pay fees online using various methods',
                            'Set up automatic payment reminders',
                            'Apply for scholarships or discounts',
                            'Download fee receipts for tax purposes'
                        ]
                    },
                    {
                        'title': 'Communication with Teachers',
                        'steps': [
                            'Send messages to teachers and staff',
                            'Request parent-teacher meetings',
                            'Respond to teacher communications',
                            'View school announcements and notices',
                            'Participate in parent forums',
                            'Provide feedback and suggestions'
                        ]
                    },
                    {
                        'title': 'School Activities',
                        'steps': [
                            'View school calendar and events',
                            'Check exam schedules and results',
                            'Monitor homework and assignments',
                            'Access school policies and guidelines',
                            'Participate in school committees',
                            'Volunteer for school activities'
                        ]
                    },
                    {
                        'title': 'Account Management',
                        'steps': [
                            'Manage multiple child accounts',
                            'Update contact information',
                            'Configure notification preferences',
                            'Set up payment methods',
                            'Access mobile app features',
                            'Manage security settings'
                        ]
                    }
                ],
                'common_tasks': [
                    'Paying school fees',
                    'Checking child\'s grades',
                    'Communicating with teachers',
                    'Viewing attendance',
                    'Accessing reports'
                ],
                'benefits': [
                    'Real-time progress updates',
                    'Convenient fee payments',
                    'Direct teacher communication',
                    'Comprehensive reporting',
                    'Mobile access'
                ]
            }
        ]
        
        # API Documentation - Based on actual Django models and URL patterns
        context['api_endpoints'] = [
            {
                'endpoint': '/api/v1/students/',
                'method': 'GET',
                'description': 'List all students with pagination and filtering (requires authentication)',
                'parameters': {
                    'page': 'integer - Page number (default: 1)',
                    'limit': 'integer - Results per page (default: 20)',
                    'class_id': 'integer - Filter by class ID',
                    'search': 'string - Search by name or admission number',
                    'is_active': 'boolean - Filter by active status'
                }
            },
            {
                'endpoint': '/api/v1/students/',
                'method': 'POST',
                'description': 'Create a new student record'
            },
            {
                'endpoint': '/api/v1/students/{id}/',
                'method': 'GET',
                'description': 'Retrieve specific student details'
            },
            {
                'endpoint': '/api/v1/students/{id}/',
                'method': 'PUT',
                'description': 'Update student information'
            },
            {
                'endpoint': '/api/v1/attendance/',
                'method': 'POST',
                'description': 'Submit attendance data for students',
                'request_body': {
                    'student_id': 'integer - Student ID (required)',
                    'date': 'date - Attendance date (YYYY-MM-DD, required)',
                    'status': 'string - present/absent/late (required)',
                    'remarks': 'string - Additional notes (optional)',
                    'marked_by': 'integer - Teacher ID (required)'
                }
            },
            {
                'endpoint': '/api/v1/attendance/',
                'method': 'GET',
                'description': 'Retrieve attendance records'
            },
            {
                'endpoint': '/api/v1/examinations/',
                'method': 'GET',
                'description': 'Retrieve examination information and schedules',
                'parameters': {
                    'exam_type': 'string - Filter by exam type (midterm/final/quiz)',
                    'class_id': 'integer - Filter by class ID',
                    'subject_id': 'integer - Filter by subject ID',
                    'start_date': 'date - Filter by start date'
                }
            },
            {
                'endpoint': '/api/v1/examinations/',
                'method': 'POST',
                'description': 'Create new examination'
            },
            {
                'endpoint': '/api/v1/grades/',
                'method': 'POST',
                'description': 'Submit student grades and scores',
                'request_body': {
                    'student_id': 'integer - Student ID (required)',
                    'exam_id': 'integer - Examination ID (required)',
                    'subject_id': 'integer - Subject ID (required)',
                    'marks': 'float - Obtained marks (required)',
                    'grade': 'string - Grade letter (auto-calculated if not provided)',
                    'remarks': 'string - Teacher remarks (optional)',
                    'graded_by': 'integer - Teacher ID (required)'
                }
            },
            {
                'endpoint': '/api/v1/grades/',
                'method': 'GET',
                'description': 'Retrieve grade information'
            },
            {
                'endpoint': '/api/v1/fees/',
                'method': 'GET',
                'description': 'Retrieve fee information and payment status',
                'parameters': {
                    'student_id': 'integer - Filter by student ID',
                    'status': 'string - Filter by payment status (paid/unpaid/partial)',
                    'fee_type': 'string - Filter by fee type (tuition/transport/library)',
                    'term': 'string - Filter by academic term',
                    'year': 'integer - Filter by academic year'
                }
            },
            {
                'endpoint': '/api/v1/fees/payments/',
                'method': 'POST',
                'description': 'Process fee payments'
            },
            {
                'endpoint': '/api/v1/academics/classes/',
                'method': 'GET',
                'description': 'Retrieve class and section information',
                'parameters': {
                    'is_active': 'boolean - Filter by active status',
                    'order': 'string - Sort by order field'
                }
            },
            {
                'endpoint': '/api/v1/academics/subjects/',
                'method': 'GET',
                'description': 'Retrieve subject information and teacher assignments',
                'parameters': {
                    'class_id': 'integer - Filter by class ID',
                    'teacher_id': 'integer - Filter by teacher ID'
                }
            },
            {
                'endpoint': '/api/v1/timetable/',
                'method': 'GET',
                'description': 'Retrieve class timetables'
            },
            {
                'endpoint': '/api/v1/notifications/',
                'method': 'POST',
                'description': 'Send notifications to users'
            },
            {
                'endpoint': '/api/v1/reports/performance/',
                'method': 'GET',
                'description': 'Generate performance reports'
            },
            {
                'endpoint': '/api/v1/auth/login/',
                'method': 'POST',
                'description': 'User authentication and token generation',
                'request_body': {
                    'email': 'string - User email address (required)',
                    'password': 'string - User password (required)',
                    'school_slug': 'string - School subdomain/identifier (required)'
                }
            },
            {
                'endpoint': '/api/v1/auth/refresh/',
                'method': 'POST',
                'description': 'Refresh JWT token'
            },
            {
                'endpoint': '/api/v1/schools/profile/',
                'method': 'GET',
                'description': 'Retrieve school profile information'
            },
            {
                'endpoint': '/api/v1/library/books/',
                'method': 'GET',
                'description': 'Retrieve library book catalog and availability',
                'parameters': {
                    'search': 'string - Search by title or author',
                    'category': 'string - Filter by category',
                    'is_available': 'boolean - Filter by availability'
                }
            },
            {
                'endpoint': '/api/v1/transport/routes/',
                'method': 'GET',
                'description': 'Retrieve transport routes and vehicle assignments',
                'parameters': {
                    'vehicle_id': 'integer - Filter by vehicle ID',
                    'is_active': 'boolean - Filter by active routes'
                }
            }
        ]
        
        # Contact Information
        context['contact_info'] = {
            'company': {
                'name': 'Timesten Technologies',
                'description': 'Leading provider of innovative educational technology solutions in Kenya',
                'mission': 'To transform education through technology, making quality education accessible and manageable for all institutions.'
            },
            'emails': {
                'general': 'clasyo@timestentechnologies.co.ke',
                'info': 'info@timestentechnologies.co.ke',
                'sales': 'sales@timestentechnologies.co.ke',
                'customer': 'customer@timestentechnologies.co.ke',
                'support': 'support@timestentechnologies.co.ke'
            },
            'phones': {
                'kenya': '+254 (718)883 983',
                'international': '+1 (458) 320-3224'
            },
            'address': {
                'location': 'Nairobi, Kenya',
                'description': 'Headquarters in Nairobi with regional presence across East Africa'
            },
            'business_hours': {
                'days': 'Monday - Friday',
                'hours': '8:00 AM - 6:00 PM EAT',
                'support': '24/7 Emergency Support Available'
            }
        }
        
        # Technical Documentation
        context['technical_docs'] = {
            'architecture': {
                'title': 'System Architecture',
                'overview': 'Clasyo is built on Django framework with a multi-tenant architecture designed specifically for Kenyan educational institutions',
                'components': [
                    {
                        'name': 'Backend Framework',
                        'technology': 'Django 4.2.7 with Django REST Framework',
                        'description': 'Robust Python-based web framework with comprehensive security features and REST API capabilities'
                    },
                    {
                        'name': 'Frontend',
                        'technology': 'Bootstrap 5 + Django Templates',
                        'description': 'Responsive web interface with server-side rendering using Django templates and Bootstrap CSS framework'
                    },
                    {
                        'name': 'Database',
                        'technology': 'MySQL (Production) / SQLite (Development)',
                        'description': 'MySQL for production environments with SQLite for development and testing'
                    },
                    {
                        'name': 'Authentication',
                        'technology': 'Django Allauth + Custom Impersonation',
                        'description': 'Secure authentication system with social login support and admin impersonation capabilities'
                    },
                    {
                        'name': 'Background Tasks',
                        'technology': 'Celery + Redis',
                        'description': 'Asynchronous task processing for background operations like email sending and report generation'
                    },
                    {
                        'name': 'Real-time Communication',
                        'technology': 'Django Channels + WebSocket',
                        'description': 'Real-time chat and notifications using WebSocket connections'
                    },
                    {
                        'name': 'File Storage',
                        'technology': 'Django File System + Pillow',
                        'description': 'Local file storage with image processing capabilities using Pillow library'
                    }
                ]
            },
            'security': {
                'title': 'Security & Compliance',
                'features': [
                    'Django built-in CSRF protection',
                    'Role-based access control (RBAC)',
                    'SQL injection prevention',
                    'XSS protection',
                    'Secure password hashing',
                    'Session security',
                    'File upload validation',
                    'API rate limiting',
                    'Multi-tenant data isolation'
                ],
                'compliance': [
                    'Kenyan Data Protection Act compliance',
                    'GDPR-ready architecture',
                    'Secure data encryption',
                    'Audit logging and monitoring'
                ]
            },
            'deployment': {
                'title': 'Deployment Options',
                'options': [
                    {
                        'name': 'Shared Hosting',
                        'description': 'Affordable shared hosting for small schools',
                        'benefits': ['Low cost', 'Easy setup', 'Basic support']
                    },
                    {
                        'name': 'VPS/Dedicated Server',
                        'description': 'Virtual Private Server or dedicated hosting',
                        'benefits': ['Better performance', 'Full control', 'Custom configuration']
                    },
                    {
                        'name': 'Cloud Deployment',
                        'description': 'Deploy on AWS, Azure, or similar cloud platforms',
                        'benefits': ['Scalable infrastructure', 'High availability', 'Global reach']
                    }
                ]
            }
        }
        
        # Implementation Guide
        context['implementation'] = {
            'phases': [
                {
                    'phase': 'Phase 1: Discovery & Planning',
                    'duration': '1-2 weeks',
                    'activities': [
                        'Requirements gathering',
                        'System configuration planning',
                        'Data migration strategy',
                        'User training planning',
                        'Go-live date setting'
                    ]
                },
                {
                    'phase': 'Phase 2: Setup & Configuration',
                    'duration': '2-3 weeks',
                    'activities': [
                        'System setup and configuration',
                        'User account creation',
                        'Academic structure setup',
                        'Fee structure configuration',
                        'Integration setup'
                    ]
                },
                {
                    'phase': 'Phase 3: Data Migration',
                    'duration': '1-2 weeks',
                    'activities': [
                        'Student data import',
                        'Staff data import',
                        'Academic data migration',
                        'Financial data migration',
                        'Data validation and cleanup'
                    ]
                },
                {
                    'phase': 'Phase 4: Training & Testing',
                    'duration': '1-2 weeks',
                    'activities': [
                        'Administrator training',
                        'Teacher training',
                        'Parent and student orientation',
                        'System testing',
                        'User acceptance testing'
                    ]
                },
                {
                    'phase': 'Phase 5: Go-Live & Support',
                    'duration': 'Ongoing',
                    'activities': [
                        'System go-live',
                        'Hypercare support',
                        'User support',
                        'System optimization',
                        'Continuous improvement'
                    ]
                }
            ],
            'checklist': {
                'pre_implementation': [
                    'Define implementation team',
                    'Set clear objectives and KPIs',
                    'Prepare data for migration',
                    'Establish communication plan',
                    'Schedule training sessions'
                ],
                'during_implementation': [
                    'Regular progress meetings',
                    'Data validation checks',
                    'User feedback collection',
                    'Issue tracking and resolution',
                    'Documentation updates'
                ],
                'post_implementation': [
                    'Performance monitoring',
                    'User satisfaction surveys',
                    'System optimization',
                    'Additional training if needed',
                    'Continuous improvement planning'
                ]
            }
        }
        
        # Pricing and Plans
        context['pricing_info'] = {
            'plans': [
                {
                    'name': 'Basic',
                    'ideal_for': 'Small schools (up to 100 students)',
                    'features': [
                        'Core school management',
                        'Student information system',
                        'Basic reporting',
                        'Parent portal',
                        'Email support'
                    ],
                    'pricing': 'Starting from KES 10,000/month'
                },
                {
                    'name': 'Professional',
                    'ideal_for': 'Medium schools (100-500 students)',
                    'features': [
                        'All Basic features',
                        'Advanced reporting',
                        'Fee management',
                        'Library management',
                        'Mobile app',
                        'Priority support'
                    ],
                    'pricing': 'Starting from KES 25,000/month'
                },
                {
                    'name': 'Enterprise',
                    'ideal_for': 'Large schools (500+ students)',
                    'features': [
                        'All Professional features',
                        'Transport management',
                        'Hostel management',
                        'HR & payroll',
                        'Custom integrations',
                        'Dedicated support',
                        'Custom training'
                    ],
                    'pricing': 'Custom pricing'
                }
            ],
            'additional_services': [
                {
                    'service': 'Data Migration',
                    'description': 'Professional data migration from existing systems',
                    'pricing': 'One-time fee based on complexity'
                },
                {
                    'service': 'Custom Training',
                    'description': 'On-site training for staff and administrators',
                    'pricing': 'Based on training scope and duration'
                },
                {
                    'service': 'Custom Development',
                    'description': 'Custom features and integrations',
                    'pricing': 'Based on requirements'
                },
                {
                    'service': 'API Access',
                    'description': 'Full API access for third-party integrations',
                    'pricing': 'Available with Enterprise plan'
                }
            ]
        }
        
        return context


def generate_pdf_documentation(request):
    """Generate PDF version of the documentation using ReportLab"""
    try:
        # Get the context data
        context = DocumentationView().get_context_data()
        
        # Create a buffer for the PDF
        buffer = BytesIO()
        
        # Create the PDF document
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )
        
        # Get styles
        styles = getSampleStyleSheet()
        
        # Custom styles with brand colors
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            textColor=colors.HexColor('#1E3A5F'),
            alignment=1  # Center
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=18,
            spaceAfter=20,
            spaceBefore=30,
            textColor=colors.HexColor('#1E3A5F')
        )
        
        subheading_style = ParagraphStyle(
            'CustomSubHeading',
            parent=styles['Heading3'],
            fontSize=14,
            spaceAfter=12,
            spaceBefore=20,
            textColor=colors.HexColor('#1E3A5F')
        )
        
        body_style = ParagraphStyle(
            'CustomBody',
            parent=styles['Normal'],
            fontSize=11,
            spaceAfter=12,
            textColor=colors.black
        )
        
        # Build the story (content)
        story = []
        
        # Title
        story.append(Paragraph("Clasyo Documentation", title_style))
        story.append(Spacer(1, 12))
        story.append(Paragraph("Comprehensive Guide for School Management System", body_style))
        story.append(Spacer(1, 20))
        
        # Getting Started Section
        story.append(Paragraph("Getting Started", heading_style))
        story.append(Paragraph("System Requirements", subheading_style))
        
        requirements = [
            "Modern web browser (Chrome, Firefox, Safari, Edge)",
            "Stable internet connection",
            "Minimum screen resolution: 1024x768",
            "JavaScript enabled",
            "Cookies enabled for session management"
        ]
        
        for req in requirements:
            story.append(Paragraph(f"• {req}", body_style))
        
        story.append(Spacer(1, 20))
        story.append(Paragraph("Account Setup", subheading_style))
        
        setup_steps = [
            "1. <b>Register Your School</b> - Visit the registration page and provide your school details including name, contact information, and administrator credentials.",
            "2. <b>Configure School Profile</b> - Complete your school profile with address, academic calendar, and grading system preferences.",
            "3. <b>Set Up Academic Structure</b> - Create academic years, terms, classes, and subjects according to your school's curriculum.",
            "4. <b>Add Users</b> - Create accounts for teachers, students, and parents with appropriate roles and permissions."
        ]
        
        for step in setup_steps:
            story.append(Paragraph(step, body_style))
            story.append(Spacer(1, 12))
        
        # System Modules Section
        story.append(Paragraph("System Modules", heading_style))
        
        for feature in context['core_features']:
            story.append(Paragraph(feature['title'], subheading_style))
            story.append(Paragraph(feature['description'], body_style))
            
            # Add key features based on module type
            if feature['title'] == 'Academic Management':
                key_features = [
                    "Academic year and term management",
                    "Class and section creation",
                    "Subject allocation",
                    "Timetable generation",
                    "CBC competency tracking"
                ]
            elif feature['title'] == 'Student Information System':
                key_features = [
                    "Student registration and enrollment",
                    "Attendance tracking",
                    "Academic performance records",
                    "Disciplinary records",
                    "Medical information"
                ]
            elif feature['title'] == 'Examination System':
                key_features = [
                    "Exam creation and scheduling",
                    "Grade entry and calculation",
                    "Report card generation",
                    "Transcript management",
                    "Performance analytics"
                ]
            elif feature['title'] == 'Fee Management':
                key_features = [
                    "Fee structure setup",
                    "Invoice generation",
                    "Payment tracking",
                    "M-Pesa integration",
                    "Financial reporting"
                ]
            elif feature['title'] == 'Library Management':
                key_features = [
                    "Book catalog management",
                    "Issue and return tracking",
                    "Fine calculation",
                    "Inventory management",
                    "Digital library support"
                ]
            elif feature['title'] == 'Communication Tools':
                key_features = [
                    "Messaging system",
                    "Notice board",
                    "Parent-teacher communication",
                    "SMS notifications",
                    "Email integration"
                ]
            else:
                key_features = [
                    "Comprehensive management tools",
                    "Real-time data synchronization",
                    "Advanced reporting capabilities",
                    "Mobile-responsive interface",
                    "Secure data storage"
                ]
            
            for kf in key_features:
                story.append(Paragraph(f"• {kf}", body_style))
            
            story.append(Spacer(1, 20))
        
        # User Guides Section
        story.append(Paragraph("User Guides", heading_style))
        
        for guide in context['user_guides']:
            story.append(Paragraph(guide['role'], subheading_style))
            story.append(Paragraph(guide['description'], body_style))
            
            for section in guide['sections']:
                story.append(Paragraph(f"• {section}", body_style))
            
            story.append(Spacer(1, 15))
        
        # API Documentation Section
        story.append(Paragraph("API Documentation", heading_style))
        story.append(Paragraph("Authentication", subheading_style))
        story.append(Paragraph("All API endpoints require authentication using JWT tokens. Include the token in the Authorization header:", body_style))
        story.append(Paragraph("Authorization: Bearer &lt;your_jwt_token&gt;", body_style))
        story.append(Spacer(1, 20))
        
        story.append(Paragraph("Base URL", subheading_style))
        story.append(Paragraph("https://api.clasyo.com/v1", body_style))
        story.append(Spacer(1, 20))
        
        story.append(Paragraph("Available Endpoints", subheading_style))
        
        # Create table for API endpoints
        api_data = [["Method", "Endpoint", "Description"]]
        for endpoint in context['api_endpoints']:
            api_data.append([endpoint['method'], endpoint['endpoint'], endpoint['description']])
        
        api_table = Table(api_data, colWidths=[1.5*inch, 3*inch, 3*inch])
        api_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4DD0E1')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#1E3A5F')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F8F9FA')),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(api_table)
        story.append(Spacer(1, 20))
        
        # Payment Gateways Section
        story.append(Paragraph("Payment Gateway Configuration", heading_style))
        story.append(Paragraph("Supported Payment Methods", subheading_style))
        
        payment_methods = [
            "<b>M-Pesa STK Push</b> - Automatic payment prompts sent to parent phones",
            "<b>M-Pesa Manual Paybill</b> - Parents manually pay using paybill details",
            "<b>PayPal</b> - International payment processing",
            "<b>Bank Transfer</b> - Direct bank deposits"
        ]
        
        for pm in payment_methods:
            story.append(Paragraph(f"• {pm}", body_style))
        
        story.append(Spacer(1, 20))
        
        # Integration Guide Section
        story.append(Paragraph("Integration Guide", heading_style))
        story.append(Paragraph("Webhook Integration", subheading_style))
        
        webhook_events = [
            "student.enrolled - New student registration",
            "fee.paid - Fee payment received",
            "attendance.marked - Attendance recorded",
            "grade.posted - Grades posted",
            "user.created - New user account created"
        ]
        
        for event in webhook_events:
            story.append(Paragraph(f"• {event}", body_style))
        
        story.append(Spacer(1, 20))
        
        # Troubleshooting Section
        story.append(Paragraph("Troubleshooting", heading_style))
        story.append(Paragraph("Common Issues", subheading_style))
        
        issues = [
            "<b>Unable to Login</b> - Check your email and password. Use the 'Forgot Password' link to reset if needed.",
            "<b>Payment Not Reflecting</b> - Wait 5-10 minutes for M-Pesa processing. Check payment confirmation SMS.",
            "<b>Reports Not Generating</b> - Ensure you have the required permissions. Check that data exists for the selected period.",
            "<b>Slow Performance</b> - Clear browser cache, check internet connection, try a different browser."
        ]
        
        for issue in issues:
            story.append(Paragraph(f"• {issue}", body_style))
        
        story.append(Spacer(1, 20))
        
        # Support Information
        story.append(Paragraph("Support", heading_style))
        support_info = [
            "<b>Email:</b> support@clasyo.com",
            "<b>Phone:</b> +254 700 123 456",
            "<b>Hours:</b> Monday - Friday, 8:00 AM - 6:00 PM EAT"
        ]
        
        for info in support_info:
            story.append(Paragraph(info, body_style))
        
        # Footer
        story.append(Spacer(1, 30))
        story.append(Paragraph("© 2025 Clasyo by Timesten Technologies. All rights reserved.", body_style))
        
        # Build PDF
        doc.build(story)
        
        # Get PDF value
        pdf_value = buffer.getvalue()
        buffer.close()
        
        # Create HTTP response with PDF
        response = HttpResponse(pdf_value, content_type='application/pdf')
        response['Content-Disposition'] = 'filename="clasyo_documentation.pdf"'
        return response
        
    except ImportError as e:
        # Fallback to HTML-based PDF if ReportLab is not available
        return generate_html_fallback_pdf(request, str(e))
    except Exception as e:
        return HttpResponse(f'Error generating PDF: {str(e)}', status=500)


def generate_html_fallback_pdf(request, error_msg):
    """Fallback method using HTML to PDF conversion"""
    try:
        # Get the context data
        context = DocumentationView().get_context_data()
        
        # Render the HTML template
        html_string = render_to_string('frontend/documentation_pdf_simple.html', context)
        
        # Create a simple HTML response that can be saved as PDF from browser
        response = HttpResponse(html_string, content_type='text/html')
        response['Content-Disposition'] = 'filename="clasyo_documentation.html"'
        response['X-PDF-Warning'] = f'PDF generation error: {error_msg}. Please save this HTML file and convert to PDF using your browser.'
        return response
        
    except Exception as e:
        return HttpResponse(f'Error generating documentation: {str(e)}', status=500)


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
