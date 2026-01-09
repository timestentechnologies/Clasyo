from django.shortcuts import render
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from accounts.models import User
from .models import Department, Designation
from core.utils import generate_email, get_school_slug_from_request


class TeacherListView(LoginRequiredMixin, ListView):
    model = User
    template_name = 'human_resource/teacher_list.html'
    context_object_name = 'teachers'
    
    def get_queryset(self):
        return User.objects.filter(role='teacher', is_active=True)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        context['departments'] = Department.objects.filter(is_active=True)
        context['designations'] = Designation.objects.filter(is_active=True)
        return context


class TeacherCreateView(LoginRequiredMixin, CreateView):
    model = User
    
    def post(self, request, *args, **kwargs):
        try:
            first_name = request.POST.get('first_name')
            last_name = request.POST.get('last_name')
            email = request.POST.get('email', '').strip()
            
            # Auto-generate email if not provided
            if not email:
                school_slug = get_school_slug_from_request(request)
                email = generate_email(first_name, last_name, school_slug, 'teacher')
            
            teacher = User.objects.create_user(
                email=email,
                password='teacher123',
                first_name=first_name,
                last_name=last_name,
                role='teacher',
                phone=request.POST.get('phone_number', ''),
                department_id=request.POST.get('department') or None,
                designation_id=request.POST.get('designation') or None,
                is_active=True
            )
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})


class TeacherDetailView(LoginRequiredMixin, DetailView):
    model = User
    template_name = 'human_resource/teacher_detail.html'
    context_object_name = 'teacher'
    
    def get_queryset(self):
        return User.objects.filter(role='teacher')
    
    def get(self, request, *args, **kwargs):
        teacher = self.get_object()
        
        # Return JSON for AJAX requests
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'teacher': {
                    'id': teacher.id,
                    'first_name': teacher.first_name,
                    'last_name': teacher.last_name,
                    'email': teacher.email,
                    'phone': str(teacher.phone) if teacher.phone else '',
                    'department': teacher.department.name if teacher.department else '',
                    'designation': teacher.designation.name if teacher.designation else '',
                    'is_active': teacher.is_active
                }
            })
        
        # Return HTML template for regular requests
        return super().get(request, *args, **kwargs)


@method_decorator(csrf_exempt, name='dispatch')
class TeacherUpdateView(LoginRequiredMixin, UpdateView):
    model = User
    
    def post(self, request, *args, **kwargs):
        try:
            teacher = self.get_object()
            if teacher.role != 'teacher':
                return JsonResponse({'success': False, 'error': 'Not a teacher'})
            
            teacher.first_name = request.POST.get('first_name')
            teacher.last_name = request.POST.get('last_name')
            teacher.email = request.POST.get('email')
            teacher.phone = request.POST.get('phone', '')
            
            # Handle password update if provided
            password = request.POST.get('password', '').strip()
            if password and password != 'teacher123':
                teacher.set_password(password)
            
            teacher.save()
            return JsonResponse({'success': True, 'message': 'Teacher updated successfully'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})


class TeacherDeleteView(LoginRequiredMixin, DeleteView):
    model = User
    
    def post(self, request, *args, **kwargs):
        try:
            teacher = self.get_object()
            if teacher.role == 'teacher':
                teacher.delete()
                return JsonResponse({'success': True})
            return JsonResponse({'success': False, 'error': 'Not a teacher'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})


# Staff Views
class StaffListView(LoginRequiredMixin, ListView):
    model = User
    template_name = 'human_resource/staff_list.html'
    context_object_name = 'staff'
    
    def get_queryset(self):
        return User.objects.filter(role__in=['staff', 'accountant', 'librarian', 'driver'], is_active=True)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        context['departments'] = Department.objects.filter(is_active=True)
        context['designations'] = Designation.objects.filter(is_active=True)
        return context


