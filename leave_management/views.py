from django.shortcuts import render
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views import View
from accounts.models import User

# Check if models exist
try:
    from .models import Leave
    MODELS_EXIST = True
except ImportError:
    MODELS_EXIST = False
    class Leave:
        pass


class LeaveListView(LoginRequiredMixin, ListView):
    template_name = 'leave_management/leave_list.html'
    context_object_name = 'leaves'
    
    def get_queryset(self):
        if not MODELS_EXIST:
            return []
        user = self.request.user
        if user.role in ['super_admin', 'school_admin']:
            return Leave.objects.all().order_by('-created_at')
        elif user.role == 'teacher':
            return Leave.objects.filter(teacher=user).order_by('-created_at')
        elif user.role == 'student':
            from students.models import Student
            try:
                student = Student.objects.get(user=user)
                return Leave.objects.filter(student=student).order_by('-created_at')
            except Student.DoesNotExist:
                return Leave.objects.none()
        elif user.role == 'staff':
            return Leave.objects.filter(staff=user).order_by('-created_at')
        else:
            return Leave.objects.none()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        return context


class LeaveApplyView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        if not MODELS_EXIST:
            return JsonResponse({'success': False, 'error': 'Models not available'})
        try:
            from .models import LeaveType
            leave_data = {
                'leave_type_id': request.POST.get('leave_type'),
                'from_date': request.POST.get('from_date'),
                'to_date': request.POST.get('to_date'),
                'reason': request.POST.get('reason'),
                'status': 'pending'
            }
            
            # Check if admin is creating leave for someone else
            if request.user.role in ['super_admin', 'school_admin']:
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
            else:
                return JsonResponse({'success': False, 'error': 'Invalid user role'})
            
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
