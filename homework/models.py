from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from tenants.models import School
from django.utils import timezone


class HomeworkAssignment(models.Model):
    """Homework Assignment Model"""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('closed', 'Closed'),
        ('archived', 'Archived'),
    ]
    
    SUBMISSION_TYPE_CHOICES = [
        ('text', 'Text Entry'),
        ('file', 'File Upload'),
        ('both', 'Text & File'),
        ('link', 'Link/URL'),
        ('none', 'No Online Submission'),
    ]
    
    # Basic Information
    title = models.CharField(_('Title'), max_length=200)
    description = models.TextField(_('Description'))
    instructions = models.TextField(_('Instructions'), blank=True)
    
    # Academic references
    class_ref = models.ForeignKey('academics.Class', on_delete=models.CASCADE, 
                                related_name='homework_assignments')
    section = models.ForeignKey('academics.Section', on_delete=models.CASCADE, 
                              related_name='homework_assignments', null=True, blank=True)
    subject = models.ForeignKey('academics.Subject', on_delete=models.CASCADE, 
                              related_name='homework_assignments')
    academic_year = models.ForeignKey('core.AcademicYear', on_delete=models.CASCADE, 
                                     related_name='homework_assignments')
    
    # Dates
    assigned_date = models.DateField(_('Assigned Date'), default=timezone.now)
    due_date = models.DateTimeField(_('Due Date'))
    
    # Grading
    points = models.DecimalField(_('Points'), max_digits=6, decimal_places=2, default=100)
    grading_type = models.CharField(_('Grading Type'), max_length=20, 
                                 choices=[('points', 'Points'), ('letter', 'Letter Grade'), 
                                         ('pass_fail', 'Pass/Fail')],
                                 default='points')
    is_graded = models.BooleanField(_('Is Graded'), default=True)
    
    # Submission settings
    submission_type = models.CharField(_('Submission Type'), max_length=10, 
                                     choices=SUBMISSION_TYPE_CHOICES, default='both')
    allow_late_submissions = models.BooleanField(_('Allow Late Submissions'), default=True)
    late_penalty_percentage = models.DecimalField(_('Late Penalty (%)'), max_digits=5, decimal_places=2, default=0)
    max_attempts = models.PositiveSmallIntegerField(_('Maximum Attempts'), default=1, 
                                                  help_text=_('0 for unlimited attempts'))
    
    # Files
    attachment = models.FileField(_('Attachment'), upload_to='homework/attachments/', blank=True, null=True)
    
    # Status
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default='draft')
    is_published = models.BooleanField(_('Is Published'), default=False)
    published_at = models.DateTimeField(_('Published At'), null=True, blank=True)
    
    # School association
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='homework_assignments', null=True, blank=True)
    
    # Creator and timestamps
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_homework')
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Homework Assignment')
        verbose_name_plural = _('Homework Assignments')
        ordering = ['-assigned_date']
    
    def __str__(self):
        return f"{self.title} - {self.subject.name} ({self.class_ref.name})"
    
    def save(self, *args, **kwargs):
        # If publishing, set published timestamp
        if self.is_published and not self.published_at:
            self.published_at = timezone.now()
            self.status = 'published'
        
        # If unpublishing, reset timestamp
        if not self.is_published and self.published_at:
            self.published_at = None
            
        # If past due date, close assignment
        if self.status == 'published' and timezone.now() > self.due_date:
            self.status = 'closed'
            
        super().save(*args, **kwargs)
    
    @property
    def is_past_due(self):
        return timezone.now() > self.due_date
    
    @property
    def days_until_due(self):
        if self.is_past_due:
            return 0
        delta = self.due_date - timezone.now()
        return delta.days


class HomeworkSubmission(models.Model):
    """Homework Submission Model"""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('late', 'Late Submission'),
        ('graded', 'Graded'),
        ('returned', 'Returned'),
    ]
    
    # Submission relationship
    homework = models.ForeignKey(HomeworkAssignment, on_delete=models.CASCADE, related_name='submissions')
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='homework_submissions')
    
    # Submission content
    submission_text = models.TextField(_('Submission Text'), blank=True)
    submission_file = models.FileField(_('Submission File'), upload_to='homework/submissions/', blank=True, null=True)
    submission_url = models.URLField(_('Submission URL'), blank=True)
    
    # Status and dates
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default='draft')
    submitted_at = models.DateTimeField(_('Submitted At'), null=True, blank=True)
    attempt_number = models.PositiveSmallIntegerField(_('Attempt Number'), default=1)
    is_late = models.BooleanField(_('Is Late'), default=False)
    
    # Grading
    points_earned = models.DecimalField(_('Points Earned'), max_digits=6, decimal_places=2, null=True, blank=True)
    grade = models.CharField(_('Grade'), max_length=10, blank=True)
    feedback = models.TextField(_('Feedback'), blank=True)
    graded_at = models.DateTimeField(_('Graded At'), null=True, blank=True)
    graded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, 
                                null=True, blank=True, related_name='homework_graded_submissions')
    
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Homework Submission')
        verbose_name_plural = _('Homework Submissions')
        ordering = ['-submitted_at']
        unique_together = ['homework', 'student', 'attempt_number']
    
    def __str__(self):
        return f"{self.student.get_full_name()} - {self.homework.title}"
    
    def save(self, *args, **kwargs):
        # If this is a new submission being submitted, set timestamp
        if self.status == 'submitted' and not self.submitted_at:
            self.submitted_at = timezone.now()
            
            # Check if late
            if timezone.now() > self.homework.due_date:
                self.is_late = True
                if self.homework.allow_late_submissions:
                    self.status = 'late'
        
        # If this is being graded, set timestamp
        if self.status == 'graded' and not self.graded_at:
            self.graded_at = timezone.now()
            
        super().save(*args, **kwargs)
    
    @property
    def percentage_score(self):
        if self.points_earned is None or self.homework.points == 0:
            return None
        return (self.points_earned / self.homework.points) * 100


class HomeworkComment(models.Model):
    """Comments on homework submissions"""
    submission = models.ForeignKey(HomeworkSubmission, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='homework_comments')
    text = models.TextField(_('Comment'))
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('Homework Comment')
        verbose_name_plural = _('Homework Comments')
        ordering = ['created_at']
    
    def __str__(self):
        return f"Comment by {self.author.get_full_name()} on {self.submission}"


class HomeworkResource(models.Model):
    """Resources attached to homework assignments"""
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
    
    homework = models.ForeignKey(HomeworkAssignment, on_delete=models.CASCADE, related_name='resources')
    title = models.CharField(_('Resource Title'), max_length=100)
    resource_type = models.CharField(_('Resource Type'), max_length=20, choices=RESOURCE_TYPES)
    file = models.FileField(_('File'), upload_to='homework/resources/', blank=True, null=True)
    url = models.URLField(_('URL'), blank=True)
    description = models.TextField(_('Description'), blank=True)
    
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='uploaded_homework_resources')
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('Homework Resource')
        verbose_name_plural = _('Homework Resources')
    
    def __str__(self):
        return self.title
