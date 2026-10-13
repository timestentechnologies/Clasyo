from django.contrib import admin
from .models import (
    Class, Section, ClassTeacherAssignment, Subject, OptionalSubject, AssignedSubject,
    ClassRoom, ClassTime, ClassRoutine, House, StudyMaterial,
    Syllabus, CurriculumUnit, CurriculumTopic, Assignment, AssignmentSubmission
)


@admin.register(Class)
class ClassAdmin(admin.ModelAdmin):
    list_display = ['name', 'numeric_name', 'order', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name']


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ['name', 'class_name', 'class_teacher', 'max_students', 'is_active']
    list_filter = ['class_name', 'is_active']
    search_fields = ['name', 'class_name__name']


@admin.register(ClassTeacherAssignment)
class ClassTeacherAssignmentAdmin(admin.ModelAdmin):
    list_display = ['section', 'teacher', 'academic_year', 'is_active', 'assigned_date']
    list_filter = ['academic_year', 'is_active']
    search_fields = ['section__name', 'section__class_name__name', 'teacher__username', 'teacher__first_name', 'teacher__last_name']


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'subject_type', 'credits', 'is_active']
    list_filter = ['subject_type', 'is_active']
    search_fields = ['name', 'code']


@admin.register(AssignedSubject)
class AssignedSubjectAdmin(admin.ModelAdmin):
    list_display = ['subject', 'class_name', 'section', 'teacher', 'academic_year', 'is_active']
    list_filter = ['class_name', 'academic_year', 'is_active']
    search_fields = ['subject__name', 'class_name__name']


@admin.register(ClassRoom)
class ClassRoomAdmin(admin.ModelAdmin):
    list_display = ['room_number', 'name', 'room_type', 'capacity', 'floor', 'building', 'is_active']
    list_filter = ['room_type', 'building', 'is_active']
    search_fields = ['room_number', 'name']


@admin.register(ClassRoutine)
class ClassRoutineAdmin(admin.ModelAdmin):
    list_display = ['class_name', 'section', 'day_of_week', 'class_time', 'subject', 'teacher', 'room']
    list_filter = ['class_name', 'day_of_week', 'academic_year']
    search_fields = ['class_name__name', 'subject__name', 'teacher__email']


@admin.register(House)
class HouseAdmin(admin.ModelAdmin):
    list_display = ['name', 'color', 'captain', 'teacher_incharge', 'total_points', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name']


@admin.register(StudyMaterial)
class StudyMaterialAdmin(admin.ModelAdmin):
    list_display = ['title', 'content_type', 'class_name', 'subject', 'uploaded_by', 'uploaded_at', 'download_count']
    list_filter = ['content_type', 'class_name', 'uploaded_at']
    search_fields = ['title', 'description']


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ['title', 'class_name', 'subject', 'assigned_date', 'due_date', 'max_marks', 'created_by']
    list_filter = ['class_name', 'subject', 'assigned_date']
    search_fields = ['title', 'description']


class CurriculumTopicInline(admin.TabularInline):
    model = CurriculumTopic
    extra = 1


@admin.register(CurriculumUnit)
class CurriculumUnitAdmin(admin.ModelAdmin):
    list_display = ['title', 'syllabus', 'unit_number', 'order', 'is_active']
    list_filter = ['is_active', 'syllabus__class_name', 'syllabus__subject']
    search_fields = ['title', 'description', 'syllabus__title']
    inlines = [CurriculumTopicInline]


@admin.register(CurriculumTopic)
class CurriculumTopicAdmin(admin.ModelAdmin):
    list_display = ['title', 'unit', 'topic_number', 'estimated_periods', 'order', 'is_active']
    list_filter = ['is_active', 'unit__syllabus']
    search_fields = ['title', 'learning_objectives', 'unit__title']

