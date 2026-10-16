from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, Http404, HttpResponse
from django.db.models import Q
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .models import Student
from .models import StudentSubject
from accounts.models import User
from core.models import SystemSetting
from core.utils import generate_email, get_school_slug_from_request
from core.utils import get_current_school
from django.db import transaction
import io
import csv
import json
import pandas as pd
from openpyxl import Workbook, load_workbook
from openpyxl.styles import PatternFill, Font, Alignment
from openpyxl.comments import Comment
from datetime import datetime


def get_student_subjects_metadata(school, active_year=None):
    from academics.models import Class, Subject, AssignedSubject
    from core.models import AcademicYear

    if active_year is None:
        ay_qs = AcademicYear.objects.filter(is_active=True)
        if school:
            ay_qs = ay_qs.filter(school=school)
        active_year = ay_qs.first()

    classes_qs = Class.objects.filter(is_active=True)
    subjects_qs = Subject.objects.filter(is_active=True).order_by('name')
    if school:
        classes_qs = classes_qs.filter(school=school)
        subjects_qs = subjects_qs.filter(school=school)
    classes_qs = classes_qs.prefetch_related('sections')

    assigned_qs = AssignedSubject.objects.filter(is_active=True)
    if school:
        assigned_qs = assigned_qs.filter(class_name__school=school, subject__school=school)
    if active_year:
        assigned_qs = assigned_qs.filter(academic_year=active_year)
    assigned_qs = assigned_qs.select_related('subject')

    class_subjects_dict = {}
    for asub in assigned_qs:
        cid = asub.class_name_id
        sub_map = class_subjects_dict.setdefault(cid, {})
        sub_info = sub_map.setdefault(asub.subject_id, {
            'id': asub.subject_id,
            'name': asub.subject.name,
            'code': asub.subject.code or '',
            'type': asub.subject.get_subject_type_display() if hasattr(asub.subject, 'get_subject_type_display') else str(asub.subject.subject_type),
            'is_compulsory': asub.is_compulsory,
            'all_sections': False,
            'section_ids': []
        })
        if asub.section_id:
            if asub.section_id not in sub_info['section_ids']:
                sub_info['section_ids'].append(asub.section_id)
        else:
            sub_info['all_sections'] = True

    # Fallback if no assigned subjects found in active_year
    if not class_subjects_dict:
        fallback_qs = AssignedSubject.objects.filter(is_active=True)
        if school:
            fallback_qs = fallback_qs.filter(class_name__school=school, subject__school=school)
        fallback_qs = fallback_qs.select_related('subject')
        for asub in fallback_qs:
            cid = asub.class_name_id
            sub_map = class_subjects_dict.setdefault(cid, {})
            sub_info = sub_map.setdefault(asub.subject_id, {
                'id': asub.subject_id,
                'name': asub.subject.name,
                'code': asub.subject.code or '',
                'type': asub.subject.get_subject_type_display() if hasattr(asub.subject, 'get_subject_type_display') else str(asub.subject.subject_type),
                'is_compulsory': asub.is_compulsory,
                'all_sections': False,
                'section_ids': []
            })
            if asub.section_id:
                if asub.section_id not in sub_info['section_ids']:
                    sub_info['section_ids'].append(asub.section_id)
            else:
                sub_info['all_sections'] = True

    classes_meta = []
    for c in classes_qs:
        c_sections = [{'id': s.id, 'name': s.name} for s in c.sections.filter(is_active=True)]
        assigned_subs = list(class_subjects_dict.get(c.id, {}).values())
        classes_meta.append({
            'id': c.id,
            'name': c.name,
            'sections': c_sections,
            'subjects': assigned_subs
        })

    all_subjects_meta = [
        {
            'id': s.id, 
            'name': s.name, 
            'code': s.code or '',
            'type': s.get_subject_type_display() if hasattr(s, 'get_subject_type_display') else str(s.subject_type),
            'is_compulsory': False
        } 
        for s in subjects_qs
    ]

    return classes_meta, all_subjects_meta


