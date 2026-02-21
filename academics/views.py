from django.shortcuts import render
from django.views.generic import ListView, CreateView, UpdateView, DetailView, DeleteView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from core.utils import get_current_school
from .models import Class, Section, Subject, ClassRoutine, ClassTime, ClassRoom, StudyMaterial, Assignment
from accounts.models import User
from tenants.models import School


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
        return queryset

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
        return context


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
        form.fields['education_level'].choices = get_allowed_education_level_choices_for_school(school)
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
        # Save the class first
        school_slug = self.kwargs.get('school_slug', '')
        school = None
        if school_slug:
            school = School.objects.filter(slug=school_slug, is_active=True).first()
        if school:
            form.instance.school = school
        self.object = form.save()
        
        # Handle sections
        section_names = self.request.POST.getlist('sections[]')
        section_capacities = self.request.POST.getlist('section_capacity[]')
        section_teachers = self.request.POST.getlist('section_teacher[]')
        
        for i, name in enumerate(section_names):
            if name.strip():  # Only create if name is not empty
                Section.objects.create(
                    class_name=self.object,
                    name=name.strip(),
                    max_students=section_capacities[i] if i < len(section_capacities) else 40,
                    class_teacher_id=section_teachers[i] if i < len(section_teachers) and section_teachers[i] else None
                )
        
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
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
        form.fields['education_level'].choices = get_allowed_education_level_choices_for_school(school)
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
        # Save the class first
        self.object = form.save()
        
        # Delete existing sections (we'll recreate them)
        self.object.sections.all().delete()
        
        # Handle sections
        section_names = self.request.POST.getlist('sections[]')
        section_capacities = self.request.POST.getlist('section_capacity[]')
        section_teachers = self.request.POST.getlist('section_teacher[]')
        
        for i, name in enumerate(section_names):
            if name.strip():  # Only create if name is not empty
                Section.objects.create(
                    class_name=self.object,
                    name=name.strip(),
                    max_students=section_capacities[i] if i < len(section_capacities) else 40,
                    class_teacher_id=section_teachers[i] if i < len(section_teachers) and section_teachers[i] else None
                )
        
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
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


def get_class_api(request, pk, school_slug=None):
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Authentication required'}, status=401)
    try:
        class_obj = Class.objects.get(pk=pk)
        sections = [
            {
                'id': section.id,
                'name': section.name,
                'max_students': section.max_students,
                'class_teacher_id': section.class_teacher_id,
                'class_teacher_name': section.class_teacher.get_full_name() if section.class_teacher else None,
            }
            for section in class_obj.sections.all()
        ]
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
            Section.objects.create(
                class_name_id=request.POST.get('class_name'),
                name=request.POST.get('name'),
                max_students=request.POST.get('max_students') or None,
                room=request.POST.get('room', ''),
                is_active=request.POST.get('is_active') == 'on'
            )
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})


class SectionDeleteView(LoginRequiredMixin, DeleteView):
    model = Section
    
    def post(self, request, *args, **kwargs):
        try:
            self.get_object().delete()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})


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
    
    def get_queryset(self):
        school = get_current_school(self.request)
        qs = Subject.objects.filter(is_active=True)
        if school:
            qs = qs.filter(school=school)
        return qs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
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
            Subject.objects.create(
                name=request.POST.get('name'),
                code=request.POST.get('code'),
                subject_type=request.POST.get('subject_type', 'theory'),
                description=request.POST.get('description', ''),
                credits=request.POST.get('credits', 1),
                is_active=request.POST.get('is_active') == 'on',
                school=school
            )
            return JsonResponse({'success': True})
        except Exception as e:
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
            subject.name = request.POST.get('name')
            subject.code = request.POST.get('code')
            subject.subject_type = request.POST.get('subject_type', 'theory')
            subject.description = request.POST.get('description', '')
            subject.credits = request.POST.get('credits', 1)
            subject.is_active = request.POST.get('is_active') == 'on'
            subject.save()
            return JsonResponse({'success': True, 'message': 'Subject updated successfully'})
        except Exception as e:
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
