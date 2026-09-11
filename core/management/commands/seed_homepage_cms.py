from django.core.management.base import BaseCommand
from frontend.models import HeroContent, ProcessStep, FeatureItem, ParallaxSection


class Command(BaseCommand):
    help = "Seed initial CMS data for Homepage (Hero, How It Works Stepper, Features, Parallax)"

    def handle(self, *args, **options):
        # 1. Hero Content
        hero, created = HeroContent.objects.update_or_create(
            id=1,
            defaults={
                'title_prefix': 'Transform Your',
                'typing_texts': "School Management\nAcademic Operations\nLearning Experiences\nCBC & TVET Institutions",
                'subtitle': 'Complete cloud-based solution for modern education management. Streamline operations and enhance learning experiences.',
                'primary_btn_text': 'Start Free Trial',
                'primary_btn_url': '#registerModal',
                'secondary_btn_text': 'Sign In',
                'secondary_btn_url': '#loginModal',
                'bg_type': 'color',
                'bg_gradient': '',
                'bg_color': '#0f172a',
                'overlay_opacity': 0.85,
                'is_active': True,
            }
        )
        self.stdout.write(self.style.SUCCESS("Updated default HeroContent with solid color"))

        # 2. Process / How It Works Steps (matching the interactive stepper)
        steps_data = [
            {
                'step_number': 1,
                'phase_tag': 'PHASE 1',
                'title': 'School Setup & CBC Configuration',
                'subtitle': 'Fast digital onboarding for your institution',
                'description': 'Configure your school profile, grading structures, Kenyan CBC learning areas, primary/secondary streams, TVET curricula, and academic sessions in minutes.',
                'icon': 'fas fa-school',
                'accent_color': '#d97706',
                'order': 1,
            },
            {
                'step_number': 2,
                'phase_tag': 'PHASE 2',
                'title': 'Student & Staff Onboarding',
                'subtitle': 'Bulk import with biometric & Guardian integration',
                'description': 'Seamlessly import student records, assign unique admission IDs, configure guardian contacts for real-time SMS alerts, and onboard teachers with granular permission roles.',
                'icon': 'fas fa-user-graduate',
                'accent_color': '#d97706',
                'order': 2,
            },
            {
                'step_number': 3,
                'phase_tag': 'PHASE 3',
                'title': 'Academics, Exams & CBC Assessment',
                'subtitle': 'Automated report cards & rubrics',
                'description': 'Generate dynamic timetables, digital lesson plans, termly exams, CBC formative/summative assessment rubrics, and instant branded PDF report cards.',
                'icon': 'fas fa-file-invoice',
                'accent_color': '#d97706',
                'order': 3,
            },
            {
                'step_number': 4,
                'phase_tag': 'PHASE 4',
                'title': 'Fees, Accounting & Inventory Control',
                'subtitle': 'Double-entry ledger with M-Pesa STK push',
                'description': 'Automate school fee structures, collect payments via direct M-Pesa STK push / Paybill integration, track double-entry Chart of Accounts, General Ledger, and inventory stock.',
                'icon': 'fas fa-coins',
                'accent_color': '#d97706',
                'order': 4,
            },
            {
                'step_number': 5,
                'phase_tag': 'PHASE 5',
                'title': 'AI Insights & Parent Communication',
                'subtitle': 'Predictive analytics & 24/7 intelligent assistant',
                'description': 'Empower school leadership with AI-driven fee collection predictions, student performance trends, automated daily attendance SMS, and real-time parent portals.',
                'icon': 'fas fa-robot',
                'accent_color': '#d97706',
                'order': 5,
            },
        ]

        for s in steps_data:
            step, s_created = ProcessStep.objects.update_or_create(
                step_number=s['step_number'],
                defaults=s
            )
            self.stdout.write(self.style.SUCCESS(f"Saved Step {step.step_number}: {step.title}"))

        # 3. Features (All 16 Comprehensive Modules)
        features_data = [
            {'title': 'Student Information & CBC', 'description': 'Complete student profiles, UPI/NEMIS tracking, admissions, and digital archive', 'icon': 'fas fa-user-graduate', 'order': 1},
            {'title': 'Academics & Timetables', 'description': 'Class streams, subject allocations, routine scheduling, and lesson planning', 'icon': 'fas fa-chalkboard-teacher', 'order': 2},
            {'title': 'Fee Management & Billing', 'description': 'Flexible termly voteheads, student invoices, waivers, and real-time balances', 'icon': 'fas fa-dollar-sign', 'order': 3},
            {'title': 'M-Pesa STK & Paybill', 'description': 'Direct Daraja STK Push, Paybill C2B automated receipting & reconciliation', 'icon': 'fas fa-mobile-alt', 'order': 4},
            {'title': 'Examinations & Grading', 'description': 'Termly exams, automatic grading curves, and instant PDF report cards', 'icon': 'fas fa-file-alt', 'order': 5},
            {'title': 'CBC Assessment Rubrics', 'description': 'Strand & sub-strand formative/summative rubrics with performance levels', 'icon': 'fas fa-clipboard-check', 'order': 6},
            {'title': 'Double-Entry Accounting', 'description': 'Chart of Accounts, General Ledger, Cashbook, Trial Balance, and Expenses', 'icon': 'fas fa-calculator', 'order': 7},
            {'title': 'Inventory & Procurement', 'description': 'Store stock tracking, supplier management, purchase orders & distribution', 'icon': 'fas fa-boxes', 'order': 8},
            {'title': 'Canteen POS & Meals', 'description': 'Cashless student POS terminal, meal allowance tracking & sales reports', 'icon': 'fas fa-utensils', 'order': 9},
            {'title': 'Transport & Logistics', 'description': 'Fleet management, bus route planning, pickup zones, and driver assignments', 'icon': 'fas fa-bus', 'order': 10},
            {'title': 'Hostels & Dormitories', 'description': 'Boarding facility allocation, room capacity tracking, and student bed logs', 'icon': 'fas fa-bed', 'order': 11},
            {'title': 'Digital Library & Barcodes', 'description': 'Book catalogue, ISBN/barcode scanning, issue & return records with overdue alerts', 'icon': 'fas fa-book', 'order': 12},
            {'title': 'Staff HR & Payroll', 'description': 'Staff profiles, role delegations, leave approvals, and automated payslip generation', 'icon': 'fas fa-users-cog', 'order': 13},
            {'title': 'Attendance & SMS Alerts', 'description': 'Daily student roll-call with automated instant SMS notifications to parents', 'icon': 'fas fa-sms', 'order': 14},
            {'title': 'Online CBT & Homework', 'description': 'Digital homework uploads, timed online computer-based examinations & results', 'icon': 'fas fa-laptop-code', 'order': 15},
            {'title': 'AI Assistant & Analytics', 'description': 'Predictive fee collection forecasts, student performance analysis & smart queries', 'icon': 'fas fa-robot', 'order': 16},
        ]

        for f in features_data:
            feat, f_created = FeatureItem.objects.update_or_create(
                title=f['title'],
                defaults=f
            )
            self.stdout.write(self.style.SUCCESS(f"Saved Feature: {feat.title}"))

        # 4. Parallax Sections (Solid colors)
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
                'bg_color': '#091528',
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
            self.stdout.write(self.style.SUCCESS(f"Saved Parallax Section: {parallax.title}"))

        self.stdout.write(self.style.SUCCESS("All CMS content successfully seeded!"))
