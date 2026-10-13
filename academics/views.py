from django.shortcuts import render, redirect
from django.views.generic import ListView, CreateView, UpdateView, DetailView, DeleteView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q, Prefetch
from core.utils import get_current_school
from core.models import AcademicYear
from .models import Class, Section, Subject, ClassRoutine, ClassTime, ClassRoom, StudyMaterial, Assignment, AssignedSubject, Syllabus
from accounts.models import User
from tenants.models import School
import json
import logging
from datetime import datetime, time

logger = logging.getLogger(__name__)
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
import openpyxl
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment


def get_allowed_education_level_choices_for_school(school):
    """Return education_level choices filtered by school.institution_type."""
    # Default: all choices
    base_choices = Class.EDUCATION_LEVEL_CHOICES
    if not school or not getattr(school, 'institution_type', None):
        return base_choices

    institution_type = school.institution_type
    allowed_keys_by_type = {
        'pre_primary_primary': ['pre_primary', 'lower_primary', 'upper_primary'],
        'primary_junior_secondary': ['lower_primary', 'upper_primary', 'junior_secondary'],
        'junior_secondary_only': ['junior_secondary'],
        'senior_secondary': ['senior_secondary'],
        'tvet_college': ['tvet', 'college'],
        # 'mixed' and 'unspecified' fall back to all levels
    }

    allowed_keys = allowed_keys_by_type.get(
        institution_type,
        [value for value, _ in base_choices],
    )
    return [choice for choice in base_choices if choice[0] in allowed_keys]


def ensure_default_class_times_for_school(school):
    if not school:
        return

    if ClassTime.objects.filter(school=school).exists():
        return

    defaults = [
        ("Assembly / Class meeting / PPI", time(7, 0), time(8, 20), False),
        ("Period 1", time(8, 20), time(9, 0), False),
        ("Period 2", time(9, 0), time(9, 40), False),
        ("Morning Break", time(9, 40), time(9, 55), True),
        ("Period 3", time(10, 0), time(10, 40), False),
        ("Period 4", time(10, 40), time(11, 20), False),
        ("Long Break", time(11, 20), time(11, 50), True),
        ("Period 5", time(11, 50), time(12, 30), False),
        ("Period 6", time(12, 30), time(13, 10), False),
        ("Lunch", time(13, 10), time(14, 10), True),
        ("Period 7", time(14, 10), time(14, 50), False),
        ("Period 8", time(14, 50), time(15, 30), False),
        ("Period 9", time(15, 30), time(16, 10), False),
        ("Games / Clubs / Societies / Career activities", time(16, 0), time(17, 0), False),
    ]

    objs = []
    order = 1
    for name, start_t, end_t, is_break in defaults:
        objs.append(
            ClassTime(
                school=school,
                name=name,
                start_time=start_t,
                end_time=end_t,
                is_break=is_break,
                order=order,
                is_active=True,
            )
        )
        order += 1

    ClassTime.objects.bulk_create(objs)


class ClassListView(LoginRequiredMixin, ListView):
    model = Class
    template_name = 'academics/class_list.html'
    context_object_name = 'classes'
    
    def get_queryset(self):
        queryset = super().get_queryset()
        school_slug = self.kwargs.get('school_slug', '')
        school = None
        if school_slug:
            school = School.objects.filter(slug=school_slug, is_active=True).first()
        if school:
            queryset = queryset.filter(school=school)
        education_level = self.request.GET.get('education_level')
        if education_level:
            queryset = queryset.filter(education_level=education_level)
        return queryset.prefetch_related('sections')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        school_slug = self.kwargs.get('school_slug', '')
        context['school_slug'] = school_slug

        school = None
        if school_slug:
            try:
                school = School.objects.get(slug=school_slug, is_active=True)
            except School.DoesNotExist:
                school = None

        context['school'] = school
        context['education_level_choices'] = get_allowed_education_level_choices_for_school(school)
        context['selected_education_level'] = self.request.GET.get('education_level', '')

        # Preload teachers for the school so frontend doesn't need to make extra AJAX calls
        try:
            teachers_qs = User.objects.filter(role='teacher', is_active=True)
            if school:
                teachers_qs = teachers_qs.filter(school=school)
            teachers_list = [
                {'id': t.id, 'name': (t.get_full_name().strip() if t.get_full_name() else '') or t.email or f"Teacher #{t.id}"}
                for t in teachers_qs
            ]
        except Exception as e:
            teachers_list = []
        context['teachers_json'] = json.dumps(teachers_list)
        return context


def _save_sections_for_class(class_obj, section_names, section_capacities, section_teachers, tenant_db=None):
    """
    Saves or updates sections for a class, safely coercing inputs and ensuring
    foreign keys (like class_teacher) resolve without integrity errors.
    """
    from accounts.models import User
    from tenants.school_sync import sync_tenant_user_by_id
    from tenants.threadlocals import get_current_tenant_db

    tenant_db = tenant_db or get_current_tenant_db() or (class_obj.school.slug if class_obj.school else 'default')
    processed_section_ids = set()

    for i, raw_name in enumerate(section_names):
        name = (raw_name or '').strip()
        if not name:
            continue

        # Coerce capacity safely
        capacity = 40
        if i < len(section_capacities):
            cap_val = section_capacities[i]
            if cap_val not in (None, '', 'null', 'None'):
                try:
                    capacity = max(1, int(cap_val))
                except (ValueError, TypeError):
                    capacity = 40

        # Coerce teacher ID safely
        teacher_id = None
        if i < len(section_teachers):
            t_val = section_teachers[i]
            if t_val not in (None, '', 'null', 'None'):
                try:
                    teacher_id = int(t_val)
                except (ValueError, TypeError):
                    teacher_id = None

        # Verify teacher exists and sync to tenant DB if needed
        if teacher_id:
            try:
                sync_tenant_user_by_id(teacher_id, db_alias=tenant_db)
            except Exception as e:
                logger.warning(f"Could not sync teacher {teacher_id} for section {name}: {e}")

            # Check if teacher exists in tenant DB before assigning FK
            try:
                if not User.objects.using(tenant_db).filter(pk=teacher_id).exists():
                    logger.warning(f"Teacher {teacher_id} not present in tenant DB {tenant_db}, omitting FK.")
                    teacher_id = None
            except Exception:
                teacher_id = None

        section, _ = Section.objects.using(tenant_db).update_or_create(
            class_name=class_obj,
            name=name,
            defaults={
                'max_students': capacity,
                'class_teacher_id': teacher_id,
                'is_active': True,
            }
        )
        processed_section_ids.add(section.id)

        try:
            from academics.models import assign_class_teacher
            teacher_obj = User.objects.using(tenant_db).get(pk=teacher_id) if teacher_id else None
            assign_class_teacher(section, teacher_obj)
        except Exception as e:
            logger.warning(f"Could not sync ClassTeacherAssignment for section {section.name}: {e}")

    # For any existing sections belonging to this class that were not in the submitted list:
    # Safely deactivate them or delete if no dependents exist
    existing_sections = Section.objects.using(tenant_db).filter(class_name=class_obj)
    for existing in existing_sections:
        if existing.id not in processed_section_ids:
            try:
                existing.delete()
            except Exception as e:
                logger.info(f"Could not delete orphaned section {existing.name} (has dependencies), deactivating instead: {e}")
                existing.is_active = False
                existing.save(using=tenant_db, update_fields=['is_active'])


