from django.contrib import admin

from .models import StudentSubject, StudentClassEnrollment


@admin.register(StudentClassEnrollment)
class StudentClassEnrollmentAdmin(admin.ModelAdmin):
    list_display = ['student', 'class_name', 'section', 'academic_year', 'school', 'status', 'enrolled_date']
    list_filter = ['academic_year', 'school', 'class_name', 'status']
    search_fields = ['student__admission_number', 'student__first_name', 'student__last_name', 'roll_number']


@admin.register(StudentSubject)
class StudentSubjectAdmin(admin.ModelAdmin):
    list_display = ['student', 'subject', 'academic_year', 'school', 'is_active', 'created_at']
    list_filter = ['academic_year', 'school', 'is_active']
    search_fields = ['student__admission_number', 'student__first_name', 'student__last_name', 'subject__name', 'subject__code']
