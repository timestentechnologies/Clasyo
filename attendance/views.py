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
    context_object_name = 'attendance_records'
    
    def get_queryset(self):
        if MODELS_EXIST:
            return Attendance.objects.all()
        return []
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        context['classes'] = Class.objects.filter(is_active=True)
        context['today'] = date.today()
        return context
    
    def post(self, request, *args, **kwargs):
        try:
            student_id = request.POST.get('student_id')
            attendance_date = request.POST.get('date', date.today())
            status = request.POST.get('status', 'present')
            
            Attendance.objects.update_or_create(
                student_id=student_id,
                date=attendance_date,
                defaults={'status': status, 'note': request.POST.get('note', '')}
            )
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})


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
