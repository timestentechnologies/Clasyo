from django.shortcuts import render
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from academics.models import Class, Section
from students.models import Student
from datetime import date

# Check if models exist
try:
    from .models import StudentAttendance
    MODELS_EXIST = True
except ImportError:
    MODELS_EXIST = False
    class StudentAttendance:
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
        
        # Add existing attendance data for the selected date
        if MODELS_EXIST and context['selected_date'] and context['selected_class_id']:
            selected_date = context['selected_date']
            if isinstance(selected_date, str):
                from datetime import datetime
                selected_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
            
            context['existing_attendance'] = StudentAttendance.objects.filter(
                date=selected_date,
                student__current_class_id=context['selected_class_id']
            ).select_related('student')
            
            print(f"Found {context['existing_attendance'].count()} existing attendance records for {selected_date}")
        
        return context
    
    def post(self, request, *args, **kwargs):
        try:
            student_id = request.POST.get('student_id')
            attendance_date = request.POST.get('date', date.today())
            status = request.POST.get('status', 'present')
            
            print(f"Received attendance data: student_id={student_id}, date={attendance_date}, status={status}")
            
            if not MODELS_EXIST:
                return JsonResponse({'success': False, 'error': 'Attendance model not available'})
            
            # Validate required fields
            if not student_id:
                return JsonResponse({'success': False, 'error': 'Student ID is required'})
            
            if not attendance_date:
                return JsonResponse({'success': False, 'error': 'Date is required'})
            
            # Convert string date to date object if needed
            from datetime import datetime
            if isinstance(attendance_date, str):
                try:
                    attendance_date = datetime.strptime(attendance_date, '%Y-%m-%d').date()
                except ValueError:
                    return JsonResponse({'success': False, 'error': 'Invalid date format. Expected YYYY-MM-DD'})
            
            # Get student and school for the record
            try:
                student = Student.objects.get(id=student_id)
                print(f"Found student: {student.get_full_name()}")
            except Student.DoesNotExist:
                return JsonResponse({'success': False, 'error': f'Student with ID {student_id} not found'})
            
            # Create or update attendance record
            attendance, created = StudentAttendance.objects.update_or_create(
                student_id=student_id,
                date=attendance_date,
                defaults={
                    'status': status,
                    'note': request.POST.get('note', ''),
                    'class_name': student.current_class,
                    'section': student.section,
                    'marked_by': request.user
                }
            )
            
            print(f"Attendance record {'created' if created else 'updated'}: {attendance}")
            
            return JsonResponse({'success': True, 'created': created, 'attendance_id': attendance.id})
        except Exception as e:
            import traceback
            print(f"Error saving attendance: {e}")
            print(traceback.format_exc())
            return JsonResponse({'success': False, 'error': str(e), 'trace': traceback.format_exc()})


class AttendanceReportView(LoginRequiredMixin, ListView):
    template_name = 'attendance/attendance_report.html'
    context_object_name = 'attendance_records'
    
    def get_queryset(self):
        if MODELS_EXIST:
            return StudentAttendance.objects.all()
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
            return StudentAttendance.objects.filter(student_id=student_id).order_by('-date')
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
            return StudentAttendance.objects.filter(student=student).order_by('-date')
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
