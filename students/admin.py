from django.contrib import admin

from .models import StudentSubject


@admin.register(StudentSubject)
class StudentSubjectAdmin(admin.ModelAdmin):
    list_display = ['student', 'subject', 'academic_year', 'school', 'is_active', 'created_at']
    list_filter = ['academic_year', 'school', 'is_active']
    search_fields = ['student__admission_number', 'student__first_name', 'student__last_name', 'subject__name', 'subject__code']