@method_decorator(csrf_exempt, name='dispatch')
class StaffCreateView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            first_name = request.POST.get('first_name')
            last_name = request.POST.get('last_name')
            email = request.POST.get('email', '').strip()
            role = request.POST.get('role', 'staff')
            
            # Auto-generate email if not provided
            if not email:
                school_slug = get_school_slug_from_request(request)
                email = generate_email(first_name, last_name, school_slug, role)
            
            staff = User.objects.create_user(
                email=email,
                password='staff123',
                first_name=first_name,
                last_name=last_name,
                role=role,
                phone=request.POST.get('phone', ''),
                is_active=True
            )
            return JsonResponse({'success': True, 'message': 'Staff added successfully!'})
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'success': False, 'error': str(e)})


class StaffDetailView(LoginRequiredMixin, DetailView):
    model = User
    template_name = 'human_resource/staff_detail.html'
    
    def get(self, request, *args, **kwargs):
        staff = self.get_object()
        
        # Return JSON for AJAX requests
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'staff': {
                    'id': staff.id,
                    'first_name': staff.first_name,
                    'last_name': staff.last_name,
                    'email': staff.email,
                    'phone': str(staff.phone) if staff.phone else '',
                    'role': staff.role,
                    'is_active': staff.is_active
                }
            })
        
        return super().get(request, *args, **kwargs)


@method_decorator(csrf_exempt, name='dispatch')
class StaffUpdateView(LoginRequiredMixin, UpdateView):
    model = User
    
    def post(self, request, *args, **kwargs):
        try:
            staff = self.get_object()
            staff.first_name = request.POST.get('first_name')
            staff.last_name = request.POST.get('last_name')
            staff.email = request.POST.get('email')
            staff.phone = request.POST.get('phone', '')
            staff.role = request.POST.get('role', staff.role)
            
            # Handle password update
            password = request.POST.get('password', '').strip()
            if password and password != 'staff123':
                staff.set_password(password)
            
            staff.save()
            return JsonResponse({'success': True, 'message': 'Staff updated successfully'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})


class StaffDeleteView(LoginRequiredMixin, DeleteView):
    model = User
    
    def post(self, request, *args, **kwargs):
        try:
            self.get_object().delete()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})


# Department Views
class DepartmentListView(LoginRequiredMixin, ListView):
    model = Department
    template_name = 'human_resource/department_list.html'
    context_object_name = 'departments'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        return context


@method_decorator(csrf_exempt, name='dispatch')
class DepartmentCreateView(LoginRequiredMixin, View):
    model = Department
    
    def post(self, request, *args, **kwargs):
        try:
            Department.objects.create(
                name=request.POST.get('name'),
                code=request.POST.get('code'),
                description=request.POST.get('description', ''),
                is_active=True
            )
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})


@method_decorator(csrf_exempt, name='dispatch')
class DepartmentUpdateView(LoginRequiredMixin, View):
    model = Department
    
    def post(self, request, *args, **kwargs):
        try:
            pk = kwargs.get('pk')
            department = Department.objects.get(pk=pk)
            
            name = request.POST.get('name')
            code = request.POST.get('code')
            description = request.POST.get('description', '')
            
            department.name = name
            department.code = code
            department.description = description
            department.save()
            
            return JsonResponse({'success': True})
        except Department.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Department not found'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})


@method_decorator(csrf_exempt, name='dispatch')
class DepartmentDeleteView(LoginRequiredMixin, View):
    model = Department
    
    def post(self, request, *args, **kwargs):
        try:
            self.get_object().delete()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})


# Designation Views
class DesignationListView(LoginRequiredMixin, ListView):
    model = Designation
    template_name = 'human_resource/designation_list.html'
    context_object_name = 'designations'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        return context


@method_decorator(csrf_exempt, name='dispatch')
class DesignationCreateView(LoginRequiredMixin, View):
    model = Designation
    
    def post(self, request, *args, **kwargs):
        try:
            Designation.objects.create(
                name=request.POST.get('name'),
                code=request.POST.get('code'),
                description=request.POST.get('description', ''),
                level=request.POST.get('level', 1),
                is_active=True
            )
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})


@method_decorator(csrf_exempt, name='dispatch')
class DesignationDeleteView(LoginRequiredMixin, View):
    model = Designation
    
    def post(self, request, *args, **kwargs):
        try:
            self.get_object().delete()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