class StudentListView(LoginRequiredMixin, ListView):
    model = Student
    template_name = 'students/list.html'
    context_object_name = 'students'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset()
        school = get_current_school(self.request)
        status = self.request.GET.get('status', '').strip().lower()
        cohort = self.request.GET.get('cohort', '').strip()
        class_id = self.request.GET.get('class_id', '').strip() or self.request.GET.get('class_filter', '').strip()
        search_query = self.request.GET.get('search', '').strip() or self.request.GET.get('q', '').strip()

        if school:
            base = queryset.filter(
                Q(school=school) | Q(current_class__school=school) | Q(user__school=school) | Q(parent_user__school=school) | Q(created_by__school=school)
            ).distinct()
        else:
            base = queryset

        # Enrollment & Active status filtering
        if status in ('enrolled', 'pending', 'transferred', 'withdrawn', 'graduated'):
            base = base.filter(enrollment_status=status)
        elif status == 'active':
            base = base.filter(is_active=True)
        elif status == 'inactive':
            base = base.filter(is_active=False)

        # Intake cohort filtering
        if cohort:
            base = base.filter(Q(intake_cohort__iexact=cohort) | Q(academic_year__name__iexact=cohort))

        # Class filtering
        if class_id and class_id.isdigit():
            base = base.filter(current_class_id=int(class_id))

        # Instant search filtering
        if search_query:
            base = base.filter(
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(admission_number__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(intake_cohort__icontains=search_query)
            )

        return base.select_related(
            'current_class', 'section', 'academic_year', 'dormitory', 'room', 'user'
        ).order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        school_slug = self.kwargs.get('school_slug', '')
        context['school_slug'] = school_slug
        
        # Add school object to context
        from tenants.models import School
        try:
            school = School.objects.get(slug=school_slug, is_active=True)
            context['school'] = school
        except School.DoesNotExist:
            context['school'] = None
        
        # Add classes and sections for the form (scoped to this school)
        from academics.models import Class, Section, Subject
        subj_qs = Subject.objects.filter(is_active=True)
        if context.get('school'):
            context['classes'] = Class.objects.filter(is_active=True, school=context['school'])
            context['sections'] = Section.objects.filter(is_active=True, class_name__school=context['school'])
            school_subjs = subj_qs.filter(Q(school=context['school']) | Q(school__isnull=True))
            if school_subjs.exists():
                subj_qs = school_subjs
        else:
            context['classes'] = Class.objects.filter(is_active=True)
            context['sections'] = Section.objects.filter(is_active=True)
        if not subj_qs.exists():
            subj_qs = Subject.objects.all()
        context['subjects'] = subj_qs.order_by('name')
        
        # Add dormitories and rooms for the form
        try:
            from dormitory.models import Dormitory, Room
            context['dormitories'] = Dormitory.objects.filter(is_active=True)
            context['rooms'] = Room.objects.filter(is_active=True)
        except ImportError:
            context['dormitories'] = []
            context['rooms'] = []

        try:
            from clubs.models import Club
            if context.get('school'):
                context['clubs'] = Club.objects.filter(is_active=True, school=context['school']).order_by('name')
            else:
                context['clubs'] = Club.objects.filter(is_active=True).order_by('name')
        except ImportError:
            context['clubs'] = []

        from core.models import AcademicYear
        ay_qs = AcademicYear.objects.all().order_by('-start_date')
        if context.get('school'):
            ay_qs = ay_qs.filter(school=context['school'])
        context['academic_years'] = ay_qs
        active_academic_year = ay_qs.filter(is_active=True).first()
        context['active_academic_year'] = active_academic_year

        # Admissions & Enrollment workflow metrics & cohorts
        count_qs = Student.objects.all()
        if context.get('school'):
            count_qs = count_qs.filter(
                Q(school=context['school']) | Q(current_class__school=context['school']) | Q(user__school=context['school']) | Q(created_by__school=context['school'])
            ).distinct()

        context['status_counts'] = {
            'all': count_qs.count(),
            'enrolled': count_qs.filter(enrollment_status='enrolled').count(),
            'pending': count_qs.filter(enrollment_status='pending').count(),
            'transferred': count_qs.filter(enrollment_status='transferred').count(),
            'withdrawn': count_qs.filter(enrollment_status='withdrawn').count(),
        }

        cohort_set = set(count_qs.exclude(intake_cohort='').values_list('intake_cohort', flat=True).distinct())
        for ay in ay_qs:
            if ay.name:
                cohort_set.add(ay.name)
        context['intake_cohorts'] = sorted(list(cohort_set), reverse=True)
        context['selected_status'] = self.request.GET.get('status', '').strip().lower()
        context['selected_cohort'] = self.request.GET.get('cohort', '').strip()
        context['selected_class'] = self.request.GET.get('class_id', '').strip() or self.request.GET.get('class_filter', '').strip()
        context['search_query'] = self.request.GET.get('search', '').strip() or self.request.GET.get('q', '').strip()

        # Precompute classes and subjects metadata for instant client-side rendering
        classes_meta, all_subjects_meta = get_student_subjects_metadata(context.get('school'), active_academic_year)
        context['classes_meta_json'] = json.dumps(classes_meta)
        context['all_subjects_meta_json'] = json.dumps(all_subjects_meta)

        # Embed everything the in-page edit panel needs so it opens instantly (no AJAX round trip)
        def _iso(value):
            return value.isoformat() if hasattr(value, 'isoformat') else (value or '')

        page_students = list(context.get('students') or [])
        club_map = {}
        try:
            from clubs.models import ClubMembership
            user_ids = [s.user_id for s in page_students if getattr(s, 'user_id', None)]
            if user_ids:
                memberships = ClubMembership.objects.filter(student_id__in=user_ids, status='active')
                if context.get('school'):
                    memberships = memberships.filter(club__school=context['school'])
                for student_id, club_id in memberships.values_list('student_id', 'club_id'):
                    club_map.setdefault(student_id, []).append(club_id)
        except Exception:
            club_map = {}

        # Precompute student subject enrollments
        student_subjects_map = {}
        enr_qs = StudentSubject.objects.filter(student__in=page_students, is_active=True)
        if active_academic_year:
            year_enr = enr_qs.filter(Q(academic_year=active_academic_year) | Q(academic_year__isnull=True))
            if year_enr.exists():
                enr_qs = year_enr
        for st_id, sub_id in enr_qs.values_list('student_id', 'subject_id'):
            student_subjects_map.setdefault(st_id, []).append(sub_id)

        students_data = {}
        for s in page_students:
            students_data[str(s.pk)] = {
                'student_id': s.pk,
                'first_name': s.first_name or '',
                'last_name': s.last_name or '',
                'email': s.email or '',
                'admission_number': s.admission_number or '',
                'date_of_birth': _iso(s.date_of_birth),
                'gender': s.gender or '',
                'blood_group': s.blood_group or '',
                'current_class': s.current_class_id or '',
                'section': s.section_id or '',
                'academic_year': s.academic_year_id or '',
                'intake_cohort': s.intake_cohort or (s.academic_year.name if s.academic_year else ''),
                'enrollment_status': s.enrollment_status or 'enrolled',
                'admission_date': _iso(s.admission_date),
                'current_address': s.current_address or '',
                'city': s.city or '',
                'state': s.state or '',
                'postal_code': s.postal_code or '',
                'father_name': s.father_name or '',
                'father_phone': s.father_phone or '',
                'father_email': s.father_email or '',
                'father_occupation': s.father_occupation or '',
                'mother_name': s.mother_name or '',
                'mother_phone': s.mother_phone or '',
                'mother_email': s.mother_email or '',
                'mother_occupation': s.mother_occupation or '',
                'guardian_name': s.guardian_name or '',
                'guardian_phone': s.guardian_phone or '',
                'guardian_email': s.guardian_email or '',
                'guardian_relation': s.guardian_relation or '',
                'is_transport_required': 'True' if s.is_transport_required else 'False',
                'is_hostel_required': 'True' if s.is_hostel_required else 'False',
                'dormitory': s.dormitory_id or '',
                'room': s.room_id or '',
                'club_ids': club_map.get(s.user_id, []),
                'subject_ids': student_subjects_map.get(s.pk, []),
            }
            students_data[str(s.pk)] = {
                key: (val if isinstance(val, (str, int, list)) else str(val))
                for key, val in students_data[str(s.pk)].items()
            }
        context['students_data'] = students_data

        # Platform schools for electronic transfer
        from tenants.models import School
        current_school = context.get('school') or get_current_school(self.request)
        other_schools_qs = School.objects.filter(is_active=True)
        if current_school:
            other_schools_qs = other_schools_qs.exclude(pk=current_school.pk)
        context['platform_schools'] = list(other_schools_qs.order_by('name').values('id', 'name', 'slug'))

        return context


class StudentSubjectsView(LoginRequiredMixin, View):
    """
    Subjects are now managed directly inline on the student add/edit panel.
    Redirect any direct navigation back to the student list.
    """
    def dispatch(self, request, *args, **kwargs):
        school_slug = kwargs.get('school_slug', '')
        return redirect(f"/school/{school_slug}/students/")


class StudentDetailView(LoginRequiredMixin, View):
    """
    Dedicated student profile page has been eliminated.
    All student viewing, editing, and workflows are served via the in-page edit panel.
    Redirect direct navigation back to the student list page.
    """
    def dispatch(self, request, *args, **kwargs):
        school_slug = kwargs.get('school_slug', '')
        pk = kwargs.get('pk', '')
        if school_slug and pk:
            return redirect(f"/school/{school_slug}/students/?edit={pk}")
        if school_slug:
            return redirect(f"/school/{school_slug}/students/")
        return redirect('students:list')


@method_decorator(csrf_exempt, name='dispatch')
class StudentCreateView(CreateView):
    model = Student
    template_name = 'students/form.html'
    fields = []
    
    def get_success_url(self):
        return f"/school/{self.kwargs.get('school_slug')}/students/"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        # Get admission number prefix from settings
        settings = SystemSetting.objects.first()
        prefix = settings.admission_number_prefix if settings else 'STU'
        context['next_admission_number'] = Student.generate_admission_number(prefix)
        return context
    
    def post(self, request, *args, **kwargs):
        try:
            if not request.user.is_authenticated:
                return JsonResponse({'success': False, 'error': 'Not authenticated'})
            
            from datetime import date
            
            # Get or create settings for prefix
            settings = SystemSetting.objects.first()
            prefix = settings.admission_number_prefix if settings else 'STU'
            
            # Generate admission number or use provided
            admission_number = request.POST.get('admission_number')
            if not admission_number or admission_number.strip() == '':
                admission_number = Student.generate_admission_number(prefix)
            
            # Create user account first
            first_name = request.POST.get('first_name')
            last_name = request.POST.get('last_name')
            email = request.POST.get('email', '').strip()
            
            # Auto-generate email if not provided
            if not email:
                school_slug = get_school_slug_from_request(request)
                email = generate_email(first_name, last_name, school_slug, 'student')
            
            # Check if user with this email already exists
            if User.objects.filter(email=email).exists():
                return JsonResponse({
                    'success': False, 
                    'error': f'A user with email {email} already exists. Please use a different email.'
                })
            
            from tenants.models import School
            school_slug = self.kwargs.get('school_slug', '')
            school = School.objects.filter(slug=school_slug, is_active=True).first() if school_slug else None

            user = User.objects.create(
                email=email,
                password='student123',  # Will be hashed
                first_name=first_name,
                last_name=last_name,
                role='student',
                is_active=True
            )
            user.set_password('student123')  # Hash the password properly
            if school:
                user.school = school
            user.save()
            
            # Get admission date or use today
            admission_date = request.POST.get('admission_date')
            if not admission_date:
                admission_date = date.today()
            
            # Create parent user account if parent/guardian email provided or can be generated
            parent_user = None
            father_email = request.POST.get('father_email', '').strip()
            mother_email = request.POST.get('mother_email', '').strip()
            guardian_email = request.POST.get('guardian_email', '').strip()
            father_name = request.POST.get('father_name', '').strip()
            mother_name = request.POST.get('mother_name', '').strip()
            guardian_name = request.POST.get('guardian_name', '').strip()
            
            # Determine parent email and name (supports father only, mother only, or guardian only)
            parent_email = father_email or mother_email or guardian_email
            parent_full_name = father_name or mother_name or guardian_name
            parent_first_name = parent_full_name.split()[0] if parent_full_name else ''
            parent_last_name = parent_full_name.split()[-1] if parent_full_name and ' ' in parent_full_name else last_name
            
            # Auto-generate parent email if name provided but no email
            if not parent_email and parent_full_name:
                school_slug = get_school_slug_from_request(request)
                parent_email = generate_email(parent_first_name, parent_last_name, school_slug, 'parent')
                if father_name and not father_email:
                    father_email = parent_email
                elif mother_name and not mother_email:
                    mother_email = parent_email
                elif guardian_name and not guardian_email:
                    guardian_email = parent_email
            
            if parent_email:
                # Check if parent account already exists
                try:
                    parent_user = User.objects.get(email=parent_email, role='parent')
                except User.DoesNotExist:
                    # Create new parent account
                    try:
                        parent_user = User.objects.create(
                            email=parent_email,
                            first_name=parent_first_name or 'Parent',
                            last_name=parent_last_name,  # Already set to student's last name if not provided
                            role='parent',
                            phone=request.POST.get('father_phone', '').strip() or request.POST.get('mother_phone', '').strip() or request.POST.get('guardian_phone', '').strip(),
                            is_active=True
                        )
                        parent_user.set_password('parent123')  # Default password
                        if parent_user and school and not getattr(parent_user, 'school', None):
                            parent_user.school = school
                            parent_user.save(update_fields=['school'])
                    except Exception as e:
                        print(f"[WARNING] Could not create parent account: {e}")

            # Resolve current class/section scoped to school
            from academics.models import Class, Section
            current_class = None
            section = None
            current_class_id = request.POST.get('current_class')
            if current_class_id:
                if school:
                    current_class = Class.objects.filter(id=current_class_id, school=school).first()
                else:
                    current_class = Class.objects.filter(id=current_class_id).first()
            section_id = request.POST.get('section')
            if section_id:
                if school:
                    section = Section.objects.filter(id=section_id, class_name__school=school).first()
                else:
                    section = Section.objects.filter(id=section_id).first()
            
            # Resolve academic year
            from core.models import AcademicYear
            academic_year = None
            ay_raw = request.POST.get('academic_year')
            if ay_raw and str(ay_raw).isdigit():
                academic_year = AcademicYear.objects.filter(id=int(ay_raw)).first()
            if not academic_year:
                ay_qs = AcademicYear.objects.filter(is_active=True)
                if school:
                    ay_qs = ay_qs.filter(school=school)
                academic_year = ay_qs.first()
            if not academic_year and school:
                academic_year = AcademicYear.objects.filter(school=school).order_by('-start_date').first()

            # Admissions & Enrollment workflow fields
            enrollment_status = request.POST.get('enrollment_status', 'enrolled').strip().lower()
            if enrollment_status not in ('enrolled', 'pending', 'transferred', 'withdrawn', 'graduated'):
                enrollment_status = 'enrolled'
            
            intake_cohort = request.POST.get('intake_cohort', '').strip()
            if not intake_cohort and academic_year:
                intake_cohort = academic_year.name

            # Create student with all fields including parent details, academic year, and enrollment status
            student = Student.objects.create(
                user=user,
                first_name=first_name,
                last_name=last_name,
                email=email,
                admission_number=admission_number,
                admission_date=admission_date,
                enrollment_status=enrollment_status,
                intake_cohort=intake_cohort,
                date_of_birth=request.POST.get('date_of_birth') or None,
                gender=request.POST.get('gender', ''),
                blood_group=request.POST.get('blood_group', ''),
                religion=request.POST.get('religion', ''),
                current_address=request.POST.get('current_address', ''),
                city=request.POST.get('city', ''),
                state=request.POST.get('state', ''),
                country=request.POST.get('country', 'US'),
                postal_code=request.POST.get('postal_code', ''),
                # Parent Details
                father_name=father_name,
                father_phone=request.POST.get('father_phone', '').strip() or None,
                father_email=father_email,
                father_occupation=request.POST.get('father_occupation', '').strip(),
                mother_name=mother_name,
                mother_phone=request.POST.get('mother_phone', '').strip() or None,
                mother_email=mother_email,
                mother_occupation=request.POST.get('mother_occupation', '').strip(),
                guardian_name=guardian_name,
                guardian_phone=request.POST.get('guardian_phone', '').strip() or None,
                guardian_email=guardian_email,
                guardian_relation=request.POST.get('guardian_relation', '').strip(),
                parent_user=parent_user,  # Link to parent user account
                current_class=current_class,
                section=section,
                academic_year=academic_year,
                school=school,
                created_by=request.user
            )

            # Transport and dormitory
            student.is_transport_required = request.POST.get('is_transport_required') == 'True'
            student.is_hostel_required = request.POST.get('is_hostel_required') == 'True'
            if student.is_hostel_required:
                dormitory_id = request.POST.get('dormitory')
                room_id = request.POST.get('room')
                if dormitory_id:
                    try:
                        from dormitory.models import Dormitory
                        student.dormitory = Dormitory.objects.get(id=dormitory_id)
                    except Exception:
                        pass
                if room_id:
                    try:
                        from dormitory.models import Room
                        student.room = Room.objects.get(id=room_id)
                    except Exception:
                        pass
            student.save()

            if current_class and academic_year and enrollment_status == 'enrolled':
                try:
                    from .models import StudentClassEnrollment
                    StudentClassEnrollment.objects.create(
                        student=student,
                        school=school,
                        academic_year=academic_year,
                        class_name=current_class,
                        section=section,
                        roll_number=student.roll_number or '',
                        status='active',
                        enrolled_date=admission_date,
                        created_by=request.user
                    )
                except Exception as e:
                    print(f"[WARNING] Could not create StudentClassEnrollment: {e}")

            # Record admission timeline entry
            try:
                from .models import StudentTimeline
                timeline_title = 'Student Admitted & Enrolled' if enrollment_status == 'enrolled' else 'Admission Application Registered (Pending)'
                timeline_desc = (
                    f"Admitted to {current_class.name if current_class else 'Class'}" + (f" ({section.name})" if section else '') + (f" for cohort {intake_cohort or academic_year.name}" if (intake_cohort or academic_year) else '')
                    if enrollment_status == 'enrolled'
                    else f"Application registered for {current_class.name if current_class else 'Class'} (Cohort: {intake_cohort or 'Pending'}). Pending confirmation."
                )
                StudentTimeline.objects.create(
                    student=student,
                    timeline_type='admission',
                    title=timeline_title,
                    description=timeline_desc,
                    date=admission_date,
                    created_by=request.user
                )
            except Exception as e:
                pass

            club_ids = request.POST.getlist('club_ids')
            if club_ids:
                from datetime import date
                try:
                    from clubs.models import Club, ClubMembership
                    clubs_qs = Club.objects.filter(id__in=club_ids, is_active=True)
                    if school:
                        clubs_qs = clubs_qs.filter(school=school)
                    for club in clubs_qs:
                        membership, _ = ClubMembership.objects.get_or_create(
                            student=user,
                            club=club,
                            defaults={
                                'application_reason': 'Added by admin',
                                'parent_consent': True,
                                'status': 'active',
                                'join_date': date.today(),
                            },
                        )
                        if membership.status != 'active':
                            membership.status = 'active'
                            membership.join_date = membership.join_date or date.today()
                            if not membership.application_reason:
                                membership.application_reason = 'Added by admin'
                            membership.save(update_fields=['status', 'join_date', 'application_reason'])
                except Exception:
                    pass

            # Save student subject enrollments
            subject_ids = request.POST.getlist('subject_ids') or request.POST.getlist('subjects')
            if subject_ids:
                from academics.models import Subject, AssignedSubject
                from .models import StudentSubject
                for sid in subject_ids:
                    try:
                        sub = Subject.objects.filter(id=int(sid)).first()
                        if not sub:
                            continue
                        assigned_sub = None
                        if current_class:
                            assigned_qs = AssignedSubject.objects.filter(
                                class_name=current_class,
                                subject=sub,
                                is_active=True
                            )
                            if academic_year:
                                assigned_qs = assigned_qs.filter(academic_year=academic_year)
                            if section:
                                assigned_sub = assigned_qs.filter(section=section).first()
                            if not assigned_sub:
                                assigned_sub = assigned_qs.filter(section__isnull=True).first()

                        StudentSubject.objects.get_or_create(
                            student=student,
                            subject=sub,
                            academic_year=academic_year,
                            defaults={
                                'school': school,
                                'assigned_subject': assigned_sub,
                                'created_by': request.user,
                                'is_active': True,
                            }
                        )
                    except Exception as e:
                        print(f"[WARNING] Could not enroll student in subject {sid}: {e}")
            
            return JsonResponse({
                'success': True, 
                'message': 'Student added successfully',
                'admission_number': admission_number
            })
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'success': False, 'error': str(e)})


