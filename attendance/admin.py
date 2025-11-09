from django.contrib import admin
from .models import StudentAttendance, StaffAttendance


@admin.register(StudentAttendance)
class StudentAttendanceAdmin(admin.ModelAdmin):
    list_display = ['student', 'date', 'status', 'class_name', 'section', 'marked_by']
    list_filter = ['date', 'status', 'class_name', 'section']
    search_fields = ['student__first_name', 'student__last_name', 'student__admission_number']
    date_hierarchy = 'date'
    readonly_fields = ['created_at', 'updated_at']


@admin.register(StaffAttendance)
class StaffAttendanceAdmin(admin.ModelAdmin):
    list_display = ['staff', 'date', 'status', 'check_in_time', 'check_out_time', 'marked_by']
    list_filter = ['date', 'status', 'staff__role']
    search_fields = ['staff__first_name', 'staff__last_name', 'staff__email']
    date_hierarchy = 'date'
    readonly_fields = ['created_at', 'updated_at']