class ClassCreateView(LoginRequiredMixin, CreateView):
    model = Class
    template_name = 'academics/class_form.html'
    fields = ['name', 'numeric_name', 'description', 'order', 'is_active', 'education_level']
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        school_slug = self.kwargs.get('school_slug', '')
        school = None
        if school_slug:
            try:
                school = School.objects.get(slug=school_slug, is_active=True)
            except School.DoesNotExist:
                school = None
        choices = get_allowed_education_level_choices_for_school(school)
        if not any(c[0] == 'unspecified' for c in choices):
            choices = [('unspecified', 'Unspecified')] + list(choices)
        form.fields['education_level'].choices = choices
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        school_slug = self.kwargs.get('school_slug', '')
        context['school_slug'] = school_slug

        school = None
        if school_slug:
            try:
                school = School.objects.get(slug=school_slug, is_active=True)
            except School.DoesNotExist:
                school = None

        context['school'] = school
        context['education_level_choices'] = get_allowed_education_level_choices_for_school(school)
        return context
    
    def get_success_url(self):
        return reverse('academics:class_list', kwargs={'school_slug': self.kwargs.get('school_slug')})
    
    def form_valid(self, form):
        school_slug = self.kwargs.get('school_slug', '')
        school = None
        if school_slug:
            school = School.objects.filter(slug=school_slug, is_active=True).first()
        if school:
            form.instance.school = school

        is_ajax = (
            self.request.headers.get('x-requested-with') == 'XMLHttpRequest' or
            self.request.headers.get('accept', '').find('application/json') != -1
        )

        try:
            with transaction.atomic():
                self.object = form.save()
                
                section_names = self.request.POST.getlist('sections[]')
                section_capacities = self.request.POST.getlist('section_capacity[]')
                section_teachers = self.request.POST.getlist('section_teacher[]')
                
                _save_sections_for_class(
                    class_obj=self.object,
                    section_names=section_names,
                    section_capacities=section_capacities,
                    section_teachers=section_teachers
                )
        except Exception as e:
            logger.exception(f"Error creating class: {e}")
            if is_ajax:
                return JsonResponse({'success': False, 'error': str(e)}, status=400)
            form.add_error(None, str(e))
            return self.form_invalid(form)

        if is_ajax:
            return JsonResponse({'success': True, 'id': self.object.pk})
        
        return super().form_valid(form)

    def form_invalid(self, form):
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'errors': form.errors}, status=400)
        return super().form_invalid(form)


class ClassUpdateView(LoginRequiredMixin, UpdateView):
    model = Class
    template_name = 'academics/class_form.html'
    fields = ['name', 'numeric_name', 'description', 'order', 'is_active', 'education_level']
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        school_slug = self.kwargs.get('school_slug', '')
        school = None
        if school_slug:
            try:
                school = School.objects.get(slug=school_slug, is_active=True)
            except School.DoesNotExist:
                school = None
        choices = get_allowed_education_level_choices_for_school(school)
        if not any(c[0] == 'unspecified' for c in choices):
            choices = [('unspecified', 'Unspecified')] + list(choices)
        form.fields['education_level'].choices = choices
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        school_slug = self.kwargs.get('school_slug', '')
        context['school_slug'] = school_slug

        school = None
        if school_slug:
            try:
                school = School.objects.get(slug=school_slug, is_active=True)
            except School.DoesNotExist:
                school = None

        context['school'] = school
        context['education_level_choices'] = get_allowed_education_level_choices_for_school(school)
        return context
    
    def get_success_url(self):
        return reverse('academics:class_list', kwargs={'school_slug': self.kwargs.get('school_slug')})
    
    def form_valid(self, form):
        is_ajax = (
            self.request.headers.get('x-requested-with') == 'XMLHttpRequest' or
            self.request.headers.get('accept', '').find('application/json') != -1
        )

        try:
            with transaction.atomic():
                self.object = form.save()
                
                section_names = self.request.POST.getlist('sections[]')
                section_capacities = self.request.POST.getlist('section_capacity[]')
                section_teachers = self.request.POST.getlist('section_teacher[]')
                
                _save_sections_for_class(
                    class_obj=self.object,
                    section_names=section_names,
                    section_capacities=section_capacities,
                    section_teachers=section_teachers
                )
        except Exception as e:
            logger.exception(f"Error updating class: {e}")
            if is_ajax:
                return JsonResponse({'success': False, 'error': str(e)}, status=400)
            form.add_error(None, str(e))
            return self.form_invalid(form)

        if is_ajax:
            return JsonResponse({'success': True, 'id': self.object.pk})
        
        return super().form_valid(form)

    def form_invalid(self, form):
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'errors': form.errors}, status=400)
        return super().form_invalid(form)


class ClassDeleteView(LoginRequiredMixin, DeleteView):
    model = Class
    
    def post(self, request, *args, **kwargs):
        try:
            class_obj = self.get_object()
            class_obj.delete()
            return JsonResponse({'success': True, 'message': 'Class deleted successfully'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})


class ClassSubjectAssignmentsView(LoginRequiredMixin, View):
    template_name = 'academics/class_subjects.html'

    def _get_active_year(self, school):
        from core.models import AcademicYear

        qs = AcademicYear.objects.filter(is_active=True)
        if school:
            qs = qs.filter(school=school)
        return qs.first()

    def get(self, request, *args, **kwargs):
        school_slug = self.kwargs.get('school_slug', '')
        return redirect('academics:subject_list', school_slug=school_slug)

    def post(self, request, *args, **kwargs):
        school_slug = self.kwargs.get('school_slug', '')
        return redirect('academics:subject_list', school_slug=school_slug)


def get_class_api(request, pk, school_slug=None):
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Authentication required'}, status=401)
    try:
        class_obj = Class.objects.get(pk=pk)
        sections = list(class_obj.sections.values('id', 'name', 'max_students', 'class_teacher_id'))
        return JsonResponse({
            'success': True,
            'id': class_obj.id,
            'name': class_obj.name,
            'numeric_name': class_obj.numeric_name,
            'description': class_obj.description,
            'order': class_obj.order,
            'is_active': class_obj.is_active,
            'education_level': class_obj.education_level,
            'education_level_display': class_obj.get_education_level_display(),
            'sections': sections,
        })
    except Class.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Class not found'}, status=404)


class SectionListView(LoginRequiredMixin, ListView):
    model = Section
    template_name = 'academics/section_list.html'
    context_object_name = 'sections'
    
    def get_queryset(self):
        school = get_current_school(self.request)
        qs = Section.objects.filter(is_active=True)
        if school:
            qs = qs.filter(class_name__school=school)
        return qs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        school_slug = self.kwargs.get('school_slug', '')
        school = School.objects.filter(slug=school_slug, is_active=True).first() if school_slug else None
        if school:
            context['classes'] = Class.objects.filter(is_active=True, school=school)
        else:
            context['classes'] = Class.objects.filter(is_active=True)
        return context