@method_decorator(csrf_exempt, name='dispatch')
class StudentUpdateView(UpdateView):
    model = Student
    template_name = 'students/edit_modal.html'
    fields = []
    
    def get_success_url(self):
        return f"/school/{self.kwargs.get('school_slug')}/students/"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        context['student'] = self.get_object()
        from academics.models import Class, Section, Subject
        subj_qs = Subject.objects.filter(is_active=True)
        if school:
            context['classes'] = Class.objects.filter(is_active=True, school=school)
            context['sections'] = Section.objects.filter(is_active=True, class_name__school=school)
            school_subjs = subj_qs.filter(Q(school=school) | Q(school__isnull=True))
            if school_subjs.exists():
                subj_qs = school_subjs
        else:
            context['classes'] = Class.objects.filter(is_active=True)
            context['sections'] = Section.objects.filter(is_active=True)
        if not subj_qs.exists():
            subj_qs = Subject.objects.all()
        context['subjects'] = subj_qs.order_by('name')
        
        # Add dormitories and rooms for the form
        try:
            from dormitory.models import Dormitory, Room
            context['dormitories'] = Dormitory.objects.filter(is_active=True)
            context['rooms'] = Room.objects.filter(is_active=True)
        except ImportError:
            context['dormitories'] = []
            context['rooms'] = []

        try:
            from clubs.models import Club, ClubMembership
            clubs_qs = Club.objects.filter(is_active=True)
            if school:
                clubs_qs = clubs_qs.filter(school=school)
            context['clubs'] = clubs_qs.order_by('name')
            selected = set()
            if context['student'] and getattr(context['student'], 'user_id', None):
                memberships_qs = ClubMembership.objects.filter(student_id=context['student'].user_id, status='active')
                if school:
                    memberships_qs = memberships_qs.filter(club__school=school)
                selected = set(memberships_qs.values_list('club_id', flat=True))
            context['selected_club_ids'] = selected
        except ImportError:
            context['clubs'] = []
            context['selected_club_ids'] = set()
        
        # Precompute classes and subjects metadata for inline editing
        classes_meta, all_subjects_meta = get_student_subjects_metadata(school, None)
        context['classes_meta_json'] = json.dumps(classes_meta)
        context['all_subjects_meta_json'] = json.dumps(all_subjects_meta)
        student = context.get('student')
        if student:
            context['enrolled_subject_ids'] = list(
                StudentSubject.objects.filter(student=student, is_active=True).values_list('subject_id', flat=True)
            )
        else:
            context['enrolled_subject_ids'] = []

        return context
    
    def post(self, request, *args, **kwargs):
        try:
            if not request.user.is_authenticated:
                return JsonResponse({'success': False, 'error': 'Not authenticated'})
            
            student = self.get_object()
            
            # Update student fields
            student.first_name = request.POST.get('first_name', student.first_name)
            student.last_name = request.POST.get('last_name', student.last_name)
            student.email = request.POST.get('email', student.email)
            student.date_of_birth = request.POST.get('date_of_birth', student.date_of_birth)
            student.gender = request.POST.get('gender', student.gender)
            student.blood_group = request.POST.get('blood_group', student.blood_group)
            student.current_address = request.POST.get('current_address', student.current_address)
            student.city = request.POST.get('city', student.city)
            student.state = request.POST.get('state', student.state)
            student.postal_code = request.POST.get('postal_code', student.postal_code)
            student.admission_date = request.POST.get('admission_date', student.admission_date)
            
            # Admissions & Enrollment workflow fields
            if 'enrollment_status' in request.POST:
                new_status = request.POST.get('enrollment_status', '').strip().lower()
                if new_status in ('enrolled', 'pending', 'transferred', 'withdrawn', 'graduated'):
                    student.enrollment_status = new_status
            if 'intake_cohort' in request.POST:
                student.intake_cohort = request.POST.get('intake_cohort', '').strip()
            if 'academic_year' in request.POST:
                ay_id = request.POST.get('academic_year', '').strip()
                if ay_id and ay_id.isdigit():
                    from core.models import AcademicYear
                    ay = AcademicYear.objects.filter(id=int(ay_id)).first()
                    if ay:
                        student.academic_year = ay
            
            # Update transport and dormitory details
            student.is_transport_required = request.POST.get('is_transport_required') == 'True'
            student.is_hostel_required = request.POST.get('is_hostel_required') == 'True'
            
            if student.is_hostel_required:
                dormitory_id = request.POST.get('dormitory')
                room_id = request.POST.get('room')
                if dormitory_id:
                    try:
                        from dormitory.models import Dormitory
                        student.dormitory = Dormitory.objects.get(id=dormitory_id)
                    except:
                        pass
                if room_id:
                    try:
                        from dormitory.models import Room
                        student.room = Room.objects.get(id=room_id)
                    except:
                        pass
            else:
                student.dormitory = None
                student.room = None
            
            # Update academic details
            current_class_id = request.POST.get('current_class')
            if current_class_id:
                from academics.models import Class
                from tenants.models import School
                school_slug = self.kwargs.get('school_slug', '')
                school = School.objects.filter(slug=school_slug, is_active=True).first() if school_slug else None
                if school:
                    current_class = Class.objects.filter(id=current_class_id, school=school).first()
                else:
                    current_class = Class.objects.filter(id=current_class_id).first()
                if current_class:
                    student.current_class = current_class
                else:
                    student.current_class = None
            
            section_id = request.POST.get('section')
            if section_id:
                from academics.models import Section
                from tenants.models import School
                school_slug = self.kwargs.get('school_slug', '')
                school = School.objects.filter(slug=school_slug, is_active=True).first() if school_slug else None
                if school:
                    section = Section.objects.filter(id=section_id, class_name__school=school).first()
                else:
                    section = Section.objects.filter(id=section_id).first()
                if section:
                    student.section = section
                else:
                    student.section = None
            
            # Ensure student is linked to a school if missing
            if not getattr(student, 'school', None):
                try:
                    if student.current_class and getattr(student.current_class, 'school', None):
                        student.school = student.current_class.school
                    elif student.user and getattr(student.user, 'school', None):
                        student.school = student.user.school
                except Exception:
                    pass
            
            # Update parent details (supports father only, mother only, or guardian only)
            if 'father_name' in request.POST:
                student.father_name = request.POST.get('father_name', '').strip()
            if 'father_phone' in request.POST:
                student.father_phone = request.POST.get('father_phone', '').strip() or None
            father_email = request.POST.get('father_email', '').strip()
            student.father_email = father_email
            if 'father_occupation' in request.POST:
                student.father_occupation = request.POST.get('father_occupation', '').strip()

            if 'mother_name' in request.POST:
                student.mother_name = request.POST.get('mother_name', '').strip()
            if 'mother_phone' in request.POST:
                student.mother_phone = request.POST.get('mother_phone', '').strip() or None
            mother_email = request.POST.get('mother_email', '').strip()
            student.mother_email = mother_email
            if 'mother_occupation' in request.POST:
                student.mother_occupation = request.POST.get('mother_occupation', '').strip()

            if 'guardian_name' in request.POST:
                student.guardian_name = request.POST.get('guardian_name', '').strip()
            if 'guardian_phone' in request.POST:
                student.guardian_phone = request.POST.get('guardian_phone', '').strip() or None
            guardian_email = request.POST.get('guardian_email', '').strip()
            student.guardian_email = guardian_email
            if 'guardian_relation' in request.POST:
                student.guardian_relation = request.POST.get('guardian_relation', '').strip()
            
            # Create or link parent user account if email provided or can be generated
            father_name = student.father_name
            mother_name = student.mother_name
            guardian_name = student.guardian_name
            
            parent_email = father_email or mother_email or guardian_email
            parent_full_name = father_name or mother_name or guardian_name
            parent_first_name = parent_full_name.split()[0] if parent_full_name else ''
            parent_last_name = parent_full_name.split()[-1] if parent_full_name and ' ' in parent_full_name else student.last_name
            
            # Auto-generate parent email if name provided but no email
            if not parent_email and parent_full_name and not student.parent_user:
                school_slug = get_school_slug_from_request(request)
                parent_email = generate_email(parent_first_name, parent_last_name, school_slug, 'parent')
                # Update the student's email fields with the auto-generated email
                if father_name:
                    student.father_email = parent_email
                elif mother_name:
                    student.mother_email = parent_email
                else:
                    student.guardian_email = parent_email
            
            if parent_email and not student.parent_user:
                # Check if parent account already exists
                try:
                    parent_user = User.objects.get(email=parent_email, role='parent')
                    student.parent_user = parent_user
                except User.DoesNotExist:
                    # Create new parent account
                    try:
                        parent_user = User.objects.create(
                            email=parent_email,
                            first_name=parent_first_name or 'Parent',
                            last_name=parent_last_name or student.last_name,
                            role='parent',
                            phone=request.POST.get('father_phone', '').strip() or request.POST.get('mother_phone', '').strip() or request.POST.get('guardian_phone', '').strip(),
                            is_active=True
                        )
                        parent_user.set_password('parent123')  # Default password
                        if school and not getattr(parent_user, 'school', None):
                            parent_user.school = school
                        parent_user.save()
                        student.parent_user = parent_user
                    except Exception as e:
                        print(f"[WARNING] Could not create parent account: {e}")
            
            student.save()

            # Synchronize active class enrollment
            if student.current_class and student.academic_year:
                try:
                    from .models import StudentClassEnrollment
                    enr = StudentClassEnrollment.objects.filter(student=student, academic_year=student.academic_year).first()
                    status = 'active' if (student.is_active and student.enrollment_status == 'enrolled') else ('completed' if (student.is_alumni or student.enrollment_status == 'graduated') else ('transferred' if student.enrollment_status == 'transferred' else 'withdrawn'))
                    if enr:
                        enr.class_name = student.current_class
                        enr.section = student.section
                        enr.status = status
                        if student.roll_number:
                            enr.roll_number = student.roll_number
                        enr.save(update_fields=['class_name', 'section', 'status', 'roll_number', 'updated_at'])
                    else:
                        from datetime import date
                        StudentClassEnrollment.objects.create(
                            student=student,
                            school=student.school,
                            academic_year=student.academic_year,
                            class_name=student.current_class,
                            section=student.section,
                            roll_number=student.roll_number or '',
                            status=status,
                            enrolled_date=student.admission_date or date.today(),
                            created_by=request.user
                        )
                except Exception as e:
                    print(f"[WARNING] Could not sync StudentClassEnrollment: {e}")

            club_ids = set(map(int, request.POST.getlist('club_ids')))
            if club_ids is not None:
                from datetime import date
                try:
                    from clubs.models import Club, ClubMembership
                    school = get_current_school(request)
                    allowed_clubs = Club.objects.filter(is_active=True)
                    if school:
                        allowed_clubs = allowed_clubs.filter(school=school)
                    allowed_ids = set(allowed_clubs.values_list('id', flat=True))
                    club_ids = set([cid for cid in club_ids if cid in allowed_ids])

                    memberships_qs = ClubMembership.objects.filter(student=student.user, club__in=allowed_clubs)
                    memberships_qs.exclude(club_id__in=club_ids).exclude(status='inactive').update(status='inactive')

                    for club in allowed_clubs.filter(id__in=club_ids):
                        membership, _ = ClubMembership.objects.get_or_create(
                            student=student.user,
                            club=club,
                            defaults={
                                'application_reason': 'Added by admin',
                                'parent_consent': True,
                                'status': 'active',
                                'join_date': date.today(),
                            },
                        )
                        if membership.status != 'active':
                            membership.status = 'active'
                            membership.join_date = membership.join_date or date.today()
                            if not membership.application_reason:
                                membership.application_reason = 'Added by admin'
                            membership.save(update_fields=['status', 'join_date', 'application_reason'])
                except Exception:
                    pass

            # Process subject enrollments
            if 'subject_ids' in request.POST or 'subjects' in request.POST or request.POST.get('has_subjects_section'):
                raw_sids = request.POST.getlist('subject_ids') or request.POST.getlist('subjects')
                new_subject_ids = set()
                for sid in raw_sids:
                    try:
                        new_subject_ids.add(int(sid))
                    except (ValueError, TypeError):
                        pass

                from core.models import AcademicYear
                from academics.models import Subject, AssignedSubject
                from .models import StudentSubject

                target_year = student.academic_year
                if not target_year:
                    ay_qs = AcademicYear.objects.filter(is_active=True)
                    if student.school:
                        ay_qs = ay_qs.filter(school=student.school)
                    target_year = ay_qs.first()

                with transaction.atomic():
                    # Deactivate subjects no longer selected
                    deact_filter = {'student': student, 'is_active': True}
                    if target_year:
                        deact_filter['academic_year'] = target_year
                    StudentSubject.objects.filter(**deact_filter).exclude(subject_id__in=new_subject_ids).update(is_active=False)

                    # Add or activate selected subjects
                    for sid in new_subject_ids:
                        sub = Subject.objects.filter(id=sid).first()
                        if not sub:
                            continue
                        assigned_sub = None
                        if student.current_class:
                            assigned_qs = AssignedSubject.objects.filter(
                                class_name=student.current_class,
                                subject=sub,
                                is_active=True
                            )
                            if target_year:
                                assigned_qs = assigned_qs.filter(academic_year=target_year)
                            if student.section:
                                assigned_sub = assigned_qs.filter(section=student.section).first()
                            if not assigned_sub:
                                assigned_sub = assigned_qs.filter(section__isnull=True).first()

                        lookup = {
                            'student': student,
                            'subject': sub,
                        }
                        if target_year:
                            lookup['academic_year'] = target_year

                        obj, created = StudentSubject.objects.get_or_create(
                            **lookup,
                            defaults={
                                'school': student.school,
                                'assigned_subject': assigned_sub,
                                'created_by': request.user,
                                'is_active': True,
                            }
                        )
                        if not created and not obj.is_active:
                            obj.is_active = True
                            obj.assigned_subject = assigned_sub
                            obj.save(update_fields=['is_active', 'assigned_subject'])
            
            # Update user email if changed
            if student.user.email != student.email:
                student.user.email = student.email
                student.user.first_name = student.first_name
                student.user.last_name = student.last_name
                student.user.save()
            
            return JsonResponse({'success': True, 'message': 'Student updated successfully'})
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'success': False, 'error': str(e)})


