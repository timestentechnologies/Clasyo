from django.db import models
from django.utils.translation import gettext_lazy as _
from tenants.models import School
from students.models import Student
from academics.models import Class, Section
from accounts.models import User


class StudentAttendance(models.Model):
    """Track student attendance"""
    STATUS_CHOICES = [
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
        ('excused', 'Excused'),
        ('sick', 'Sick'),
    ]
    
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='student_attendance')
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='attendance_records')
    class_name = models.ForeignKey(Class, on_delete=models.CASCADE, null=True, blank=True)
    section = models.ForeignKey(Section, on_delete=models.CASCADE, null=True, blank=True)
    
    date = models.DateField(_('Attendance Date'))
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default='present')
    
    note = models.TextField(_('Note'), blank=True)
    marked_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='marked_attendance')
    
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Student Attendance')
        verbose_name_plural = _('Student Attendance Records')
        unique_together = ['student', 'date']
        ordering = ['-date', 'student__admission_number']
        indexes = [
            models.Index(fields=['date', 'status']),
            models.Index(fields=['student', 'date']),
        ]
    
    def __str__(self):
        return f"{self.student.get_full_name()} - {self.date} - {self.status}"


class StaffAttendance(models.Model):
    """Track teacher and staff attendance"""
    STATUS_CHOICES = [
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
        ('on_leave', 'On Leave'),
        ('half_day', 'Half Day'),
    ]
    
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='staff_attendance')
    staff = models.ForeignKey(User, on_delete=models.CASCADE, related_name='attendance_records',
                            limit_choices_to={'role__in': ['teacher', 'admin', 'staff']})
    
    date = models.DateField(_('Attendance Date'))
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default='present')
    
    check_in_time = models.TimeField(_('Check In Time'), null=True, blank=True)
    check_out_time = models.TimeField(_('Check Out Time'), null=True, blank=True)
    
    note = models.TextField(_('Note'), blank=True)
    marked_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='marked_staff_attendance')
    
    # Link to leave application if applicable
    leave_application = models.ForeignKey('leave_management.LeaveApplication', 
                                        on_delete=models.SET_NULL, null=True, blank=True,
                                        related_name='attendance_records')
    
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Staff Attendance')
        verbose_name_plural = _('Staff Attendance Records')
        unique_together = ['staff', 'date']
        ordering = ['-date', 'staff__first_name']
        indexes = [
            models.Index(fields=['date', 'status']),
            models.Index(fields=['staff', 'date']),
        ]
    
    def __str__(self):
        return f"{self.staff.get_full_name()} - {self.date} - {self.status}"
    
    def calculate_hours_worked(self):
        """Calculate hours worked based on check-in and check-out times"""
        if self.check_in_time and self.check_out_time:
            from datetime import datetime, timedelta
            check_in = datetime.combine(datetime.today(), self.check_in_time)
            check_out = datetime.combine(datetime.today(), self.check_out_time)
            duration = check_out - check_in
            return duration.total_seconds() / 3600  # Convert to hours
        return 0


# Keep backward compatibility
Attendance = StudentAttendance
