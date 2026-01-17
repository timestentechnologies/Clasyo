from django import forms
from .models import LessonPlan, LessonPlanResource

class LessonPlanForm(forms.ModelForm):
    class Meta:
        model = LessonPlan
        fields = [
            'title', 'subject', 'class_ref', 'section', 'grade_level',
            'planned_date', 'duration_minutes', 'lesson_number', 'academic_year', 'unit_title',
            'template', 'learning_objectives', 'materials_resources', 'introduction',
            'main_content', 'activities', 'assessment', 'conclusion',
            'homework', 'differentiation', 'notes'
        ]

class LessonPlanResourceForm(forms.ModelForm):
    class Meta:
        model = LessonPlanResource
        fields = ['title', 'resource_type', 'file', 'url', 'description']

LessonPlanResourceFormSet = forms.inlineformset_factory(
    LessonPlan, 
    LessonPlanResource,
    form=LessonPlanResourceForm,
    extra=0,
    can_delete=True
)
