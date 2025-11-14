from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from tenants.models import School


class LessonPlanTemplate(models.Model):
    """Lesson Plan Template Model"""
    TEMPLATE_TYPES = [
        ('standard', 'Standard'),
        ('project_based', 'Project Based Learning'),
        ('inquiry_based', 'Inquiry Based Learning'),
        ('direct_instruction', 'Direct Instruction'),
        ('flipped_classroom', 'Flipped Classroom'),
        ('differentiated', 'Differentiated Instruction'),
        ('custom', 'Custom'),
    ]

    name = models.CharField(_('Template Name'), max_length=100)
    description = models.TextField(_('Description'), blank=True)
    template_type = models.CharField(_('Template Type'), max_length=30, choices=TEMPLATE_TYPES, default='standard')
    
    # School association (for multi-tenant)
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='lesson_plan_templates', null=True, blank=True)
    
    # Template structure (stored as JSON)
    structure = models.JSONField(_('Template Structure'), default=dict)
    
    is_active = models.BooleanField(_('Is Active'), default=True)
    is_default = models.BooleanField(_('Is Default'), default=False)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, 
                                 null=True, related_name='created_lesson_templates')
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Lesson Plan Template')
        verbose_name_plural = _('Lesson Plan Templates')
        ordering = ['-is_default', 'name']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        # If this template is set as default, unset default for other templates
        if self.is_default:
            LessonPlanTemplate.objects.filter(
                school=self.school, 
                is_default=True
            ).exclude(pk=self.pk).update(is_default=False)
            
        super().save(*args, **kwargs)


class LessonPlan(models.Model):
    """Lesson Plan Model"""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('review', 'In Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('completed', 'Completed'),
    ]
    
    title = models.CharField(_('Lesson Title'), max_length=200)
    description = models.TextField(_('Description'), blank=True)
    
    # Academic references
    class_ref = models.ForeignKey('academics.Class', on_delete=models.CASCADE, 
                                related_name='lesson_plans')
    section = models.ForeignKey('academics.Section', on_delete=models.CASCADE, 
                              related_name='lesson_plans', null=True, blank=True)
    subject = models.ForeignKey('academics.Subject', on_delete=models.CASCADE, 
                              related_name='lesson_plans')
    academic_year = models.ForeignKey('core.AcademicYear', on_delete=models.CASCADE, 
                                     related_name='lesson_plans')
    
    # Template reference
    template = models.ForeignKey(LessonPlanTemplate, on_delete=models.SET_NULL, 
                               null=True, blank=True, related_name='lesson_plans')
    
    # Lesson details
    duration_minutes = models.PositiveIntegerField(_('Duration (minutes)'), default=60)
    planned_date = models.DateField(_('Planned Date'))
    learning_objectives = models.TextField(_('Learning Objectives'))
    materials_resources = models.TextField(_('Materials & Resources'), blank=True)
    
    # Lesson structure
    introduction = models.TextField(_('Introduction'), blank=True)
    main_content = models.TextField(_('Main Content'))
    activities = models.TextField(_('Activities'), blank=True)
    assessment = models.TextField(_('Assessment'), blank=True)
    differentiation = models.TextField(_('Differentiation Strategies'), blank=True)
    conclusion = models.TextField(_('Conclusion'), blank=True)
    homework = models.TextField(_('Homework Assignment'), blank=True)
    notes = models.TextField(_('Additional Notes'), blank=True)
    
    # Attachments
    attachments = models.FileField(_('Attachments'), upload_to='lesson_plans/', blank=True, null=True)
    
    # Status tracking
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default='draft')
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, 
                                  null=True, blank=True, related_name='approved_lesson_plans')
    approved_at = models.DateTimeField(_('Approved At'), null=True, blank=True)
    
    # Execution tracking
    is_executed = models.BooleanField(_('Is Executed'), default=False)
    execution_date = models.DateField(_('Execution Date'), null=True, blank=True)
    execution_notes = models.TextField(_('Execution Notes'), blank=True)
    
    # Creator and timestamps
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_lesson_plans')
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Lesson Plan')
        verbose_name_plural = _('Lesson Plans')
        ordering = ['planned_date']
    
    def __str__(self):
        return f"{self.title} - {self.subject.name} ({self.class_ref.name})"


class LessonPlanStandard(models.Model):
    """Standards addressed in the lesson plan"""
    lesson_plan = models.ForeignKey(LessonPlan, on_delete=models.CASCADE, related_name='standards')
    standard_code = models.CharField(_('Standard Code'), max_length=50)
    description = models.TextField(_('Standard Description'))
    
    class Meta:
        verbose_name = _('Lesson Plan Standard')
        verbose_name_plural = _('Lesson Plan Standards')
    
    def __str__(self):
        return self.standard_code


class LessonPlanFeedback(models.Model):
    """Feedback on lesson plans"""
    lesson_plan = models.ForeignKey(LessonPlan, on_delete=models.CASCADE, related_name='feedback')
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='provided_feedback')
    feedback = models.TextField(_('Feedback'))
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('Lesson Plan Feedback')
        verbose_name_plural = _('Lesson Plan Feedback')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Feedback on {self.lesson_plan.title} by {self.reviewer.get_full_name()}"


class LessonPlanResource(models.Model):
    """Resources attached to lesson plans"""
    RESOURCE_TYPES = [
        ('document', 'Document'),
        ('presentation', 'Presentation'),
        ('worksheet', 'Worksheet'),
        ('video', 'Video'),
        ('audio', 'Audio'),
        ('image', 'Image'),
        ('link', 'Web Link'),
        ('other', 'Other'),
    ]
    
    lesson_plan = models.ForeignKey(LessonPlan, on_delete=models.CASCADE, related_name='resources')
    title = models.CharField(_('Resource Title'), max_length=100)
    resource_type = models.CharField(_('Resource Type'), max_length=20, choices=RESOURCE_TYPES)
    file = models.FileField(_('File'), upload_to='lesson_plan_resources/', blank=True, null=True)
    url = models.URLField(_('URL'), blank=True)
    description = models.TextField(_('Description'), blank=True)
    
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='uploaded_lesson_resources')
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('Lesson Plan Resource')
        verbose_name_plural = _('Lesson Plan Resources')
    
    def __str__(self):
        return self.title