class SectionCreateView(LoginRequiredMixin, CreateView):
    model = Section
    template_name = 'academics/section_form.html'
    fields = ['class_name', 'name', 'max_students', 'class_teacher', 'room', 'is_active']
    success_url = reverse_lazy('academics:section_list')
    
    def post(self, request, *args, **kwargs):
        try:
            from tenants.school_sync import sync_tenant_user_by_id

            class_id = request.POST.get('class_name')
            name = (request.POST.get('name') or '').strip()
            if not class_id or not name:
                return JsonResponse({'success': False, 'error': 'Class and section name are required.'}, status=400)

            cap_raw = request.POST.get('max_students')
            try:
                max_students = max(1, int(cap_raw)) if cap_raw else 40
            except (ValueError, TypeError):
                max_students = 40

            teacher_raw = request.POST.get('class_teacher')
            teacher_id = None
            if teacher_raw not in (None, '', 'null', 'None'):
                try:
                    teacher_id = int(teacher_raw)
                    sync_tenant_user_by_id(teacher_id)
                except (ValueError, TypeError):
                    teacher_id = None

            room_raw = request.POST.get('room')
            room_id = None
            if room_raw not in (None, '', 'null', 'None'):
                try:
                    room_id = int(room_raw)
                except (ValueError, TypeError):
                    room_id = None

            section = Section.objects.create(
                class_name_id=class_id,
                name=name,
                max_students=max_students,
                class_teacher_id=teacher_id,
                room_id=room_id,
                is_active=request.POST.get('is_active') in ('on', 'true', True)
            )
            if teacher_id:
                try:
                    from academics.models import assign_class_teacher
                    assign_class_teacher(section, section.class_teacher)
                except Exception as ex:
                    logger.warning(f"Could not assign class teacher on create: {ex}")

            return JsonResponse({'success': True, 'id': section.id})
        except Exception as e:
            logger.exception(f"Error creating section: {e}")
            return JsonResponse({'success': False, 'error': str(e)}, status=400)


class SectionUpdateView(LoginRequiredMixin, UpdateView):
    model = Section
    fields = ['class_name', 'name', 'max_students', 'class_teacher', 'room', 'is_active']
    
    def post(self, request, *args, **kwargs):
        try:
            from tenants.school_sync import sync_tenant_user_by_id

            section = self.get_object()
            if request.POST.get('class_name'):
                section.class_name_id = request.POST.get('class_name')
            if request.POST.get('name'):
                section.name = request.POST.get('name').strip()
            
            cap_raw = request.POST.get('max_students')
            if cap_raw is not None:
                try:
                    section.max_students = max(1, int(cap_raw)) if cap_raw else 40
                except (ValueError, TypeError):
                    section.max_students = 40
            
            teacher_changed = False
            if 'class_teacher' in request.POST:
                teacher_changed = True
                teacher_raw = request.POST.get('class_teacher')
                if teacher_raw in (None, '', 'null', 'None'):
                    section.class_teacher_id = None
                else:
                    try:
                        t_id = int(teacher_raw)
                        sync_tenant_user_by_id(t_id)
                        section.class_teacher_id = t_id
                    except (ValueError, TypeError):
                        section.class_teacher_id = None

            if 'room' in request.POST:
                room_raw = request.POST.get('room')
                if room_raw in (None, '', 'null', 'None'):
                    section.room_id = None
                else:
                    try:
                        section.room_id = int(room_raw)
                    except (ValueError, TypeError):
                        section.room_id = None

            if 'is_active' in request.POST:
                section.is_active = request.POST.get('is_active') in ('on', 'true', True)

            section.save()

            if teacher_changed:
                try:
                    from academics.models import assign_class_teacher
                    assign_class_teacher(section, section.class_teacher)
                except Exception as ex:
                    logger.warning(f"Could not sync ClassTeacherAssignment on update: {ex}")

            return JsonResponse({'success': True, 'id': section.id})
        except Exception as e:
            logger.exception(f"Error updating section: {e}")
            return JsonResponse({'success': False, 'error': str(e)}, status=400)


class SectionDeleteView(LoginRequiredMixin, DeleteView):
    model = Section
    
    def post(self, request, *args, **kwargs):
        try:
            self.get_object().delete()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})


def _sync_subject_assignments(subject, school, request):
    """Synchronize class and section linkages for a subject in the active academic year."""
    if 'sync_classes' not in request.POST:
        return

    # Resolve active academic year
    active_year = AcademicYear.objects.filter(is_active=True)
    if school:
        active_year = active_year.filter(school=school)
    active_year = active_year.first()

    if not active_year and school:
        active_year = AcademicYear.objects.filter(school=school).order_by('-start_date').first()

    if not active_year:
        logger.warning(f"No academic year found when syncing subject assignments for {subject}")
        return

    # Parse class IDs and section IDs from POST
    all_class_ids = [int(cid) for cid in request.POST.getlist('class_ids') if cid.isdigit()]
    specific_section_ids = [int(sid) for sid in request.POST.getlist('section_ids') if sid.isdigit()]

    # Fetch existing assignments to preserve teachers
    existing_assignments = AssignedSubject.objects.filter(
        subject=subject,
        academic_year=active_year
    )
    if school:
        existing_assignments = existing_assignments.filter(class_name__school=school)

    # Map (class_id, section_id) -> teacher_id
    teacher_map = {
        (a.class_name_id, a.section_id): a.teacher_id
        for a in existing_assignments
    }

    # Desired (class_id, section_id) pairs
    desired_pairs = set()

    # Find classes of specific sections
    valid_sections = []
    specific_section_class_ids = set()
    if specific_section_ids:
        valid_sections = list(Section.objects.filter(id__in=specific_section_ids).select_related('class_name'))
        if school:
            valid_sections = [s for s in valid_sections if s.class_name.school_id == school.id]
        specific_section_class_ids = {s.class_name_id for s in valid_sections}

    # Process class_ids
    valid_classes = Class.objects.filter(id__in=all_class_ids)
    if school:
        valid_classes = valid_classes.filter(school=school)
    for c in valid_classes:
        # If specific sections were chosen for this class, don't assign all sections (None)
        if c.id not in specific_section_class_ids:
            desired_pairs.add((c.id, None))

    # Add specific section pairs
    for s in valid_sections:
        desired_pairs.add((s.class_name_id, s.id))

    existing_pairs = set(teacher_map.keys())

    # Delete unselected pairs
    to_remove = existing_pairs - desired_pairs
    for cid, sid in to_remove:
        q = existing_assignments.filter(class_name_id=cid)
        if sid is None:
            q = q.filter(section__isnull=True)
        else:
            q = q.filter(section_id=sid)
        q.delete()

    # Create new pairs
    to_add = desired_pairs - existing_pairs
    for cid, sid in to_add:
        AssignedSubject.objects.create(
            subject=subject,
            class_name_id=cid,
            section_id=sid,
            academic_year=active_year,
            is_active=True,
            teacher_id=teacher_map.get((cid, sid))
        )


