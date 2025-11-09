from django.shortcuts import render
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from academics.models import Class, Section
from students.models import Student
from datetime import date

# Check if models exist
try:
    from .models import Attendance
    MODELS_EXIST = True
except ImportError:
    MODELS_EXIST = False
    class Attendance:
        pass


class MarkAttendanceView(LoginRequiredMixin, ListView):
    template_name = 'attendance/mark_attendance.html'
    context_object_name = 'students'
    
    def get_queryset(self):
        # Get filter parameters
        class_id = self.request.GET.get('class_id')
        section_id = self.request.GET.get('section_id')
        
        if not class_id:
            return []
        
        # Start with students query
        queryset = Student.objects.filter(is_active=True, current_class_id=class_id)
        
        # Filter by section if provided
        if section_id:
            queryset = queryset.filter(section_id=section_id)
        
        return queryset.order_by('roll_number', 'first_name')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        context['classes'] = Class.objects.filter(is_active=True).order_by('order', 'name')
        context['today'] = date.today()
        context['selected_date'] = self.request.GET.get('date', date.today())
        context['selected_class_id'] = self.request.GET.get('class_id', '')
        context['selected_section_id'] = self.request.GET.get('section_id', '')
        return context
    
    def post(self, request, *args, **kwargs):
        try:
            student_id = request.POST.get('student_id')
            attendance_date = request.POST.get('date', date.today())
            status = request.POST.get('status', 'present')
            
            if not MODELS_EXIST:
                return JsonResponse({'success': False, 'error': 'Attendance model not available'})
            
            # Get student and school for the record
            student = Student.objects.get(id=student_id)
            
            Attendance.objects.update_or_create(
                student_id=student_id,
                date=attendance_date,
                defaults={
                    'status': status,
                    'note': request.POST.get('note', ''),
                    'school': student.school,
                    'class_name': student.current_class,
                    'section': student.section,
                    'marked_by': request.user
                }
            )
            return JsonResponse({'success': True})
        except Exception as e:
            import traceback
            return JsonResponse({'success': False, 'error': str(e), 'trace': traceback.format_exc()})


class AttendanceReportView(LoginRequiredMixin, ListView):
    template_name = 'attendance/attendance_report.html'
    context_object_name = 'attendance_records'
    
    def get_queryset(self):
        if MODELS_EXIST:
            return Attendance.objects.all()
        return []
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        context['classes'] = Class.objects.filter(is_active=True)
        context['students'] = Student.objects.filter(is_active=True)
        return context


class StudentAttendanceView(LoginRequiredMixin, ListView):
    template_name = 'attendance/student_attendance.html'
    context_object_name = 'attendance_records'
    
    def get_queryset(self):
        if MODELS_EXIST:
            student_id = self.kwargs.get('student_id')
            return Attendance.objects.filter(student_id=student_id).order_by('-date')
        return []
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        student_id = self.kwargs.get('student_id')
        context['student'] = Student.objects.get(pk=student_id)
        
        # Calculate attendance percentage
        total = self.get_queryset().count()
        present = self.get_queryset().filter(status='present').count()
        context['attendance_percentage'] = (present / total * 100) if total > 0 else 0
        return context


class MyAttendanceView(LoginRequiredMixin, ListView):
    """View for students to see their own attendance"""
    template_name = 'attendance/my_attendance.html'
    context_object_name = 'attendance_records'
    paginate_by = 30
    
    def get_queryset(self):
        if MODELS_EXIST and hasattr(self.request.user, 'student_profile'):
            student = self.request.user.student_profile
            return Attendance.objects.filter(student=student).order_by('-date')
        return []
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        
        if hasattr(self.request.user, 'student_profile'):
            context['student'] = self.request.user.student_profile
            
            # Calculate attendance statistics
            queryset = self.get_queryset()
            total = queryset.count()
            present = queryset.filter(status='present').count()
            absent = queryset.filter(status='absent').count()
            late = queryset.filter(status='late').count()
            
            context['total_days'] = total
            context['present_days'] = present
            context['absent_days'] = absent
            context['late_days'] = late
            context['attendance_percentage'] = (present / total * 100) if total > 0 else 0
        
        return context
