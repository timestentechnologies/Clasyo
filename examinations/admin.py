from django.contrib import admin
from .models import (
    Exam, ExamQuestion, ExamFile, Grade, ExamMark, 
    ExamResult, ExamSubmission, QuestionAnswer
)


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ['name', 'exam_type', 'start_date', 'end_date', 'is_published', 'class_assigned', 'subject']
    list_filter = ['exam_type', 'is_published', 'is_online', 'class_assigned']
    search_fields = ['name']
    date_hierarchy = 'start_date'


@admin.register(ExamQuestion)
class ExamQuestionAdmin(admin.ModelAdmin):
    list_display = ['exam', 'question_type', 'order', 'points']
    list_filter = ['question_type', 'exam']
    search_fields = ['question_text']
    ordering = ['exam', 'order']


@admin.register(ExamSubmission)
class ExamSubmissionAdmin(admin.ModelAdmin):
    list_display = ['student', 'exam', 'status', 'percentage', 'submitted_at', 'graded_by']
    list_filter = ['status', 'exam', 'graded_at']
    search_fields = ['student__first_name', 'student__last_name', 'exam__name']
    readonly_fields = ['started_at', 'submitted_at', 'graded_at']
    date_hierarchy = 'submitted_at'


@admin.register(QuestionAnswer)
class QuestionAnswerAdmin(admin.ModelAdmin):
    list_display = ['submission', 'question', 'is_correct', 'points_awarded']
    list_filter = ['is_correct', 'question__question_type']
    search_fields = ['submission__student__first_name', 'question__question_text']


@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = ['name', 'min_percentage', 'max_percentage', 'point']
    ordering = ['-min_percentage']


@admin.register(ExamMark)
class ExamMarkAdmin(admin.ModelAdmin):
    list_display = ['student', 'exam', 'subject', 'marks_obtained', 'total_marks', 'percentage']
    list_filter = ['exam', 'subject']
    search_fields = ['student__first_name', 'student__last_name']


@admin.register(ExamResult)
class ExamResultAdmin(admin.ModelAdmin):
    list_display = ['student', 'exam', 'percentage', 'grade']
    list_filter = ['exam', 'grade']
    search_fields = ['student__first_name', 'student__last_name']
    ordering = ['-percentage']


admin.site.register(ExamFile)