class SubjectListView(LoginRequiredMixin, ListView):
    model = Subject
    template_name = 'academics/subject_list.html'
    context_object_name = 'subjects'

    def dispatch(self, request, *args, **kwargs):
        if request.user.role == 'student':
            from django.contrib import messages
            from django.shortcuts import redirect
            messages.info(request, "Students can only view subjects assigned to their class.")
            return redirect('core:my_subjects', school_slug=kwargs.get('school_slug'))
        if not (request.user.is_school_admin or request.user.is_teacher):
            from django.contrib import messages
            from django.shortcuts import redirect
            messages.error(request, "Access denied.")
            return redirect('core:dashboard', school_slug=kwargs.get('school_slug'))
        return super().dispatch(request, *args, **kwargs)

    def _get_active_year(self, school):
        year = AcademicYear.objects.filter(is_active=True)
        if school:
            year = year.filter(school=school)
        year = year.first()
        if not year and school:
            year = AcademicYear.objects.filter(school=school).order_by('-start_date').first()
        return year

    def get_queryset(self):
        school = get_current_school(self.request)
        qs = Subject.objects.filter(is_active=True)
        if school:
            qs = qs.filter(school=school)
        active_year = self._get_active_year(school)
        if active_year:
            assignment_qs = AssignedSubject.objects.filter(
                academic_year=active_year,
                is_active=True
            ).select_related('class_name', 'section').order_by('class_name__order', 'class_name__name', 'section__name')
            qs = qs.prefetch_related(
                Prefetch('subject_assignments', queryset=assignment_qs, to_attr='active_assignments')
            )
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        school = get_current_school(self.request)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        active_year = self._get_active_year(school)
        context['active_year'] = active_year

        # Active classes with sections for the school to link in add/edit panel
        classes_qs = Class.objects.filter(is_active=True)
        if school:
            classes_qs = classes_qs.filter(school=school)
        context['classes'] = list(classes_qs.prefetch_related('sections').order_by('order', 'name'))

        # Decorate subjects with assigned classes data for UI and filtering
        for subject in context['subjects']:
            active_assignments = getattr(subject, 'active_assignments', None)
            if active_assignments is None:
                if active_year:
                    active_assignments = list(subject.subject_assignments.filter(
                        academic_year=active_year, is_active=True
                    ).select_related('class_name', 'section').order_by('class_name__order', 'class_name__name', 'section__name'))
                else:
                    active_assignments = []

            assigned_classes_list = []
            badges = []
            class_names_set = set()
            class_ids_set = set()

            for a in active_assignments:
                class_ids_set.add(str(a.class_name_id))
                class_names_set.add(a.class_name.name.lower())
                assigned_classes_list.append({
                    'class_id': a.class_name_id,
                    'class_name': a.class_name.name,
                    'section_id': a.section_id,
                    'section_name': a.section.name if a.section else None
                })
                badges.append({
                    'class_id': a.class_name_id,
                    'name': a.class_name.name,
                    'section_name': a.section.name if a.section else None
                })

            subject.assigned_classes_json = json.dumps(assigned_classes_list)
            subject.assigned_display_badges = badges
            subject.assigned_class_ids_str = ' '.join(class_ids_set)
            subject.assigned_class_names_str = ', '.join(sorted(class_names_set))

        return context


class SubjectCreateView(LoginRequiredMixin, CreateView):
    model = Subject
    template_name = 'academics/subject_form.html'
    fields = ['name', 'code', 'subject_type', 'description', 'credits', 'is_active']
    success_url = reverse_lazy('academics:subject_list')

    def dispatch(self, request, *args, **kwargs):
        if request.user.role == 'student':
            from django.contrib import messages
            from django.shortcuts import redirect
            messages.error(request, "Access denied.")
            return redirect('core:my_subjects', school_slug=kwargs.get('school_slug'))
        if not (request.user.is_school_admin or request.user.is_teacher):
            from django.contrib import messages
            from django.shortcuts import redirect
            messages.error(request, "Access denied.")
            return redirect('core:dashboard', school_slug=kwargs.get('school_slug'))
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        try:
            school = get_current_school(request)
            with transaction.atomic():
                subject = Subject.objects.create(
                    name=request.POST.get('name'),
                    code=request.POST.get('code'),
                    subject_type=request.POST.get('subject_type', 'theory'),
                    description=request.POST.get('description', ''),
                    credits=request.POST.get('credits', 1) or 1,
                    is_active=request.POST.get('is_active') == 'on',
                    school=school
                )
                _sync_subject_assignments(subject, school, request)
            return JsonResponse({'success': True, 'id': subject.id})
        except Exception as e:
            logger.exception(f"Error creating subject: {e}")
            return JsonResponse({'success': False, 'error': str(e)})


class SubjectUpdateView(LoginRequiredMixin, UpdateView):
    model = Subject
    template_name = 'academics/subject_form.html'
    fields = ['name', 'code', 'subject_type', 'description', 'credits', 'is_active']
    success_url = reverse_lazy('academics:subject_list')

    def dispatch(self, request, *args, **kwargs):
        if request.user.role == 'student':
            from django.contrib import messages
            from django.shortcuts import redirect
            messages.error(request, "Access denied.")
            return redirect('core:my_subjects', school_slug=kwargs.get('school_slug'))
        if not (request.user.is_school_admin or request.user.is_teacher):
            from django.contrib import messages
            from django.shortcuts import redirect
            messages.error(request, "Access denied.")
            return redirect('core:dashboard', school_slug=kwargs.get('school_slug'))
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        try:
            subject = self.get_object()
            school = get_current_school(request) or subject.school
            with transaction.atomic():
                subject.name = request.POST.get('name')
                subject.code = request.POST.get('code')
                subject.subject_type = request.POST.get('subject_type', 'theory')
                subject.description = request.POST.get('description', '')
                subject.credits = request.POST.get('credits', 1) or 1
                subject.is_active = request.POST.get('is_active') == 'on'
                subject.save()
                _sync_subject_assignments(subject, school, request)
            return JsonResponse({'success': True, 'message': 'Subject updated successfully'})
        except Exception as e:
            logger.exception(f"Error updating subject: {e}")
            return JsonResponse({'success': False, 'error': str(e)})


class SubjectDeleteView(LoginRequiredMixin, DeleteView):
    model = Subject

    def dispatch(self, request, *args, **kwargs):
        if request.user.role == 'student':
            from django.contrib import messages
            from django.shortcuts import redirect
            messages.error(request, "Access denied.")
            return redirect('core:my_subjects', school_slug=kwargs.get('school_slug'))
        if not (request.user.is_school_admin or request.user.is_teacher):
            from django.contrib import messages
            from django.shortcuts import redirect
            messages.error(request, "Access denied.")
            return redirect('core:dashboard', school_slug=kwargs.get('school_slug'))
        return super().dispatch(request, *args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        try:
            self.get_object().delete()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})


class ClassRoutineView(LoginRequiredMixin, ListView):
    model = ClassRoutine
    template_name = 'academics/routine.html'
    context_object_name = 'routines'

    def dispatch(self, request, *args, **kwargs):
        if request.user.role == 'student':
            messages.info(request, "Students can only view their own class routine.")
            return redirect('core:my_class_routine', school_slug=kwargs.get('school_slug'))
        if not (request.user.is_school_admin or request.user.is_teacher):
            from django.contrib import messages
            messages.error(request, "Access denied.")
            from django.shortcuts import redirect
            return redirect('core:dashboard', school_slug=kwargs.get('school_slug'))
        return super().dispatch(request, *args, **kwargs)
    
    def get_queryset(self):
        school = get_current_school(self.request)
        qs = ClassRoutine.objects.all()
        if school:
            qs = qs.filter(class_name__school=school)
        return qs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        context['days'] = ClassRoutine.WEEKDAY_CHOICES
        school = get_current_school(self.request)

        ensure_default_class_times_for_school(school)
        # Filter classes by school
        classes_qs = Class.objects.filter(is_active=True)
        if school:
            classes_qs = classes_qs.filter(school=school)
        context['classes'] = classes_qs
        # Filter rooms and periods by school for form dropdowns
        rooms_qs = ClassRoom.objects.filter(is_active=True)
        periods_qs = ClassTime.objects.filter(is_active=True)
        if school:
            rooms_qs = rooms_qs.filter(school=school)
            periods_qs = periods_qs.filter(school=school)
        context['rooms'] = rooms_qs
        context['periods'] = periods_qs

        subjects_qs = Subject.objects.filter(is_active=True)
        if school:
            subjects_qs = subjects_qs.filter(school=school)
        context['subjects'] = subjects_qs

        teachers_qs = User.objects.filter(role='teacher', is_active=True)
        if school:
            teachers_qs = teachers_qs.filter(school=school)
        context['teachers'] = teachers_qs

        years_qs = AcademicYear.objects.all()
        if school:
            years_qs = years_qs.filter(school=school)
        context['academic_years'] = years_qs
        return context


