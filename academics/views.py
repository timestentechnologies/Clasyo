from django.shortcuts import render
from django.views.generic import ListView, CreateView, UpdateView, DetailView, DeleteView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .models import Class, Section, Subject, ClassRoutine, ClassTime, ClassRoom, StudyMaterial, Assignment
from accounts.models import User


class ClassListView(LoginRequiredMixin, ListView):
    model = Class
    template_name = 'academics/class_list.html'
    context_object_name = 'classes'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        return context


class ClassCreateView(LoginRequiredMixin, CreateView):
    model = Class
    template_name = 'academics/class_form.html'
    fields = ['name', 'numeric_name', 'description', 'order', 'is_active']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        return context
    
    def get_success_url(self):
        return reverse('academics:class_list', kwargs={'school_slug': self.kwargs.get('school_slug')})
    
    def form_valid(self, form):
        # Save the class first
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
        
        return super().form_valid(form)


class ClassUpdateView(LoginRequiredMixin, UpdateView):
    model = Class
    template_name = 'academics/class_form.html'
    fields = ['name', 'numeric_name', 'description', 'order', 'is_active']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
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
        
        return super().form_valid(form)


class ClassDeleteView(LoginRequiredMixin, DeleteView):
    model = Class
    
    def post(self, request, *args, **kwargs):
        try:
            class_obj = self.get_object()
            class_obj.delete()
            return JsonResponse({'success': True, 'message': 'Class deleted successfully'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})


class SectionListView(LoginRequiredMixin, ListView):
    model = Section
    template_name = 'academics/section_list.html'
    context_object_name = 'sections'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
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
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        return context


class SubjectCreateView(LoginRequiredMixin, CreateView):
    model = Subject
    template_name = 'academics/subject_form.html'
    fields = ['name', 'code', 'subject_type', 'description', 'credits', 'is_active']
    success_url = reverse_lazy('academics:subject_list')
    
    def post(self, request, *args, **kwargs):
        try:
            Subject.objects.create(
                name=request.POST.get('name'),
                code=request.POST.get('code'),
                subject_type=request.POST.get('subject_type', 'theory'),
                description=request.POST.get('description', ''),
                credits=request.POST.get('credits', 1),
                is_active=request.POST.get('is_active') == 'on'
            )
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})


class SubjectUpdateView(LoginRequiredMixin, UpdateView):
    model = Subject
    template_name = 'academics/subject_form.html'
    fields = ['name', 'code', 'subject_type', 'description', 'credits', 'is_active']
    success_url = reverse_lazy('academics:subject_list')
    
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
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        context['days'] = ClassRoutine.WEEKDAY_CHOICES
        context['classes'] = Class.objects.filter(is_active=True)
        return context


class ClassRoutineCreateView(LoginRequiredMixin, CreateView):
    model = ClassRoutine
    template_name = 'academics/routine_form.html'
    fields = '__all__'
    
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
        return ClassTime.objects.filter(is_active=True).order_by('order', 'start_time')


class ClassTimeCreateView(LoginRequiredMixin, CreateView):
    model = ClassTime
    template_name = 'academics/class_time_form.html'
    fields = ['name', 'start_time', 'end_time', 'is_break', 'order', 'is_active']
    
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
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        return context
    
    def get_success_url(self):
        return reverse('academics:class_time_list', kwargs={'school_slug': self.kwargs.get('school_slug')})


class ClassTimeDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        try:
            class_time = ClassTime.objects.get(pk=pk)
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
        return ClassRoom.objects.filter(is_active=True).order_by('building', 'floor', 'room_number')


class ClassRoomCreateView(LoginRequiredMixin, CreateView):
    model = ClassRoom
    template_name = 'academics/classroom_form.html'
    fields = ['room_number', 'name', 'room_type', 'capacity', 'floor', 'building', 'is_active']
    
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
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        return context
    
    def get_success_url(self):
        return reverse('academics:classroom_list', kwargs={'school_slug': self.kwargs.get('school_slug')})


class ClassRoomDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        try:
            classroom = ClassRoom.objects.get(pk=pk)
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


class StudyMaterialUploadView(LoginRequiredMixin, CreateView):
    model = StudyMaterial
    template_name = 'academics/study_material_form.html'
    fields = ['title', 'content_type', 'description', 'class_name', 'section', 'subject', 'file']
    success_url = reverse_lazy('academics:study_materials')


class AssignmentListView(LoginRequiredMixin, ListView):
    model = Assignment
    template_name = 'academics/assignments.html'
    context_object_name = 'assignments'


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
        # Get all teachers (you can add tenant filtering later if needed)
        teachers = User.objects.filter(role='teacher', is_active=True).values('id', 'first_name', 'last_name', 'email')
        
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
