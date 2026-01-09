from django.shortcuts import render
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views import View
from accounts.models import User
from datetime import datetime

# Check if models exist
try:
    from .models import Leave, LeaveType
    MODELS_EXIST = True
except ImportError:
    MODELS_EXIST = False
    class Leave:
        pass
    class LeaveType:
        pass


class LeaveListView(LoginRequiredMixin, ListView):
    template_name = 'leave_management/leave_list.html'
    context_object_name = 'leaves'
    
    def get_queryset(self):
        if not MODELS_EXIST:
            return []
        user = self.request.user
        # Admins (superadmin, admin) see all leave applications
        if user.role in ['superadmin', 'admin']:
            return Leave.objects.all().order_by('-created_at')
        # Teachers see only their own leave applications
        elif user.role == 'teacher':
            return Leave.objects.filter(teacher=user).order_by('-created_at')
        # Students see only their own leave applications
        elif user.role == 'student':
            from students.models import Student
            try:
                student = Student.objects.get(user=user)
                return Leave.objects.filter(student=student).order_by('-created_at')
            except Student.DoesNotExist:
                return Leave.objects.none()
        # Staff see only their own leave applications
        elif user.role == 'staff':
            return Leave.objects.filter(staff=user).order_by('-created_at')
        else:
            return Leave.objects.none()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        if MODELS_EXIST:
            context['leave_types'] = LeaveType.objects.all()
        else:
            context['leave_types'] = []
        return context


class LeaveApplyView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        if not MODELS_EXIST:
            return JsonResponse({'success': False, 'error': 'Models not available'})
        try:
            from .models import LeaveType
            leave_type_name = request.POST.get('leave_type')
            from_date_str = request.POST.get('from_date')
            to_date_str = request.POST.get('to_date')

            if not leave_type_name:
                return JsonResponse({'success': False, 'error': 'Leave type is required'})

            if not from_date_str or not to_date_str:
                return JsonResponse({'success': False, 'error': 'From and To dates are required'})

            # Parse dates from strings (HTML date inputs use YYYY-MM-DD)
            try:
                from_date = datetime.strptime(from_date_str, "%Y-%m-%d").date()
                to_date = datetime.strptime(to_date_str, "%Y-%m-%d").date()
            except ValueError:
                return JsonResponse({'success': False, 'error': 'Invalid date format'})

            # Get or create LeaveType by name
            try:
                leave_type, created = LeaveType.objects.get_or_create(name=leave_type_name.title())
            except Exception as e:
                return JsonResponse({'success': False, 'error': f'Error creating leave type: {str(e)}'})

            leave_data = {
                'leave_type': leave_type,
                'from_date': from_date,
                'to_date': to_date,
                'reason': request.POST.get('reason'),
                'status': 'pending'
            }
            
            # Check if admin is creating leave for someone else
            if request.user.role in ['superadmin', 'admin']:
                applicant_type = request.POST.get('applicant_type')
                applicant_id = request.POST.get('applicant_id')
                
                if applicant_type and applicant_id:
                    # Admin creating leave for someone else
                    leave_data['applicant_type'] = applicant_type
                    
                    if applicant_type == 'teacher':
                        leave_data['teacher_id'] = applicant_id
                    elif applicant_type == 'student':
                        leave_data['student_id'] = applicant_id
                    elif applicant_type == 'staff':
                        leave_data['staff_id'] = applicant_id
                    else:
                        return JsonResponse({'success': False, 'error': 'Invalid applicant type'})
                else:
                    # Admin applying for themselves (treated as staff)
                    leave_data['staff'] = request.user
                    leave_data['applicant_type'] = 'staff'
            elif request.user.role == 'teacher':
                leave_data['teacher'] = request.user
                leave_data['applicant_type'] = 'teacher'
            elif request.user.role == 'student':
                from students.models import Student
                student = Student.objects.get(user=request.user)
                leave_data['student'] = student
                leave_data['applicant_type'] = 'student'
            elif request.user.role == 'staff':
                leave_data['staff'] = request.user
                leave_data['applicant_type'] = 'staff'
            elif request.user.role in ['superadmin', 'admin']:
                # Admin applying for themselves (treated as staff)
                leave_data['staff'] = request.user
                leave_data['applicant_type'] = 'staff'
            else:
                return JsonResponse({'success': False, 'error': f'Invalid user role: {request.user.role}'})
            
            Leave.objects.create(**leave_data)
            return JsonResponse({'success': True})
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'success': False, 'error': str(e)})


class LeaveApproveView(LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        if not MODELS_EXIST:
            return JsonResponse({'success': False, 'error': 'Models not available'})
        try:
            leave = Leave.objects.get(pk=pk)
            leave.status = 'approved'
            leave.approved_by = request.user
            leave.save()
            return JsonResponse({'success': True})
        except Leave.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Leave not found'})


class LeaveRejectView(LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        if not MODELS_EXIST:
            return JsonResponse({'success': False, 'error': 'Models not available'})
        try:
            leave = Leave.objects.get(pk=pk)
            leave.status = 'rejected'
            leave.approved_by = request.user
            leave.save()
            return JsonResponse({'success': True})
        except Leave.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Leave not found'})


# API Views for fetching teachers, students, and staff
class TeachersAPIView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        teachers = User.objects.filter(role='teacher', is_active=True).values('id', 'first_name', 'last_name')
        data = [{'id': t['id'], 'name': f"{t['first_name']} {t['last_name']}"} for t in teachers]
        return JsonResponse(data, safe=False)


class StudentsAPIView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        from students.models import Student
        students = Student.objects.filter(is_active=True).select_related('user').values(
            'id', 'first_name', 'last_name'
        )
        data = [{'id': s['id'], 'name': f"{s['first_name']} {s['last_name']}"} for s in students]
        return JsonResponse(data, safe=False)


class StaffAPIView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        staff = User.objects.filter(role='staff', is_active=True).values('id', 'first_name', 'last_name')
        data = [{'id': s['id'], 'name': f"{s['first_name']} {s['last_name']}"} for s in staff]
        return JsonResponse(data, safe=False)