class ClassRoutineCreateView(LoginRequiredMixin, CreateView):
    model = ClassRoutine
    template_name = 'academics/routine_form.html'
    fields = '__all__'

    def dispatch(self, request, *args, **kwargs):
        if not (request.user.is_school_admin or request.user.is_teacher):
            from django.contrib import messages
            messages.error(request, "Access denied.")
            from django.shortcuts import redirect
            return redirect('core:dashboard', school_slug=kwargs.get('school_slug'))
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        form.instance.school = get_current_school(self.request)
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        return context
    
    def get_success_url(self):
        return reverse('academics:routine', kwargs={'school_slug': self.kwargs.get('school_slug')})


# ClassTime Views for managing time periods and breaks
class ClassTimeListView(LoginRequiredMixin, ListView):
    model = ClassTime
    template_name = 'academics/class_time_list.html'
    context_object_name = 'class_times'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        return context
    
    def get_queryset(self):
        school = get_current_school(self.request)
        if not school:
            school = School.objects.filter(slug=self.kwargs.get('school_slug')).first()
        ensure_default_class_times_for_school(school)
        qs = ClassTime.objects.filter(is_active=True)
        if school:
            qs = qs.filter(school=school)
        return qs.order_by('order', 'start_time')


class ClassTimeCreateView(LoginRequiredMixin, CreateView):
    model = ClassTime
    template_name = 'academics/class_time_form.html'
    fields = ['name', 'start_time', 'end_time', 'is_break', 'order', 'is_active']
    
    def form_valid(self, form):
        form.instance.school = get_current_school(self.request)
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        return context
    
    def get_success_url(self):
        return reverse('academics:class_time_list', kwargs={'school_slug': self.kwargs.get('school_slug')})


class ClassTimeUpdateView(LoginRequiredMixin, UpdateView):
    model = ClassTime
    template_name = 'academics/class_time_form.html'
    fields = ['name', 'start_time', 'end_time', 'is_break', 'order', 'is_active']
    
    def get_queryset(self):
        school = get_current_school(self.request)
        qs = ClassTime.objects.all()
        if school:
            qs = qs.filter(school=school)
        return qs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        return context
    
    def get_success_url(self):
        return reverse('academics:class_time_list', kwargs={'school_slug': self.kwargs.get('school_slug')})


class ClassTimeDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        try:
            school = get_current_school(request)
            qs = ClassTime.objects.all()
            if school:
                qs = qs.filter(school=school)
            class_time = qs.get(pk=pk)
            class_time.delete()
            return JsonResponse({'success': True})
        except ClassTime.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Time period not found'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})


# ClassRoom Views for managing rooms
class ClassRoomListView(LoginRequiredMixin, ListView):
    model = ClassRoom
    template_name = 'academics/classroom_list.html'
    context_object_name = 'classrooms'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        return context
    
    def get_queryset(self):
        school = get_current_school(self.request)
        qs = ClassRoom.objects.filter(is_active=True)
        if school:
            qs = qs.filter(school=school)
        return qs.order_by('building', 'floor', 'room_number')


class ClassRoomCreateView(LoginRequiredMixin, CreateView):
    model = ClassRoom
    template_name = 'academics/classroom_form.html'
    fields = ['room_number', 'name', 'room_type', 'capacity', 'floor', 'building', 'is_active']
    
    def form_valid(self, form):
        form.instance.school = get_current_school(self.request)
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        return context
    
    def get_success_url(self):
        return reverse('academics:classroom_list', kwargs={'school_slug': self.kwargs.get('school_slug')})


class ClassRoomUpdateView(LoginRequiredMixin, UpdateView):
    model = ClassRoom
    template_name = 'academics/classroom_form.html'
    fields = ['room_number', 'name', 'room_type', 'capacity', 'floor', 'building', 'is_active']
    
    def get_queryset(self):
        school = get_current_school(self.request)
        qs = ClassRoom.objects.all()
        if school:
            qs = qs.filter(school=school)
        return qs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        return context
    
    def get_success_url(self):
        return reverse('academics:classroom_list', kwargs={'school_slug': self.kwargs.get('school_slug')})


class ClassRoomDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        try:
            school = get_current_school(request)
            qs = ClassRoom.objects.all()
            if school:
                qs = qs.filter(school=school)
            classroom = qs.get(pk=pk)
            classroom.delete()
            return JsonResponse({'success': True})
        except ClassRoom.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Room not found'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})


class StudyMaterialListView(LoginRequiredMixin, ListView):
    model = StudyMaterial
    template_name = 'academics/study_materials.html'
    context_object_name = 'materials'
    
    def get_queryset(self):
        school = get_current_school(self.request)
        qs = StudyMaterial.objects.all()
        if school:
            qs = qs.filter(
                Q(class_name__school=school) |
                Q(section__class_name__school=school) |
                Q(subject__school=school)
            ).distinct()
        return qs


class StudyMaterialUploadView(LoginRequiredMixin, CreateView):
    model = StudyMaterial
    template_name = 'academics/study_material_form.html'
    fields = ['title', 'content_type', 'description', 'class_name', 'section', 'subject', 'file']
    success_url = reverse_lazy('academics:study_materials')


class AssignmentListView(LoginRequiredMixin, ListView):
    model = Assignment
    template_name = 'academics/assignments.html'
    context_object_name = 'assignments'
    
    def get_queryset(self):
        school = get_current_school(self.request)
        qs = Assignment.objects.all()
        if school:
            qs = qs.filter(
                Q(class_name__school=school) |
                Q(section__class_name__school=school) |
                Q(subject__school=school)
            ).distinct()
        return qs


class AssignmentCreateView(LoginRequiredMixin, CreateView):
    model = Assignment
    template_name = 'academics/assignment_form.html'
    fields = '__all__'
    success_url = reverse_lazy('academics:assignments')


class AssignmentDetailView(LoginRequiredMixin, DetailView):
    model = Assignment
    template_name = 'academics/assignment_detail.html'
    context_object_name = 'assignment'


# API Views
def test_api(request, school_slug=None):
    """Simple test endpoint to verify API routing"""
    return JsonResponse({
        'success': True,
        'message': 'API is working!',
        'school_slug': school_slug,
        'user': request.user.email if request.user.is_authenticated else 'Anonymous'
    })


