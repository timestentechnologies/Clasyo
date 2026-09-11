from django.core.management.base import BaseCommand
from frontend.models import HeroContent, ProcessStep, FeatureItem, ParallaxSection


class Command(BaseCommand):
    help = "Seed initial CMS data for Homepage (Hero, How It Works Stepper, Features, Parallax)"

    def handle(self, *args, **options):
        # 1. Hero Content
        hero, created = HeroContent.objects.get_or_create(
            id=1,
            defaults={
                'title_prefix': 'Transform Your',
                'typing_texts': "School Management\nAcademic Operations\nLearning Experiences\nCBC & TVET Institutions",
                'subtitle': 'Complete cloud-based solution for modern education management. Streamline operations and enhance learning experiences.',
                'primary_btn_text': 'Start Free Trial',
                'primary_btn_url': '#registerModal',
                'secondary_btn_text': 'Sign In',
                'secondary_btn_url': '#loginModal',
                'bg_type': 'gradient',
                'bg_gradient': 'linear-gradient(135deg, #0f172a 0%, #1e3a5f 50%, #164e63 100%)',
                'bg_color': '#0f172a',
                'overlay_opacity': 0.85,
                'is_active': True,
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS("Created default HeroContent"))

        # 2. Process / How It Works Steps (matching the interactive stepper)
        steps_data = [
            {
                'step_number': 1,
                'phase_tag': 'PHASE 1',
                'title': 'School Setup & CBC Configuration',
                'subtitle': 'Fast digital onboarding for your institution',
                'description': 'Configure your school profile, grading structures, Kenyan CBC learning areas, primary/secondary streams, TVET curricula, and academic sessions in minutes.',
                'icon': 'fas fa-school',
                'accent_color': '#06b6d4',
                'order': 1,
            },
            {
                'step_number': 2,
                'phase_tag': 'PHASE 2',
                'title': 'Student & Staff Onboarding',
                'subtitle': 'Bulk import with biometric & Guardian integration',
                'description': 'Seamlessly import student records, assign unique admission IDs, configure guardian contacts for real-time SMS alerts, and onboard teachers with granular permission roles.',
                'icon': 'fas fa-user-graduate',
                'accent_color': '#f59e0b',
                'order': 2,
            },
            {
                'step_number': 3,
                'phase_tag': 'PHASE 3',
                'title': 'Academics, Exams & CBC Assessment',
                'subtitle': 'Automated report cards & rubrics',
                'description': 'Generate dynamic timetables, digital lesson plans, termly exams, CBC formative/summative assessment rubrics, and instant branded PDF report cards.',
                'icon': 'fas fa-file-invoice',
                'accent_color': '#10b981',
                'order': 3,
            },
            {
                'step_number': 4,
                'phase_tag': 'PHASE 4',
                'title': 'Fees, Accounting & Inventory Control',
                'subtitle': 'Double-entry ledger with M-Pesa STK push',
                'description': 'Automate school fee structures, collect payments via direct M-Pesa STK push / Paybill integration, track double-entry Chart of Accounts, General Ledger, and inventory stock.',
                'icon': 'fas fa-coins',
                'accent_color': '#8b5cf6',
                'order': 4,
            },
            {
                'step_number': 5,
                'phase_tag': 'PHASE 5',
                'title': 'AI Insights & Parent Communication',
                'subtitle': 'Predictive analytics & 24/7 intelligent assistant',
                'description': 'Empower school leadership with AI-driven fee collection predictions, student performance trends, automated daily attendance SMS, and real-time parent portals.',
                'icon': 'fas fa-robot',
                'accent_color': '#ec4899',
                'order': 5,
            },
        ]

        for s in steps_data:
            step, s_created = ProcessStep.objects.update_or_create(
                step_number=s['step_number'],
                defaults=s
            )
            if s_created:
                self.stdout.write(self.style.SUCCESS(f"Created Step {step.step_number}: {step.title}"))

        # 3. Features
        features_data = [
            {'title': 'Student Management', 'description': 'Complete student profiles, admissions, and academic tracking system', 'icon': 'fas fa-user-graduate', 'order': 1},
            {'title': 'Academic Management', 'description': 'Classes, subjects, timetables, and digital study materials', 'icon': 'fas fa-chalkboard-teacher', 'order': 2},
            {'title': 'Fee Management', 'description': 'Flexible fee structure with M-Pesa STK push, receipts and real-time balances', 'icon': 'fas fa-dollar-sign', 'order': 3},
            {'title': 'Examinations & CBC', 'description': 'Complete exam system with online testing, automated grading & CBC rubrics', 'icon': 'fas fa-file-alt', 'order': 4},
            {'title': 'Attendance & SMS', 'description': 'Daily attendance tracking with real-time SMS alerts to parents', 'icon': 'fas fa-calendar-check', 'order': 5},
            {'title': 'Communication', 'description': 'Real-time multi-channel chat, SMS, and email notification system', 'icon': 'fas fa-comments', 'order': 6},
            {'title': 'Digital Library', 'description': 'Complete digital library catalog, book issuance and barcode tracking', 'icon': 'fas fa-book', 'order': 7},
            {'title': 'Transport & Fleet', 'description': 'Route management, student bus allocation and GPS tracking', 'icon': 'fas fa-bus', 'order': 8},
            {'title': 'AI Assistant', 'description': 'Ask natural-language questions and get instant insights across all modules', 'icon': 'fas fa-robot', 'order': 9},
            {'title': 'Finance & Ledger', 'description': 'Double-entry accounting with Chart of Accounts, General Ledger and Trial Balance', 'icon': 'fas fa-coins', 'order': 10},
            {'title': 'Inventory & Stock', 'description': 'Track items, suppliers, purchase orders, issues and stock levels', 'icon': 'fas fa-boxes', 'order': 11},
            {'title': 'HR & Payroll', 'description': 'Staff records, automated payroll processing, payslips and leave management', 'icon': 'fas fa-briefcase', 'order': 12},
        ]

        for f in features_data:
            feat, f_created = FeatureItem.objects.update_or_create(
                title=f['title'],
                defaults=f
            )
            if f_created:
                self.stdout.write(self.style.SUCCESS(f"Created Feature: {feat.title}"))

        # 4. Parallax Sections
        parallax_data = [
            {
                'badge_text': 'NEXT-GEN EDUCATION MANAGEMENT',
                'title': 'Digitize Your School with Kenya\'s Most Comprehensive Cloud SaaS',
                'subtitle': 'Over 99.9% uptime, bank-grade data security, automated M-Pesa reconciliation, and Kenyan CBC compliance out of the box.',
                'content': 'Clasyo empowers school administrators, teachers, parents, and students with unified digital workflows. Say goodbye to manual paperwork and disconnected spreadsheets.',
                'primary_btn_text': 'Get Started Free',
                'primary_btn_url': '#registerModal',
                'secondary_btn_text': 'View Pricing Plans',
                'secondary_btn_url': '/pricing/',
                'bg_color': '#091528',
                'overlay_opacity': 0.80,
                'scroll_effect': 'fixed_bg',
                'order': 1,
                'is_active': True,
            },
            {
                'badge_text': 'AI-POWERED SCHOOL INTELLIGENCE',
                'title': 'Experience the Future of AI-Driven School Administration',
                'subtitle': 'Ask questions, predict fee collection bottlenecks, automate exam grading, and communicate instantly with parents.',
                'content': 'Transform data into actionable insights with our built-in AI assistant trained specifically for Kenyan educational standards.',
                'primary_btn_text': 'Schedule a Demo',
                'primary_btn_url': '/contact/',
                'secondary_btn_text': 'Learn More',
                'secondary_btn_url': '/about/',
                'bg_color': '#06202a',
                'overlay_opacity': 0.82,
                'scroll_effect': 'zoom_in',
                'order': 2,
                'is_active': True,
            },
        ]

        for p in parallax_data:
            parallax, p_created = ParallaxSection.objects.update_or_create(
                title=p['title'],
                defaults=p
            )
            if p_created:
                self.stdout.write(self.style.SUCCESS(f"Created Parallax Section: {parallax.title}"))

        self.stdout.write(self.style.SUCCESS("All CMS content successfully seeded!"))