@method_decorator(csrf_exempt, name='dispatch')
class StudentDeleteView(DeleteView):
    model = Student
    
    def get_success_url(self):
        return f"/school/{self.kwargs.get('school_slug')}/students/"
    
    def post(self, request, *args, **kwargs):
        try:
            if not request.user.is_authenticated:
                return JsonResponse({'success': False, 'error': 'Not authenticated'})

            student = self.get_object()
            if getattr(student, 'is_sample_data', False) or getattr(student.user, 'is_sample_data', False):
                return JsonResponse({'success': False, 'error': 'Sample/Demo data cannot be deleted.'})

            # Check if student has historical academic or financial records
            has_fee_records = hasattr(student, 'fee_collections') and student.fee_collections.exists()
            has_exam_records = (
                (hasattr(student, 'exam_marks') and student.exam_marks.exists()) or
                (hasattr(student, 'exam_results') and student.exam_results.exists())
            )
            has_attendance_records = hasattr(student, 'attendance_records') and student.attendance_records.exists()
            has_canteen_sales = hasattr(student, 'canteen_sales') and student.canteen_sales.exists()

            if has_fee_records or has_exam_records or has_attendance_records or has_canteen_sales:
                from django.utils import timezone
                # Preserve historical audits: soft-deactivate student
                student.is_active = False
                student.leaving_date = timezone.now().date()
                student.leaving_reason = request.POST.get('reason', 'Transferred / Deactivated')
                student.save(update_fields=['is_active', 'leaving_date', 'leaving_reason'])

                # Deactivate user account
                if student.user:
                    student.user.is_active = False
                    student.user.save(update_fields=['is_active'])

                # Deactivate room allocation if present
                if hasattr(student, 'room_allocation'):
                    ra = student.room_allocation
                    ra.is_active = False
                    ra.save()

                return JsonResponse({
                    'success': True,
                    'message': 'Student has historical fee/academic records; safely deactivated and preserved for audits.'
                })
            else:
                student.user.delete()  # Safe to delete clean record without historical data
                return JsonResponse({'success': True, 'message': 'Student deleted successfully'})
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'success': False, 'error': str(e)})


class ParentListView(LoginRequiredMixin, ListView):
    model = User
    template_name = 'students/parents.html'
    context_object_name = 'parents'
    paginate_by = 20
    
    def get_queryset(self):
        school = get_current_school(self.request)
        qs = User.objects.filter(role='parent').order_by('-created_at')
        if school:
            qs = qs.filter(
                Q(school=school) |
                Q(children__current_class__school=school) |
                Q(children__user__school=school)
            ).distinct()
        return qs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        return context


class ParentDetailView(LoginRequiredMixin, DetailView):
    model = User
    
    def get(self, request, *args, **kwargs):
        try:
            parent = self.get_object()
            if parent.role != 'parent':
                return JsonResponse({'success': False, 'error': 'Not a parent user'})
            
            # Get children (students linked to this parent) scoped to this school
            school_slug = self.kwargs.get('school_slug', '')
            from tenants.models import School
            school = School.objects.filter(slug=school_slug, is_active=True).first() if school_slug else None
            children = Student.objects.filter(parent_user=parent)
            if school:
                children = children.filter(Q(current_class__school=school) | Q(user__school=school)).distinct()
            children_data = [{
                'name': f"{child.first_name} {child.last_name}",
                'admission_number': child.admission_number
            } for child in children]
            
            return JsonResponse({
                'success': True,
                'parent': {
                    'name': parent.get_full_name(),
                    'first_name': parent.first_name,
                    'last_name': parent.last_name,
                    'email': parent.email,
                    'phone': str(parent.phone) if parent.phone else '',
                    'is_active': parent.is_active
                },
                'children': children_data
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})