def get_teachers_api(request, school_slug=None):
    """API endpoint to fetch teachers for dropdowns"""
    # Allow unauthenticated for debugging, but check user
    if not request.user.is_authenticated:
        return JsonResponse({
            'success': False,
            'error': 'Authentication required',
            'teachers': []
        }, status=401)
    
    try:
        # Scope teachers to current school
        school = get_current_school(request)
        teachers_qs = User.objects.filter(role='teacher', is_active=True)
        if school:
            teachers_qs = teachers_qs.filter(school=school)
        teachers = teachers_qs.values('id', 'first_name', 'last_name', 'email')
        
        teachers_list = [
            {
                'id': t['id'],
                'name': f"{t['first_name']} {t['last_name']}",
                'email': t['email']
            }
            for t in teachers
        ]
        
        return JsonResponse({
            'success': True,
            'teachers': teachers_list,
            'count': len(teachers_list)
        })
    except Exception as e:
        import traceback
        return JsonResponse({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc(),
            'teachers': []
        }, status=500)


def get_sections_api(request, school_slug=None):
    """API endpoint to fetch sections for a given class"""
    if not request.user.is_authenticated:
        return JsonResponse({
            'success': False,
            'error': 'Authentication required',
            'sections': []
        }, status=401)
    
    try:
        class_id = request.GET.get('class_id')
        if not class_id:
            return JsonResponse({
                'success': False,
                'error': 'class_id parameter required',
                'sections': []
            })
        
        sections = Section.objects.filter(class_name_id=class_id, is_active=True).values('id', 'name', 'capacity')
        
        sections_list = [
            {
                'id': s['id'],
                'name': s['name'],
                'capacity': s['capacity']
            }
            for s in sections
        ]
        
        return JsonResponse({
            'success': True,
            'sections': sections_list,
            'count': len(sections_list)
        })
    except Exception as e:
        import traceback
        return JsonResponse({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc(),
            'sections': []
        }, status=500)


@login_required
def get_sections_by_class(request, school_slug, class_id):
    """API endpoint to get sections for a specific class"""
    if not (request.user.is_school_admin or request.user.is_teacher):
        return JsonResponse({'success': False, 'error': 'Access denied'}, status=403)
    
    try:
        school = get_current_school(request)
        sections = Section.objects.filter(class_name_id=class_id, class_name__school=school)
        
        sections_list = [
            {
                'id': section.id,
                'name': section.name,
                'capacity': section.max_students
            }
            for section in sections
        ]
        
        return JsonResponse({
            'success': True,
            'sections': sections_list
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def class_routine_detail_api(request, school_slug, pk):
    if not (request.user.is_school_admin or request.user.is_teacher):
        return JsonResponse({'success': False, 'error': 'Access denied'}, status=403)

    school = get_current_school(request)
    qs = ClassRoutine.objects.select_related(
        'class_name', 'section', 'class_time', 'subject', 'teacher', 'room', 'academic_year'
    )
    if school:
        qs = qs.filter(class_name__school=school)

    routine = qs.filter(pk=pk).first()
    if not routine:
        return JsonResponse({'success': False, 'error': 'Routine entry not found'}, status=404)

    return JsonResponse({
        'success': True,
        'routine': {
            'id': routine.pk,
            'class_name_id': routine.class_name_id,
            'section_id': routine.section_id,
            'day_of_week': routine.day_of_week,
            'class_time_id': routine.class_time_id,
            'subject_id': routine.subject_id,
            'teacher_id': routine.teacher_id,
            'room_id': routine.room_id,
            'academic_year_id': routine.academic_year_id,
            'is_active': routine.is_active,
            'notes': routine.notes,
        }
    })


@login_required
def class_routine_edit_api(request, school_slug, pk):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    if not (request.user.is_school_admin or request.user.is_teacher):
        return JsonResponse({'success': False, 'error': 'Access denied'}, status=403)

    school = get_current_school(request)
    qs = ClassRoutine.objects.all()
    if school:
        qs = qs.filter(class_name__school=school)
    routine = qs.filter(pk=pk).first()
    if not routine:
        return JsonResponse({'success': False, 'error': 'Routine entry not found'}, status=404)

    try:
        routine.class_name_id = request.POST.get('class_name') or routine.class_name_id
        routine.section_id = request.POST.get('section') or routine.section_id
        routine.day_of_week = int(request.POST.get('day_of_week')) if request.POST.get('day_of_week') is not None else routine.day_of_week
        routine.class_time_id = request.POST.get('class_time') or routine.class_time_id
        routine.subject_id = request.POST.get('subject') or routine.subject_id
        routine.teacher_id = request.POST.get('teacher') or None
        routine.room_id = request.POST.get('room') or None
        routine.academic_year_id = request.POST.get('academic_year') or routine.academic_year_id
        routine.is_active = bool(request.POST.get('is_active'))
        routine.notes = request.POST.get('notes', '')
        routine.save()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
def class_routine_delete_api(request, school_slug, pk):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    if not (request.user.is_school_admin or request.user.is_teacher):
        return JsonResponse({'success': False, 'error': 'Access denied'}, status=403)

    school = get_current_school(request)
    qs = ClassRoutine.objects.all()
    if school:
        qs = qs.filter(class_name__school=school)
    routine = qs.filter(pk=pk).first()
    if not routine:
        return JsonResponse({'success': False, 'error': 'Routine entry not found'}, status=404)

    routine.delete()
    return JsonResponse({'success': True})


@login_required
def export_routine_pdf(request, school_slug):
    """Export class routine as formatted PDF"""
    if not (request.user.is_school_admin or request.user.is_teacher):
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    class_id = request.GET.get('class_id')
    section_id = request.GET.get('section_id')
    
    if not class_id or not section_id:
        return JsonResponse({'error': 'Class and section required'}, status=400)
    
    try:
        school = get_current_school(request)
        class_obj = Class.objects.get(id=class_id, school=school)
        section = Section.objects.get(id=section_id, class_name=class_obj)
        
        # Get routines for this class and section
        routines = ClassRoutine.objects.filter(
            class_name=class_obj,
            section=section,
            is_active=True
        ).select_related('class_time', 'subject', 'teacher').order_by('day_of_week', 'class_time__start_time')
        
        # Create PDF
        response = HttpResponse(content_type='application/pdf')
        filename = f"Timetable_{class_obj.name}_{section.name}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        doc = SimpleDocTemplate(response, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=1  # Center
        )
        story.append(Paragraph(f"CLASS TIMETABLE - {class_obj.name} {section.name}", title_style))
        story.append(Spacer(1, 12))
        
        # School info
        info_style = ParagraphStyle(
            'Info',
            parent=styles['Normal'],
            fontSize=10,
            alignment=1
        )
        story.append(Paragraph(f"{school.name}", info_style))
        story.append(Paragraph(f"Academic Year: {datetime.now().year}", info_style))
        story.append(Spacer(1, 20))
        
        # Prepare timetable data
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        time_slots = ClassTime.objects.filter(
            school=school,
            is_active=True
        ).order_by('start_time')
        
        # Create table data
        table_data = [['Time/Day'] + days]
        
        for time_slot in time_slots:
            row = [str(time_slot)]
            for day_num, day_name in enumerate(days):
                routine = routines.filter(day_of_week=day_num, class_time=time_slot).first()
                if routine:
                    cell_text = f"{routine.subject.name}<br/>"
                    if routine.teacher:
                        cell_text += f"{routine.teacher.first_name} {routine.teacher.last_name}<br/>"
                    if routine.room:
                        cell_text += f"Room: {routine.room.name}"
                else:
                    cell_text = ""
                row.append(cell_text)
            table_data.append(row)
        
        # Create table
        table = Table(table_data)
        
        # Style the table
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E3A5F')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        # Make first column (time) bold
        for i in range(1, len(table_data)):
            table.setStyle(TableStyle([
                ('FONTNAME', (0, i), (0, i), 'Helvetica-Bold'),
                ('BACKGROUND', (0, i), (0, i), colors.HexColor('#e9ecef')),
            ]))
        
        story.append(table)
        
        doc.build(story)
        return response
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def export_routine_excel(request, school_slug):
    """Export class routine as Excel spreadsheet"""
    if not (request.user.is_school_admin or request.user.is_teacher):
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    class_id = request.GET.get('class_id')
    section_id = request.GET.get('section_id')
    
    if not class_id or not section_id:
        return JsonResponse({'error': 'Class and section required'}, status=400)
    
    try:
        school = get_current_school(request)
        class_obj = Class.objects.get(id=class_id, school=school)
        section = Section.objects.get(id=section_id, class_name=class_obj)
        
        # Get routines for this class and section
        routines = ClassRoutine.objects.filter(
            class_name=class_obj,
            section=section,
            is_active=True
        ).select_related('class_time', 'subject', 'teacher', 'room').order_by('day_of_week', 'class_time__start_time')
        
        # Create Excel workbook
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = f"Timetable_{class_obj.name}_{section.name}"
        
        # Define styles
        header_font = Font(bold=True, color='FFFFFF')
        header_fill = PatternFill(start_color='1E3A5F', end_color='1E3A5F', fill_type='solid')
        border = Border(left=Side(style='thin'), right=Side(style='thin'), 
                       top=Side(style='thin'), bottom=Side(style='thin'))
        center_alignment = Alignment(horizontal='center', vertical='middle')
        
        # Set column widths
        column_widths = [15, 20, 20, 20, 20, 20]
        for i, width in enumerate(column_widths, 1):
            ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = width
        
        # Merge title cells
        ws.merge_cells('A1:F1')
        title_cell = ws['A1']
        title_cell.value = f"CLASS TIMETABLE - {class_obj.name} {section.name}"
        title_cell.font = Font(bold=True, size=16)
        title_cell.alignment = center_alignment
        
        # School info
        ws.merge_cells('A2:F2')
        ws['A2'].value = school.name
        ws['A2'].alignment = center_alignment
        
        ws.merge_cells('A3:F3')
        ws['A3'].value = f"Academic Year: {datetime.now().year}"
        ws['A3'].alignment = center_alignment
        
        # Prepare timetable headers
        headers = ['Time/Day', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        header_row = 5
        
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=header_row, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.border = border
            cell.alignment = center_alignment
        
        # Get time slots
        time_slots = ClassTime.objects.filter(
            school=school,
            is_active=True
        ).order_by('start_time')
        
        # Fill timetable data
        current_row = header_row + 1
        days = [0, 1, 2, 3, 4]  # Monday to Friday
        
        for time_slot in time_slots:
            # Time column
            time_cell = ws.cell(row=current_row, column=1, value=str(time_slot))
            time_cell.font = Font(bold=True)
            time_cell.fill = PatternFill(start_color='e9ecef', end_color='e9ecef', fill_type='solid')
            time_cell.border = border
            time_cell.alignment = center_alignment
            
            # Days columns
            for col_idx, day_num in enumerate(days, 2):
                routine = routines.filter(day_of_week=day_num, class_time=time_slot).first()
                if routine:
                    cell_text = f"{routine.subject.name}\n"
                    if routine.teacher:
                        cell_text += f"{routine.teacher.first_name} {routine.teacher.last_name}\n"
                    if routine.room:
                        cell_text += f"Room: {routine.room.name}"
                else:
                    cell_text = ""
                
                cell = ws.cell(row=current_row, column=col_idx, value=cell_text)
                cell.border = border
                cell.alignment = Alignment(horizontal='center', vertical='middle', wrap_text=True)
            
            current_row += 1
        
        # Prepare response
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        filename = f"Timetable_{class_obj.name}_{section.name}.xlsx"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        wb.save(response)
        return response
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ============================================================================
# SYLLABUS MANAGEMENT VIEWS
# ============================================================================

class SyllabusListView(LoginRequiredMixin, ListView):
    model = Syllabus
    template_name = 'academics/syllabus_list.html'
    context_object_name = 'syllabi'
    paginate_by = 15

    def get_queryset(self):
        school = get_current_school(self.request)
        qs = Syllabus.objects.select_related('class_name', 'subject', 'academic_year', 'created_by')
        if school:
            qs = qs.filter(class_name__school=school)

        class_id = self.request.GET.get('class_id')
        if class_id and class_id.isdigit():
            qs = qs.filter(class_name_id=int(class_id))

        subject_id = self.request.GET.get('subject_id')
        if subject_id and subject_id.isdigit():
            qs = qs.filter(subject_id=int(subject_id))

        academic_year_id = self.request.GET.get('academic_year_id')
        if academic_year_id and academic_year_id.isdigit():
            qs = qs.filter(academic_year_id=int(academic_year_id))

        search = self.request.GET.get('search', '').strip()
        if search:
            qs = qs.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search) |
                Q(subject__name__icontains=search) |
                Q(class_name__name__icontains=search)
            )

        return qs.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        school_slug = self.kwargs.get('school_slug', '')
        context['school_slug'] = school_slug
        school = get_current_school(self.request)

        classes_qs = Class.objects.filter(is_active=True)
        subjects_qs = Subject.objects.filter(is_active=True)
        ay_qs = AcademicYear.objects.all().order_by('-start_date')
        if school:
            classes_qs = classes_qs.filter(school=school)
            subjects_qs = subjects_qs.filter(school=school)
            ay_qs = ay_qs.filter(school=school)

        context['classes'] = classes_qs
        context['subjects'] = subjects_qs
        context['academic_years'] = ay_qs
        context['active_year'] = ay_qs.filter(is_active=True).first()

        context['selected_class_id'] = self.request.GET.get('class_id', '')
        context['selected_subject_id'] = self.request.GET.get('subject_id', '')
        context['selected_academic_year_id'] = self.request.GET.get('academic_year_id', '')
        context['search_query'] = self.request.GET.get('search', '')
        return context


ALLOWED_SYLLABUS_EXTENSIONS = ('.pdf', '.docx', '.doc', '.xlsx', '.txt')
MAX_SYLLABUS_FILE_SIZE = 15 * 1024 * 1024  # 15 MB


def validate_syllabus_file(file):
    if not file:
        return None
    import os
    ext = os.path.splitext(file.name)[1].lower()
    if ext not in ALLOWED_SYLLABUS_EXTENSIONS:
        return f"Invalid file type '{ext}'. Allowed file extensions: .pdf, .docx, .doc, .xlsx, .txt."
    if file.size > MAX_SYLLABUS_FILE_SIZE:
        return "File size exceeds maximum allowed limit of 15 MB."
    return None


def validate_syllabus_subject_assignment(class_obj, subject_obj, ay_obj, school):
    if school and subject_obj.school and subject_obj.school != school:
        return "Selected subject does not belong to this school."
    if school and class_obj.school and class_obj.school != school:
        return "Selected class does not belong to this school."

    # If class has assignments configured for this academic year, verify subject is among them
    class_assignments = AssignedSubject.objects.filter(
        class_name=class_obj,
        academic_year=ay_obj,
        is_active=True
    )
    if class_assignments.exists():
        if not class_assignments.filter(subject=subject_obj).exists():
            return f"Subject '{subject_obj.name}' is not assigned to class '{class_obj.name}' for {ay_obj.name}."
    return None