class StudentExportView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        fmt = request.GET.get('format', 'csv').lower()
        school_slug = kwargs.get('school_slug', '')
        from tenants.models import School
        school = School.objects.filter(slug=school_slug, is_active=True).first() if school_slug else None
        students = Student.objects.select_related('current_class', 'section')
        if school:
            students = students.filter(Q(current_class__school=school) | Q(user__school=school) | Q(parent_user__school=school) | Q(created_by__school=school)).distinct()
        else:
            students = students.all()

        ids_param = request.GET.get('ids', '').strip()
        if ids_param:
            id_list = [i.strip() for i in ids_param.split(',') if i.strip().isdigit()]
            if id_list:
                students = students.filter(id__in=id_list)

        headers = [
            'admission_number', 'first_name', 'last_name', 'gender', 'date_of_birth', 'admission_date',
            'current_class', 'section', 'email', 'current_address', 'city', 'state', 'postal_code',
            'father_name', 'father_phone', 'father_email', 'father_occupation',
            'mother_name', 'mother_phone', 'mother_email', 'mother_occupation',
            'guardian_name', 'guardian_phone', 'guardian_email', 'guardian_relation'
        ]
        rows = []
        for s in students:
            rows.append([
                s.admission_number or '', s.first_name or '', s.last_name or '', s.gender or '',
                s.date_of_birth.isoformat() if s.date_of_birth else '',
                s.admission_date.isoformat() if s.admission_date else '',
                getattr(s.current_class, 'name', '') or '',
                getattr(s.section, 'name', '') or '',
                s.email or '', s.current_address or '', s.city or '', s.state or '', s.postal_code or '',
                s.father_name or '', str(s.father_phone) if s.father_phone else '', s.father_email or '', s.father_occupation or '',
                s.mother_name or '', str(s.mother_phone) if s.mother_phone else '', s.mother_email or '', s.mother_occupation or '',
                s.guardian_name or '', str(s.guardian_phone) if s.guardian_phone else '', s.guardian_email or '', s.guardian_relation or ''
            ])
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        if fmt == 'excel' or fmt == 'xlsx':
            wb = Workbook()
            ws = wb.active
            ws.title = 'Students'
            ws.append(headers)
            for r in rows:
                ws.append(r)
            bio = io.BytesIO()
            wb.save(bio)
            bio.seek(0)
            resp = HttpResponse(bio.getvalue(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            resp['Content-Disposition'] = f'attachment; filename="students_{ts}.xlsx"'
            return resp
        else:
            sio = io.StringIO()
            writer = csv.writer(sio)
            writer.writerow(headers)
            for r in rows:
                writer.writerow(r)
            resp = HttpResponse(sio.getvalue(), content_type='text/csv')
            resp['Content-Disposition'] = f'attachment; filename="students_{ts}.csv"'
            return resp


class StudentTemplateView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        wb = Workbook()
        ws_template = wb.active
        ws_template.title = 'Template'
        headers = [
            'admission_number', 'first_name', 'last_name', 'gender', 'date_of_birth', 'admission_date',
            'current_class', 'section', 'email', 'current_address', 'city', 'state', 'postal_code',
            'father_name', 'father_phone', 'father_email', 'father_occupation',
            'mother_name', 'mother_phone', 'mother_email', 'mother_occupation',
            'guardian_name', 'guardian_phone', 'guardian_email', 'guardian_relation'
        ]
        ws_template.append(headers)
        required_fields = {'first_name', 'last_name', 'gender', 'date_of_birth', 'admission_date', 'current_class', 'current_address', 'city', 'state'}
        autogenerated_fields = {'admission_number', 'email', 'father_email', 'mother_email'}
        required_fill = PatternFill(fill_type='solid', start_color='FFFFF3CC', end_color='FFFFF3CC')
        autogenerated_fill = PatternFill(fill_type='solid', start_color='FFC6EFCE', end_color='FFC6EFCE')
        header_font = Font(bold=True)
        header_align = Alignment(horizontal='center', vertical='center')
        for col_idx, title in enumerate(headers, start=1):
            cell = ws_template.cell(row=1, column=col_idx)
            cell.font = header_font
            cell.alignment = header_align
            if title in required_fields:
                cell.fill = required_fill
                cell.comment = Comment('Required field', 'System')
            elif title in autogenerated_fields:
                cell.fill = autogenerated_fill
                cell.comment = Comment('Auto-generated if left blank', 'System')
        ws_template.freeze_panes = 'A2'
        for col_idx, title in enumerate(headers, start=1):
            ws_template.column_dimensions[ws_template.cell(row=1, column=col_idx).column_letter].width = max(14, len(title) + 2)
        ws_sample = wb.create_sheet('Sample Data')
        ws_sample.append(headers)
        for col_idx, title in enumerate(headers, start=1):
            c = ws_sample.cell(row=1, column=col_idx)
            c.font = header_font
            c.alignment = header_align
            if title in required_fields:
                c.fill = required_fill
            elif title in autogenerated_fields:
                c.fill = autogenerated_fill
        ws_sample.append([
            'STU00001', 'John', 'Doe', 'male', '2012-05-10', '2024-01-10', 'Grade 1', 'A', 'john.doe@school.com',
            '123 Main St', 'Nairobi', 'Nairobi', '00100',
            'James Doe', '+254700000001', 'james.doe@example.com', 'Engineer',
            'Jane Doe', '+254700000002', 'jane.doe@example.com', 'Doctor',
            '', '', '', ''
        ])
        ws_instr = wb.create_sheet('Instructions')
        instructions = [
            ['Legend:'],
            ['Yellow = Required field'],
            ['Green = Auto-generated if left blank'],
            [''],
            ['Fill data in the Template sheet. Dates must be in YYYY-MM-DD format.'],
            ['current_class and section should match existing names in your system.'],
            ['Required fields: first_name, last_name, date_of_birth, gender, admission_date, current_class, current_address, city, state.'],
            ['Auto-generated fields: admission_number, email. Parent emails (father_email/mother_email) will be auto-generated if names are provided and emails are left blank.'],
            ['Phones should include country code, e.g., +2547xxxxxxx.']
        ]
        for row in instructions:
            ws_instr.append(row)
        bio = io.BytesIO()
        wb.save(bio)
        bio.seek(0)
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        resp = HttpResponse(bio.getvalue(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        resp['Content-Disposition'] = f'attachment; filename="students_template_{ts}.xlsx"'
        return resp


@method_decorator(csrf_exempt, name='dispatch')
class StudentImportSheetsView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        f = request.FILES.get('file')
        if not f:
            return JsonResponse({'success': False, 'error': 'No file uploaded'})
        name = f.name.lower()
        if not name.endswith('.xlsx'):
            return JsonResponse({'success': True, 'sheets': []})
        try:
            wb = load_workbook(f, read_only=True)
            return JsonResponse({'success': True, 'sheets': wb.sheetnames})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})


@method_decorator(csrf_exempt, name='dispatch')
class StudentImportPreviewView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        f = request.FILES.get('file')
        if not f:
            return JsonResponse({'success': False, 'error': 'No file uploaded'})
        name = f.name.lower()
        try:
            if name.endswith('.csv'):
                df = pd.read_csv(f, dtype=str)
            elif name.endswith('.xlsx'):
                sheet = request.POST.get('sheet_name')
                df = pd.read_excel(f, sheet_name=sheet if sheet else 0, dtype=str)
            else:
                return JsonResponse({'success': False, 'error': 'Unsupported file type'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': f'Failed to read file: {e}'})

        # Normalize columns
        original_columns = list(df.columns)
        norm_columns = [str(c).strip().lower().replace('\n', ' ').replace('  ', ' ').replace(' ', '_') for c in original_columns]
        df.columns = norm_columns

        # Canonical fields and metadata
        canonical_fields = [
            'admission_number', 'first_name', 'last_name', 'gender', 'date_of_birth', 'admission_date',
            'current_class', 'section', 'email', 'current_address', 'city', 'state', 'postal_code',
            'father_name', 'father_phone', 'father_email', 'father_occupation',
            'mother_name', 'mother_phone', 'mother_email', 'mother_occupation',
            'guardian_name', 'guardian_phone', 'guardian_email', 'guardian_relation'
        ]
        required = {'first_name', 'last_name', 'gender', 'date_of_birth', 'admission_date', 'current_class', 'current_address', 'city', 'state'}
        autogenerated = {'admission_number', 'email', 'father_email', 'mother_email'}

        # Synonyms mapping (normalized -> canonical)
        synonyms = {
            'firstname': 'first_name',
            'first': 'first_name',
            'lastname': 'last_name',
            'last': 'last_name',
            'dob': 'date_of_birth',
            'dateofbirth': 'date_of_birth',
            'admissiondate': 'admission_date',
            'class': 'current_class',
            'class_name': 'current_class',
            'grade': 'current_class',
            'section_name': 'section',
            'zip': 'postal_code',
            'postcode': 'postal_code',
            'father_mobile': 'father_phone',
            'father_tel': 'father_phone',
            'mother_mobile': 'mother_phone',
            'mother_tel': 'mother_phone',
        }

        # Build column mapping
        column_map = {}
        mapped_canonicals = set()
        for src in norm_columns:
            if src in canonical_fields:
                column_map[src] = src
                mapped_canonicals.add(src)
            elif src in synonyms:
                column_map[src] = synonyms[src]
                mapped_canonicals.add(synonyms[src])
            else:
                column_map[src] = None

        missing_required = sorted(list(required - mapped_canonicals))

        # Prepare a working dataframe with canonical columns only
        work_df = pd.DataFrame()
        for src, dst in column_map.items():
            if dst:
                work_df[dst] = df[src]
        work_df = work_df.fillna('')

        total_rows = len(work_df.index)
        row_errors = []

        # Vectorized date validation
        def is_valid_date(series):
            try:
                conv = pd.to_datetime(series, errors='coerce')
                return ~conv.isna()
            except Exception:
                return pd.Series([False] * len(series))

        # Preload reference names for existence checks (prefer school-scoped)
        from academics.models import Class, Section
        school_slug = kwargs.get('school_slug', '')
        from tenants.models import School
        school = School.objects.filter(slug=school_slug, is_active=True).first() if school_slug else None
        if school:
            class_names = set([n.lower() for n in Class.objects.filter(school=school).values_list('name', flat=True)])
            section_names = set([n.lower() for n in Section.objects.filter(class_name__school=school).values_list('name', flat=True)])
        else:
            class_names = set([n.lower() for n in Class.objects.values_list('name', flat=True)])
            section_names = set([n.lower() for n in Section.objects.values_list('name', flat=True)])

        # Validate rows
        for idx in range(total_rows):
            errs = []
            row = work_df.iloc[idx]
            # Required non-empty
            for col in required:
                if col not in work_df.columns or not str(row.get(col, '')).strip():
                    errs.append(f"Missing required: {col}")
            # Dates
            if 'date_of_birth' in work_df.columns and str(row.get('date_of_birth', '')).strip():
                if not is_valid_date(pd.Series([row['date_of_birth']])).iloc[0]:
                    errs.append('Invalid date format: date_of_birth')
            if 'admission_date' in work_df.columns and str(row.get('admission_date', '')).strip():
                if not is_valid_date(pd.Series([row['admission_date']])).iloc[0]:
                    errs.append('Invalid date format: admission_date')
            # Existence checks (best-effort)
            if 'current_class' in work_df.columns and str(row.get('current_class', '')).strip():
                if row['current_class'].strip().lower() not in class_names:
                    errs.append('Unknown class name: current_class')
            if 'section' in work_df.columns and str(row.get('section', '')).strip():
                if row['section'].strip().lower() not in section_names:
                    errs.append('Unknown section name: section')
            if errs:
                row_errors.append({'row': idx + 2, 'errors': errs})

        invalid_rows = len(row_errors)
        can_import = (invalid_rows == 0) and (len(missing_required) == 0)

        # Build first non-empty values per source column
        first_values = {}
        for src in norm_columns:
            val = ''
            try:
                ser = df[src]
                for v in ser:
                    if pd.isna(v):
                        continue
                    s = str(v).strip()
                    if s:
                        val = s
                        break
            except Exception:
                val = ''
            first_values[src] = val

        # Build columns info
        columns_info = []
        for original, norm in zip(original_columns, norm_columns):
            mapped = column_map.get(norm)
            columns_info.append({
                'source': original,
                'normalized': norm,
                'mapped_to': mapped or '',
                'first_value': first_values.get(norm, ''),
                'is_required': (mapped in required) if mapped else False,
                'is_autogenerated': (mapped in autogenerated) if mapped else False,
                'status': 'mapped' if mapped else 'unmapped'
            })

        # Predict potential creates/updates
        potential = {'updates': 0, 'creates': 0, 'unknown': 0}
        try:
            from students.models import Student
            adms = set()
            emails = set()
            if 'admission_number' in work_df.columns:
                adms = set([str(x).strip() for x in work_df['admission_number'].tolist() if str(x).strip()])
            if 'email' in work_df.columns:
                emails = set([str(x).strip() for x in work_df['email'].tolist() if str(x).strip()])
            existing_adm = set()
            existing_email = set()
            if adms:
                existing_adm = set(Student.objects.filter(admission_number__in=list(adms)).values_list('admission_number', flat=True))
            if emails:
                existing_email = set(Student.objects.filter(email__in=list(emails)).values_list('email', flat=True))
            for idx in range(total_rows):
                adm = str(work_df.iloc[idx].get('admission_number', '')).strip() if 'admission_number' in work_df.columns else ''
                eml = str(work_df.iloc[idx].get('email', '')).strip() if 'email' in work_df.columns else ''
                if (adm and adm in existing_adm) or (eml and eml in existing_email):
                    potential['updates'] += 1
                elif adm or eml:
                    potential['creates'] += 1
                else:
                    potential['unknown'] += 1
        except Exception:
            pass

        preview = {
            'success': True,
            'columns': columns_info,
            'missing_required': missing_required,
            'stats': {
                'total_rows': int(total_rows),
                'invalid_rows': int(invalid_rows),
                'valid_rows': int(total_rows - invalid_rows)
            },
            'sample_errors': row_errors[:50],
            'can_import': can_import,
            'potential_actions': potential
        }
        return JsonResponse(preview)

@method_decorator(csrf_exempt, name='dispatch')
class StudentImportView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        f = request.FILES.get('file')
        if not f:
            return JsonResponse({'success': False, 'error': 'No file uploaded'})
        name = f.name.lower()
        try:
            if name.endswith('.csv'):
                df = pd.read_csv(f, dtype=str)
            elif name.endswith('.xlsx'):
                sheet = request.POST.get('sheet_name')
                df = pd.read_excel(f, sheet_name=sheet if sheet else 0, dtype=str)
            else:
                return JsonResponse({'success': False, 'error': 'Unsupported file type'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': f'Failed to read file: {e}'})
        df.columns = [str(c).strip().lower().replace(' ', '_') for c in df.columns]
        df = df.fillna('')
        required = ['first_name', 'last_name', 'date_of_birth', 'gender', 'admission_date', 'current_class', 'current_address', 'city', 'state']
        from academics.models import Class, Section
        from tenants.models import School
        school_slug = kwargs.get('school_slug', '')
        school = School.objects.filter(slug=school_slug, is_active=True).first() if school_slug else None
        success_count = 0
        created_count = 0
        updated_count = 0
        errors = []
        for idx, row in enumerate(df.to_dict(orient='records')):
            try:
                for col in required:
                    if not str(row.get(col, '')).strip():
                        raise ValueError(f'Missing required field: {col}')
                dob = pd.to_datetime(row.get('date_of_birth'), errors='coerce')
                adm_dt = pd.to_datetime(row.get('admission_date'), errors='coerce')
                if pd.isna(dob) or pd.isna(adm_dt):
                    raise ValueError('Invalid date format, use YYYY-MM-DD')
                dob = dob.date()
                adm_dt = adm_dt.date()
                class_name = str(row.get('current_class', '')).strip()
                section_name = str(row.get('section', '')).strip()
                if class_name:
                    if school:
                        current_class = Class.objects.filter(name__iexact=class_name, school=school).first()
                    else:
                        current_class = Class.objects.filter(name__iexact=class_name).first()
                    if not current_class:
                        raise ValueError(f"Class '{class_name}' does not exist for this school")
                else:
                    current_class = None

                if section_name:
                    if not current_class:
                        raise ValueError(f"Cannot assign section '{section_name}' without a valid class")
                    section = Section.objects.filter(name__iexact=section_name, class_name=current_class).first()
                    if not section:
                        raise ValueError(f"Section '{section_name}' does not exist for class '{class_name}'")
                else:
                    section = None
                admission_number = str(row.get('admission_number', '')).strip() or None
                email = str(row.get('email', '')).strip()
                first_name = str(row.get('first_name', '')).strip()
                last_name = str(row.get('last_name', '')).strip()
                if not email:
                    school_slug = get_school_slug_from_request(request)
                    email = generate_email(first_name, last_name, school_slug, 'student')
                student = None
                if admission_number:
                    student = Student.objects.filter(admission_number=admission_number).first()
                if not student and email:
                    student = Student.objects.filter(email=email).first()
                if student and student.user:
                    user = student.user
                else:
                    user = User.objects.filter(email=email, role='student').first()
                    if not user:
                        user = User.objects.create(email=email, first_name=first_name, last_name=last_name, role='student', is_active=True)
                        user.set_password('student123')
                        if school:
                            user.school = school
                        user.save()
                # Ensure imported student's user is linked to this school
                if school and not getattr(user, 'school', None):
                    user.school = school
                    user.save(update_fields=['school'])
                parent_user = None
                father_email = str(row.get('father_email', '')).strip()
                mother_email = str(row.get('mother_email', '')).strip()
                father_name = str(row.get('father_name', '')).strip()
                mother_name = str(row.get('mother_name', '')).strip()
                parent_email = father_email if father_email else mother_email
                parent_full_name = father_name if father_name else mother_name
                parent_first_name = parent_full_name.split()[0] if parent_full_name else ''
                parent_last_name = parent_full_name.split()[-1] if parent_full_name and ' ' in parent_full_name else last_name
                if not parent_email and parent_full_name:
                    school_slug = get_school_slug_from_request(request)
                    parent_email = generate_email(parent_first_name, parent_last_name, school_slug, 'parent')
                if parent_email:
                    parent_user = User.objects.filter(email=parent_email, role='parent').first()
                    if not parent_user:
                        parent_user = User.objects.create(email=parent_email, first_name=parent_first_name or 'Parent', last_name=parent_last_name or last_name, role='parent', phone=row.get('father_phone', '') or row.get('mother_phone', ''), is_active=True)
                        parent_user.set_password('parent123')
                        if school:
                            parent_user.school = school
                        parent_user.save()
                # Ensure imported parent user is linked to this school
                if parent_user and school and not getattr(parent_user, 'school', None):
                    parent_user.school = school
                    parent_user.save(update_fields=['school'])
                data = {
                    'user': user,
                    'first_name': first_name,
                    'last_name': last_name,
                    'email': email,
                    'admission_number': admission_number or Student.generate_admission_number('STU'),
                    'admission_date': adm_dt,
                    'date_of_birth': dob,
                    'gender': str(row.get('gender', '')).strip(),
                    'blood_group': str(row.get('blood_group', '')).strip(),
                    'religion': str(row.get('religion', '')).strip(),
                    'current_address': str(row.get('current_address', '')).strip(),
                    'city': str(row.get('city', '')).strip(),
                    'state': str(row.get('state', '')).strip(),
                    'country': str(row.get('country', 'US')).strip() or 'US',
                    'postal_code': str(row.get('postal_code', '')).strip(),
                    'father_name': father_name,
                    'father_phone': row.get('father_phone', ''),
                    'father_email': father_email,
                    'father_occupation': str(row.get('father_occupation', '')).strip(),
                    'mother_name': mother_name,
                    'mother_phone': row.get('mother_phone', ''),
                    'mother_email': mother_email,
                    'mother_occupation': str(row.get('mother_occupation', '')).strip(),
                    'guardian_name': str(row.get('guardian_name', '')).strip(),
                    'guardian_phone': row.get('guardian_phone', ''),
                    'guardian_email': str(row.get('guardian_email', '')).strip(),
                    'guardian_relation': str(row.get('guardian_relation', '')).strip(),
                    'current_class': current_class,
                    'section': section,
                    'academic_year': (
                        AcademicYear.objects.filter(school=school, is_active=True).first()
                        or AcademicYear.objects.filter(is_active=True).first()
                        or AcademicYear.objects.filter(school=school).order_by('-start_date').first()
                        if school else AcademicYear.objects.filter(is_active=True).first()
                    ),
                    'parent_user': parent_user,
                    'created_by': request.user
                }
                with transaction.atomic():
                    if student:
                        for k, v in data.items():
                            setattr(student, k, v)
                        # Backfill school on existing student if missing
                        if school and not getattr(student, 'school', None):
                            student.school = school
                        student.save()
                        updated_count += 1
                    else:
                        # Ensure new student is linked to this school
                        student = Student.objects.create(**data, school=school)
                        created_count += 1

                    if student and student.current_class and student.academic_year:
                        try:
                            from .models import StudentClassEnrollment
                            status = 'active' if student.is_active else ('completed' if student.is_alumni else 'withdrawn')
                            StudentClassEnrollment.objects.update_or_create(
                                student=student,
                                academic_year=student.academic_year,
                                defaults={
                                    'school': student.school or school,
                                    'class_name': student.current_class,
                                    'section': student.section,
                                    'roll_number': student.roll_number or '',
                                    'status': status,
                                    'enrolled_date': student.admission_date or adm_dt,
                                    'created_by': request.user
                                }
                            )
                        except Exception as e:
                            print(f"[WARNING] Could not sync StudentClassEnrollment in import: {e}")
                success_count += 1
            except Exception as e:
                errors.append({'row': idx + 2, 'error': str(e)})
        return JsonResponse({'success': True, 'imported': success_count, 'created': created_count, 'updated': updated_count, 'errors': len(errors), 'error_rows': errors})


class StudentPromotionView(LoginRequiredMixin, View):
    """View to manage student promotions across classes, sections, and academic years."""
    template_name = 'students/promote.html'

    def dispatch(self, request, *args, **kwargs):
        if not (request.user.is_school_admin or request.user.role in ('admin', 'superadmin', 'teacher')):
            messages.error(request, "Access denied. Only administrators and authorized staff can manage promotions.")
            return redirect('core:dashboard', school_slug=kwargs.get('school_slug'))
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        school_slug = self.kwargs.get('school_slug', '')
        school = get_current_school(request)
        from core.models import AcademicYear
        from academics.models import Class, Section
        from .models import StudentPromotion

        ay_qs = AcademicYear.objects.all().order_by('-start_date')
        classes_qs = Class.objects.filter(is_active=True).order_by('order', 'name')
        sections_qs = Section.objects.filter(is_active=True).order_by('class_name__order', 'name')
        
        if school:
            ay_qs = ay_qs.filter(school=school)
            classes_qs = classes_qs.filter(school=school)
            sections_qs = sections_qs.filter(class_name__school=school)

        active_year = ay_qs.filter(is_active=True).first()
        recent_promotions = StudentPromotion.objects.all().select_related(
            'student', 'from_class', 'to_class', 'from_section', 'to_section',
            'from_academic_year', 'to_academic_year', 'created_by'
        ).order_by('-created_at')

        if school:
            recent_promotions = recent_promotions.filter(
                Q(student__school=school) | Q(from_class__school=school)
            )

        recent_promotions = recent_promotions[:30]

        context = {
            'school_slug': school_slug,
            'school': school,
            'academic_years': ay_qs,
            'active_year': active_year,
            'classes': classes_qs,
            'sections': sections_qs,
            'recent_promotions': recent_promotions,
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        from django.shortcuts import get_object_or_404
        school_slug = self.kwargs.get('school_slug', '')
        school = get_current_school(request)
        from core.models import AcademicYear
        from academics.models import Class, Section
        from .models import Student, StudentPromotion, StudentTimeline
        from django.utils import timezone
        from django.db import IntegrityError

        from_year_id = request.POST.get('from_academic_year')
        to_year_id = request.POST.get('to_academic_year')
        from_class_id = request.POST.get('from_class')
        from_section_id = request.POST.get('from_section') or None
        to_class_id = request.POST.get('to_class')
        to_section_id = request.POST.get('to_section') or None
        remarks = request.POST.get('remarks', '').strip()
        promotion_date_str = request.POST.get('promotion_date')

        promotion_date = timezone.now().date()
        if promotion_date_str:
            try:
                promotion_date = datetime.strptime(promotion_date_str, '%Y-%m-%d').date()
            except ValueError:
                pass

        if not from_year_id or not to_year_id or not from_class_id or not to_class_id:
            messages.error(request, "Please select source and target academic years and classes.")
            return redirect('students:promote', school_slug=school_slug)

        if str(from_year_id) == str(to_year_id):
            messages.error(request, "Source and destination academic years cannot be identical.")
            return redirect('students:promote', school_slug=school_slug)

        from_year = get_object_or_404(AcademicYear, pk=from_year_id)
        to_year = get_object_or_404(AcademicYear, pk=to_year_id)
        from_class = get_object_or_404(Class, pk=from_class_id)
        to_class = get_object_or_404(Class, pk=to_class_id)

        if school:
            if (from_year.school and from_year.school != school) or (to_year.school and to_year.school != school):
                messages.error(request, "Selected academic years do not belong to this school.")
                return redirect('students:promote', school_slug=school_slug)
            if from_class.school != school or to_class.school != school:
                messages.error(request, "Selected classes do not belong to this school.")
                return redirect('students:promote', school_slug=school_slug)

        from_section = Section.objects.filter(pk=from_section_id, class_name=from_class).first() if from_section_id else None
        default_to_section = None
        if to_section_id:
            to_sec_qs = Section.objects.filter(pk=to_section_id, class_name=to_class)
            if school:
                to_sec_qs = to_sec_qs.filter(class_name__school=school)
            default_to_section = to_sec_qs.first()
            if not default_to_section:
                messages.error(request, "Selected destination section does not belong to the destination class or school.")
                return redirect('students:promote', school_slug=school_slug)

        student_ids = request.POST.getlist('student_ids')
        if not student_ids:
            messages.warning(request, "No students were selected for promotion.")
            return redirect('students:promote', school_slug=school_slug)

        promoted_count = 0
        retained_count = 0
        left_count = 0
        skipped_duplicate_count = 0

        with transaction.atomic():
            for sid_str in student_ids:
                try:
                    sid = int(sid_str)
                    stud_qs = Student.objects.select_for_update()
                    if school:
                        stud_qs = stud_qs.filter(school=school)
                    student = stud_qs.get(pk=sid)
                except (ValueError, Student.DoesNotExist):
                    continue

                # Prevent duplicate promotions into the same destination academic year
                if StudentPromotion.objects.filter(student=student, to_academic_year=to_year).exists():
                    skipped_duplicate_count += 1
                    continue

                action = request.POST.get(f'action_{sid}', 'promote')
                override_sec_id = request.POST.get(f'target_section_{sid}')
                target_section = default_to_section
                if override_sec_id:
                    override_sec_qs = Section.objects.filter(pk=override_sec_id, class_name=to_class)
                    if school:
                        override_sec_qs = override_sec_qs.filter(class_name__school=school)
                    target_sec_obj = override_sec_qs.first()
                    if target_sec_obj:
                        target_section = target_sec_obj

                student_from_class = student.current_class or from_class
                student_from_section = student.section or from_section

                try:
                    from .models import StudentClassEnrollment
                    if action == 'promote':
                        promo = StudentPromotion.objects.create(
                            student=student,
                            from_class=student_from_class,
                            from_section=student_from_section,
                            to_class=to_class,
                            to_section=target_section,
                            from_academic_year=from_year,
                            to_academic_year=to_year,
                            promotion_date=promotion_date,
                            remarks=remarks or f"Promoted to {to_class.name}",
                            created_by=request.user
                        )

                        # Mark source year enrollment as completed
                        StudentClassEnrollment.objects.filter(
                            student=student,
                            academic_year=from_year,
                            status='active'
                        ).update(status='completed')

                        # Create destination year enrollment
                        StudentClassEnrollment.objects.update_or_create(
                            student=student,
                            academic_year=to_year,
                            defaults={
                                'school': student.school or school,
                                'class_name': to_class,
                                'section': target_section,
                                'roll_number': student.roll_number or '',
                                'status': 'active',
                                'enrolled_date': promotion_date,
                                'promotion': promo,
                                'remarks': remarks or f"Promoted to {to_class.name}",
                                'created_by': request.user
                            }
                        )

                        student.current_class = to_class
                        student.section = target_section
                        student.academic_year = to_year
                        student.save(update_fields=['current_class', 'section', 'academic_year'])

                        try:
                            StudentTimeline.objects.create(
                                student=student,
                                timeline_type='promotion',
                                title=f"Promoted to {to_class.name}",
                                description=f"Promoted from {student_from_class.name} to {to_class.name}" + (f" ({target_section.name})" if target_section else "") + f" for academic year {to_year.name}.",
                                date=promotion_date,
                                created_by=request.user
                            )
                        except Exception:
                            pass
                        promoted_count += 1

                    elif action == 'repeat':
                        promo = StudentPromotion.objects.create(
                            student=student,
                            from_class=student_from_class,
                            from_section=student_from_section,
                            to_class=student_from_class,
                            to_section=student_from_section,
                            from_academic_year=from_year,
                            to_academic_year=to_year,
                            promotion_date=promotion_date,
                            remarks=remarks or f"Retained in {student_from_class.name}",
                            created_by=request.user
                        )

                        # Mark source year enrollment as repeated
                        StudentClassEnrollment.objects.filter(
                            student=student,
                            academic_year=from_year,
                            status='active'
                        ).update(status='repeated')

                        # Create destination year enrollment in current class
                        StudentClassEnrollment.objects.update_or_create(
                            student=student,
                            academic_year=to_year,
                            defaults={
                                'school': student.school or school,
                                'class_name': student_from_class,
                                'section': student_from_section,
                                'roll_number': student.roll_number or '',
                                'status': 'active',
                                'enrolled_date': promotion_date,
                                'promotion': promo,
                                'remarks': remarks or f"Retained in {student_from_class.name}",
                                'created_by': request.user
                            }
                        )

                        student.academic_year = to_year
                        student.save(update_fields=['academic_year'])

                        try:
                            StudentTimeline.objects.create(
                                student=student,
                                timeline_type='promotion',
                                title=f"Retained in {student_from_class.name}",
                                description=f"Retained in {student_from_class.name} for academic year {to_year.name}.",
                                date=promotion_date,
                                created_by=request.user
                            )
                        except Exception:
                            pass
                        retained_count += 1

                    elif action == 'leave':
                        # Mark source year enrollment as withdrawn
                        StudentClassEnrollment.objects.filter(
                            student=student,
                            academic_year=from_year,
                            status='active'
                        ).update(status='withdrawn')

                        student.is_active = False
                        student.is_alumni = True
                        student.leaving_date = promotion_date
                        student.leaving_reason = remarks or 'Graduated / Left school'
                        student.save(update_fields=['is_active', 'is_alumni', 'leaving_date', 'leaving_reason'])

                        try:
                            StudentTimeline.objects.create(
                                student=student,
                                timeline_type='promotion',
                                title="Graduated / Left School",
                                description=remarks or f"Left school after completing {student_from_class.name}.",
                                date=promotion_date,
                                created_by=request.user
                            )
                        except Exception:
                            pass
                        left_count += 1
                except IntegrityError:
                    skipped_duplicate_count += 1
                    continue

        summary_msg = []
        if promoted_count:
            summary_msg.append(f"{promoted_count} promoted to {to_class.name}")
        if retained_count:
            summary_msg.append(f"{retained_count} retained in {from_class.name}")
        if left_count:
            summary_msg.append(f"{left_count} graduated/left")
        if skipped_duplicate_count:
            summary_msg.append(f"{skipped_duplicate_count} skipped (already promoted/processed for {to_year.name})")

        messages.success(request, f"Promotion processed successfully: {', '.join(summary_msg) if summary_msg else 'Done'}.")
        return redirect('students:promote', school_slug=school_slug)


def get_promotion_students_api(request, school_slug=None):
    """API endpoint to fetch eligible students for promotion based on class & section."""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Authentication required'}, status=401)

    class_id = request.GET.get('class_id')
    section_id = request.GET.get('section_id')
    school = get_current_school(request)

    if not class_id or not str(class_id).isdigit():
        return JsonResponse({'success': False, 'students': []})

    from .models import Student
    qs = Student.objects.filter(current_class_id=int(class_id), is_active=True).select_related('section', 'current_class')

    if section_id and str(section_id).isdigit():
        qs = qs.filter(section_id=int(section_id))

    if school:
        qs = qs.filter(school=school)

    qs = qs.order_by('first_name', 'last_name')

    students_data = []
    for s in qs:
        photo_url = s.photo.url if s.photo else None
        students_data.append({
            'id': s.id,
            'admission_number': s.admission_number,
            'full_name': s.get_full_name(),
            'roll_number': s.roll_number or '',
            'current_class': s.current_class.name if s.current_class else '',
            'current_section': s.section.name if s.section else '',
            'current_section_id': s.section_id or '',
            'photo': photo_url,
        })

    return JsonResponse({
        'success': True,
        'count': len(students_data),
        'students': students_data,
    })


class StudentPromotionHistoryView(LoginRequiredMixin, ListView):
    """View to browse and filter student promotion history."""
    template_name = 'students/promotion_history.html'
    context_object_name = 'promotions'
    paginate_by = 30

    def dispatch(self, request, *args, **kwargs):
        if not (request.user.is_school_admin or request.user.role in ('admin', 'superadmin', 'teacher')):
            messages.error(request, "Access denied.")
            return redirect('core:dashboard', school_slug=kwargs.get('school_slug'))
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        from .models import StudentPromotion
        school = get_current_school(self.request)
        qs = StudentPromotion.objects.all().select_related(
            'student', 'from_class', 'to_class', 'from_section', 'to_section',
            'from_academic_year', 'to_academic_year', 'created_by'
        )

        if school:
            qs = qs.filter(Q(student__school=school) | Q(from_class__school=school))

        ay = self.request.GET.get('academic_year')
        if ay and str(ay).isdigit():
            qs = qs.filter(to_academic_year_id=int(ay))

        cls = self.request.GET.get('class_id')
        if cls and str(cls).isdigit():
            qs = qs.filter(to_class_id=int(cls))

        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(student__first_name__icontains=q) |
                Q(student__last_name__icontains=q) |
                Q(student__admission_number__icontains=q)
            )

        return qs.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        school = get_current_school(self.request)
        school_slug = self.kwargs.get('school_slug', '')
        context['school_slug'] = school_slug

        from core.models import AcademicYear
        from academics.models import Class

        ay_qs = AcademicYear.objects.all().order_by('-start_date')
        cls_qs = Class.objects.filter(is_active=True).order_by('order', 'name')
        if school:
            ay_qs = ay_qs.filter(school=school)
            cls_qs = cls_qs.filter(school=school)

        context['academic_years'] = ay_qs
        context['classes'] = cls_qs
        context['selected_year'] = self.request.GET.get('academic_year', '')
        context['selected_class'] = self.request.GET.get('class_id', '')
        context['search_query'] = self.request.GET.get('q', '')
        return context


class PlatformSchoolsApiView(LoginRequiredMixin, View):
    """Return list of other active tenant schools for electronic transfer"""
    def get(self, request, *args, **kwargs):
        current_school = get_current_school(request)
        schools_qs = School.objects.filter(is_active=True)
        if current_school:
            schools_qs = schools_qs.exclude(pk=current_school.pk)
        
        data = [
            {'id': s.id, 'name': s.name, 'slug': s.slug}
            for s in schools_qs.order_by('name')
        ]
        return JsonResponse({'success': True, 'schools': data})


class StudentExitView(LoginRequiredMixin, View):
    """
    Handle student transfer, withdrawal, and exit workflows.
    Supports:
    - External school transfer
    - Electronic push to another school on the Clasyo platform
    - Family relocation, graduation/alumni, expulsion, health, or other exit reasons
    - Optional automated Transfer Certificate (TC) generation
    - Preserves all historical financial & academic records
    """
    def post(self, request, pk, *args, **kwargs):
        try:
            school = get_current_school(request)
            qs = Student.objects.all()
            if school:
                qs = qs.filter(school=school)
            
            student = get_object_or_404(qs, pk=pk)
            
            if getattr(student, 'is_sample_data', False):
                return JsonResponse({'success': False, 'error': 'Sample/Demo data cannot be modified.'})

            exit_type = request.POST.get('exit_type', 'other').strip()
            leaving_date_str = request.POST.get('leaving_date', '').strip()
            destination_school = request.POST.get('destination_school', '').strip()
            target_school_id = request.POST.get('target_school_id', '').strip()
            exit_remarks = request.POST.get('exit_remarks', '').strip()
            generate_tc = request.POST.get('generate_tc') in ('1', 'true', 'on', 'yes')

            from django.utils.dateparse import parse_date
            leaving_date = parse_date(leaving_date_str) if leaving_date_str else timezone.now().date()
            if not leaving_date:
                leaving_date = timezone.now().date()

            target_school = None
            if exit_type == 'transfer_platform' and target_school_id and str(target_school_id).isdigit():
                try:
                    target_school = School.objects.get(pk=int(target_school_id), is_active=True)
                    destination_school = target_school.name
                except School.DoesNotExist:
                    return JsonResponse({'success': False, 'error': 'Selected destination school was not found.'})

            # Exit type human label
            exit_labels = {
                'transfer_external': 'Transferred to External School',
                'transfer_platform': f'Transferred to {destination_school}',
                'relocation': 'Family Relocation',
                'graduation': 'Graduated / Completed Studies',
                'financial': 'Financial Reasons',
                'expulsion': 'Disciplinary / Expulsion',
                'medical': 'Medical / Health Reasons',
                'other': 'Left School'
            }
            exit_label = exit_labels.get(exit_type, 'Left School')
            full_leaving_reason = f"{exit_label}. Destination: {destination_school}." if destination_school else exit_label
            if exit_remarks:
                full_leaving_reason += f" Remarks: {exit_remarks}"

            # 1. Update Student in current school (soft deactivation for audit integrity)
            student.is_active = False
            student.leaving_date = leaving_date
            student.leaving_reason = full_leaving_reason
            student.exit_type = exit_type
            student.destination_school = destination_school
            student.exit_remarks = exit_remarks
            if target_school:
                student.transfer_target_school = target_school
            if exit_type == 'graduation':
                student.is_alumni = True
                student.enrollment_status = 'graduated'
            elif 'transfer' in exit_type:
                student.enrollment_status = 'transferred'
            else:
                student.enrollment_status = 'withdrawn'

            student.save(update_fields=[
                'is_active', 'leaving_date', 'leaving_reason', 'exit_type',
                'destination_school', 'exit_remarks', 'transfer_target_school', 'is_alumni', 'enrollment_status'
            ])

            # Deactivate login
            if student.user:
                student.user.is_active = False
                student.user.save(update_fields=['is_active'])

            # Deactivate dormitory/room allocation
            if hasattr(student, 'room_allocation'):
                try:
                    ra = student.room_allocation
                    ra.is_active = False
                    ra.save()
                except Exception:
                    pass

            # Update active Class Enrollment
            enrollment_status = 'transferred' if 'transfer' in exit_type else ('completed' if exit_type == 'graduation' else 'withdrawn')
            StudentClassEnrollment.objects.filter(
                student=student,
                status='active'
            ).update(status=enrollment_status)

            # Log to StudentTimeline
            try:
                StudentTimeline.objects.create(
                    student=student,
                    timeline_type='transfer' if 'transfer' in exit_type else 'status_change',
                    title=exit_label,
                    description=full_leaving_reason,
                    date=leaving_date,
                    created_by=request.user
                )
            except Exception:
                pass

            # Optional: Generate Transfer Certificate
            tc_data = None
            if generate_tc or exit_type == 'transfer_platform':
                try:
                    from certificates.models import CertificateType, Certificate
                    cert_type, _ = CertificateType.objects.get_or_create(
                        code='TC',
                        defaults={
                            'name': 'Transfer Certificate',
                            'category': 'completion',
                            'description': 'Official School Transfer Certificate',
                            'school': school,
                        }
                    )
                    tc_cert = Certificate.objects.create(
                        certificate_type=cert_type,
                        student=student,
                        title=f"Transfer Certificate - {student.get_full_name()}",
                        issue_date=leaving_date,
                        academic_year=student.academic_year,
                        class_name=student.current_class,
                        description=f"This is to certify that {student.get_full_name()} was enrolled in {student.current_class.name if student.current_class else 'our school'}. Reason for leaving: {full_leaving_reason}.",
                        remarks=exit_remarks,
                        created_by=request.user
                    )
                    student.transfer_certificate_number = tc_cert.certificate_number
                    student.save(update_fields=['transfer_certificate_number'])
                    tc_data = {
                        'id': tc_cert.id,
                        'certificate_number': tc_cert.certificate_number,
                        'view_url': reverse('certificates:view', kwargs={'school_slug': school.slug if school else 'default', 'pk': tc_cert.id}),
                        'download_url': reverse('certificates:download', kwargs={'school_slug': school.slug if school else 'default', 'pk': tc_cert.id})
                    }
                except Exception as ce:
                    print("Could not auto-generate TC:", ce)

            # 2. Automated Multi-School Electronic Push (Platform Transfer)
            target_created = False
            target_adm_no = ''
            new_student_id = None
            if exit_type == 'transfer_platform' and target_school:
                try:
                    # Check if student already exists in destination school
                    exists_in_target = Student.objects.filter(
                        school=target_school,
                        first_name__iexact=student.first_name,
                        last_name__iexact=student.last_name,
                        date_of_birth=student.date_of_birth
                    ).first()

                    if not exists_in_target:
                        # Find latest active year in target school
                        from core.models import AcademicYear, Notification
                        target_ay = AcademicYear.objects.filter(school=target_school, is_active=True).first()
                        if not target_ay:
                            target_ay = AcademicYear.objects.filter(school=target_school).order_by('-start_date').first()

                        # Generate admission number for target school
                        target_prefix = (target_school.slug[:3] if target_school.slug else 'STU').upper()
                        target_adm_no = Student.generate_admission_number(prefix=target_prefix)

                        new_student = Student.objects.create(
                            school=target_school,
                            admission_number=target_adm_no,
                            first_name=student.first_name,
                            last_name=student.last_name,
                            date_of_birth=student.date_of_birth,
                            gender=student.gender,
                            blood_group=student.blood_group,
                            religion=student.religion,
                            nationality=student.nationality,
                            address=student.address,
                            city=student.city,
                            state=student.state,
                            country=student.country,
                            postal_code=student.postal_code,
                            admission_date=leaving_date,
                            academic_year=target_ay,
                            previous_school=school.name if school else "Previous School",
                            previous_class=student.current_class.name if student.current_class else "",
                            transfer_certificate_number=student.transfer_certificate_number or "",
                            father_name=student.father_name,
                            father_phone=student.father_phone,
                            father_email=student.father_email,
                            father_occupation=student.father_occupation,
                            mother_name=student.mother_name,
                            mother_phone=student.mother_phone,
                            mother_email=student.mother_email,
                            mother_occupation=student.mother_occupation,
                            guardian_name=student.guardian_name,
                            guardian_phone=student.guardian_phone,
                            guardian_email=student.guardian_email,
                            guardian_relation=student.guardian_relation,
                            guardian_occupation=student.guardian_occupation,
                            guardian_address=student.guardian_address,
                            medical_history=student.medical_history,
                            allergies=student.allergies,
                            disabilities=student.disabilities,
                            current_medications=student.current_medications,
                            is_active=True,
                            created_by=request.user
                        )
                        if student.photo:
                            new_student.photo = student.photo
                            new_student.save(update_fields=['photo'])

                        # Target timeline entry
                        StudentTimeline.objects.create(
                            student=new_student,
                            timeline_type='transfer',
                            title=f"Electronic Transfer from {school.name if school else 'Partner School'}",
                            description=f"Student profile transferred electronically. Prior class: {student.current_class.name if student.current_class else 'N/A'}. TC No: {student.transfer_certificate_number or 'N/A'}. Pending class assignment.",
                            date=leaving_date,
                            created_by=request.user
                        )

                        # Notify target school admins
                        target_admins = User.objects.filter(school=target_school, role__in=['admin', 'school_admin'])
                        for admin in target_admins:
                            Notification.objects.create(
                                user=admin,
                                title="Incoming Student Transfer",
                                message=f"Student {new_student.get_full_name()} has transferred from {school.name if school else 'another school'}. Please assign class and section.",
                                notification_type="info",
                                link=f"/school/{target_school.slug}/students/{new_student.pk}/"
                            )

                        target_created = True
                        new_student_id = new_student.id
                except Exception as pe:
                    import traceback
                    traceback.print_exc()

            response_msg = f"Student {student.get_full_name()} has been successfully marked as exited ({exit_label})."
            if target_created:
                response_msg += f" Profile electronically created in {target_school.name} (Admission #{target_adm_no})."

            return JsonResponse({
                'success': True,
                'message': response_msg,
                'tc': tc_data,
                'target_created': target_created,
                'new_student_id': new_student_id
            })

        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'success': False, 'error': str(e)}, status=500)


class StudentStatusUpdateView(LoginRequiredMixin, View):
    """Update or transition a student's enrollment status (e.g. Pending -> Enrolled)."""
    def post(self, request, pk, *args, **kwargs):
        try:
            school = get_current_school(request)
            qs = Student.objects.all()
            if school:
                qs = qs.filter(school=school)
            student = get_object_or_404(qs, pk=pk)

            new_status = request.POST.get('status', '').strip().lower()
            if new_status not in ('enrolled', 'pending', 'transferred', 'withdrawn', 'graduated'):
                return JsonResponse({'success': False, 'error': f'Invalid status: {new_status}'})

            if new_status == 'enrolled':
                student.confirm_enrollment(enrolled_by=request.user)
            else:
                student.enrollment_status = new_status
                if new_status == 'pending':
                    student.is_active = True
                    student.is_alumni = False
                elif new_status in ('transferred', 'withdrawn', 'graduated'):
                    student.is_active = False
                    if new_status == 'graduated':
                        student.is_alumni = True
                student.save()

            is_ajax = (
                request.headers.get('x-requested-with') == 'XMLHttpRequest' or
                'application/json' in request.headers.get('accept', '') or
                request.content_type == 'application/json'
            )
            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'student_id': student.pk,
                    'enrollment_status': student.enrollment_status,
                    'status_display': student.get_enrollment_status_display(),
                    'message': f"Student status successfully updated to {student.get_enrollment_status_display()}."
                })
            messages.success(request, f"Student status successfully updated to {student.get_enrollment_status_display()}.")
            return redirect('students:list', school_slug=school.slug if school else kwargs.get('school_slug'))
        except Exception as e:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': str(e)}, status=500)
            messages.error(request, f"Error updating student status: {e}")
            return redirect('students:list', school_slug=kwargs.get('school_slug'))


class StudentBulkConfirmEnrollmentView(LoginRequiredMixin, View):
    """Bulk confirm enrollment for multiple pending students."""
    def post(self, request, *args, **kwargs):
        try:
            school = get_current_school(request)
            ids = request.POST.getlist('ids[]') or request.POST.getlist('ids') or request.POST.getlist('selected_ids')
            if not ids:
                try:
                    data = json.loads(request.body.decode('utf-8'))
                    ids = data.get('ids', [])
                except Exception:
                    ids = []

            if not ids:
                return JsonResponse({'success': False, 'error': 'No students selected for enrollment confirmation.'})

            qs = Student.objects.filter(id__in=ids)
            if school:
                qs = qs.filter(school=school)

            confirmed_count = 0
            for student in qs:
                student.confirm_enrollment(enrolled_by=request.user)
                confirmed_count += 1

            return JsonResponse({
                'success': True,
                'confirmed_count': confirmed_count,
                'message': f"Successfully confirmed enrollment for {confirmed_count} student(s)."
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