class SyllabusCreateView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        if not (request.user.is_school_admin or request.user.is_teacher or request.user.is_superuser):
            return JsonResponse({'success': False, 'error': 'Permission denied.'}, status=403)
        try:
            school = get_current_school(request)
            class_id = request.POST.get('class_name')
            subject_id = request.POST.get('subject')
            academic_year_id = request.POST.get('academic_year')
            title = request.POST.get('title', '').strip()
            description = request.POST.get('description', '').strip()
            content = request.POST.get('content', '').strip()
            file = request.FILES.get('file')

            if not (class_id and subject_id and title):
                return JsonResponse({'success': False, 'error': 'Class, subject, and title are required.'}, status=400)

            class_obj = Class.objects.filter(pk=class_id)
            if school:
                class_obj = class_obj.filter(school=school)
            class_obj = class_obj.first()
            if not class_obj:
                return JsonResponse({'success': False, 'error': 'Invalid class.'}, status=400)

            subject_obj = Subject.objects.filter(pk=subject_id)
            if school:
                subject_obj = subject_obj.filter(school=school)
            subject_obj = subject_obj.first()
            if not subject_obj:
                return JsonResponse({'success': False, 'error': 'Invalid subject.'}, status=400)

            ay_obj = None
            if academic_year_id and str(academic_year_id).isdigit():
                ay_obj = AcademicYear.objects.filter(pk=int(academic_year_id)).first()
            if not ay_obj:
                ay_qs = AcademicYear.objects.filter(is_active=True)
                if school:
                    ay_qs = ay_qs.filter(school=school)
                ay_obj = ay_qs.first()

            if not ay_obj:
                return JsonResponse({'success': False, 'error': 'No active academic year found.'}, status=400)

            # Validate uploaded file
            file_error = validate_syllabus_file(file)
            if file_error:
                return JsonResponse({'success': False, 'error': file_error}, status=400)

            # Validate subject assignment to class
            assignment_error = validate_syllabus_subject_assignment(class_obj, subject_obj, ay_obj, school)
            if assignment_error:
                return JsonResponse({'success': False, 'error': assignment_error}, status=400)

            syllabus = Syllabus.objects.create(
                class_name=class_obj,
                subject=subject_obj,
                academic_year=ay_obj,
                title=title,
                description=description,
                content=content,
                file=file,
                created_by=request.user
            )

            if request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.headers.get('accept', ''):
                return JsonResponse({'success': True, 'id': syllabus.id, 'message': 'Syllabus created successfully.'})
            from django.contrib import messages
            messages.success(request, 'Syllabus added successfully.')
            return redirect('academics:syllabus_list', school_slug=kwargs.get('school_slug'))
        except Exception as e:
            logger.exception(f"Error creating syllabus: {e}")
            return JsonResponse({'success': False, 'error': str(e)}, status=500)


class SyllabusUpdateView(LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        if not (request.user.is_school_admin or request.user.is_teacher or request.user.is_superuser):
            return JsonResponse({'success': False, 'error': 'Permission denied.'}, status=403)
        try:
            school = get_current_school(request)
            qs = Syllabus.objects.all()
            if school:
                qs = qs.filter(class_name__school=school)
            syllabus = qs.get(pk=pk)

            class_id = request.POST.get('class_name')
            subject_id = request.POST.get('subject')
            academic_year_id = request.POST.get('academic_year')
            title = request.POST.get('title', '').strip()
            description = request.POST.get('description', '').strip()
            content = request.POST.get('content', '').strip()

            target_class = syllabus.class_name
            target_subject = syllabus.subject
            target_ay = syllabus.academic_year

            if class_id:
                class_obj = Class.objects.filter(pk=class_id)
                if school:
                    class_obj = class_obj.filter(school=school)
                if class_obj.exists():
                    target_class = class_obj.first()
                    syllabus.class_name = target_class

            if subject_id:
                subject_obj = Subject.objects.filter(pk=subject_id)
                if school:
                    subject_obj = subject_obj.filter(school=school)
                if subject_obj.exists():
                    target_subject = subject_obj.first()
                    syllabus.subject = target_subject

            if academic_year_id and str(academic_year_id).isdigit():
                ay_obj = AcademicYear.objects.filter(pk=int(academic_year_id)).first()
                if ay_obj:
                    target_ay = ay_obj
                    syllabus.academic_year = target_ay

            # Validate subject assignment to class
            assignment_error = validate_syllabus_subject_assignment(target_class, target_subject, target_ay, school)
            if assignment_error:
                return JsonResponse({'success': False, 'error': assignment_error}, status=400)

            if title:
                syllabus.title = title
            syllabus.description = description
            syllabus.content = content

            if 'file' in request.FILES:
                new_file = request.FILES['file']
                file_error = validate_syllabus_file(new_file)
                if file_error:
                    return JsonResponse({'success': False, 'error': file_error}, status=400)
                syllabus.file = new_file

            syllabus.save()

            if request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.headers.get('accept', ''):
                return JsonResponse({'success': True, 'message': 'Syllabus updated successfully.'})
            from django.contrib import messages
            messages.success(request, 'Syllabus updated successfully.')
            return redirect('academics:syllabus_list', school_slug=kwargs.get('school_slug'))
        except Syllabus.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Syllabus not found.'}, status=404)
        except Exception as e:
            logger.exception(f"Error updating syllabus: {e}")
            return JsonResponse({'success': False, 'error': str(e)}, status=500)


class SyllabusDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        if not (request.user.is_school_admin or request.user.is_teacher or request.user.is_superuser):
            return JsonResponse({'success': False, 'error': 'Permission denied.'}, status=403)
        try:
            school = get_current_school(request)
            qs = Syllabus.objects.all()
            if school:
                qs = qs.filter(class_name__school=school)
            syllabus = qs.get(pk=pk)
            syllabus.delete()
            return JsonResponse({'success': True, 'message': 'Syllabus deleted successfully.'})
        except Syllabus.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Syllabus not found.'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)


def syllabus_detail_api(request, pk, school_slug=None):
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Authentication required'}, status=401)
    try:
        school = get_current_school(request)
        qs = Syllabus.objects.select_related('class_name', 'subject', 'academic_year', 'created_by')
        if school:
            qs = qs.filter(class_name__school=school)
        syllabus = qs.get(pk=pk)
        return JsonResponse({
            'success': True,
            'id': syllabus.id,
            'title': syllabus.title,
            'description': syllabus.description,
            'content': syllabus.content,
            'class_id': syllabus.class_name_id,
            'class_name': syllabus.class_name.name,
            'subject_id': syllabus.subject_id,
            'subject_name': syllabus.subject.name,
            'academic_year_id': syllabus.academic_year_id,
            'academic_year_name': syllabus.academic_year.name,
            'file_url': syllabus.file.url if syllabus.file else None,
            'file_name': syllabus.file.name.split('/')[-1] if syllabus.file else None,
            'created_by': syllabus.created_by.get_full_name() if syllabus.created_by else 'Staff',
            'created_at': syllabus.created_at.strftime('%b %d, %Y'),
            'updated_at': syllabus.updated_at.strftime('%b %d, %Y')
        })
    except Syllabus.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Syllabus not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
