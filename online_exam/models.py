from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from tenants.models import School
from django.utils import timezone
from ckeditor.fields import RichTextField
from django.db.models.signals import post_save
from django.dispatch import receiver
import random
from academics.models import Subject, Class, Section
from students.models import Student


class OnlineExam(models.Model):
    """Online Exam model"""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('archived', 'Archived'),
    ]
    
    DIFFICULTY_CHOICES = [
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard'),
        ('mixed', 'Mixed'),
    ]
    
    title = models.CharField(_('Exam Title'), max_length=200)
    description = models.TextField(_('Description'), blank=True)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='online_exams')
    class_ref = models.ForeignKey(Class, on_delete=models.CASCADE, verbose_name=_('Class'), related_name='online_exams')
    section = models.ForeignKey(Section, on_delete=models.CASCADE, null=True, blank=True, related_name='online_exams')
    
    # Exam configuration
    instructions = RichTextField(_('Exam Instructions'), blank=True)
    start_time = models.DateTimeField(_('Start Time'))
    end_time = models.DateTimeField(_('End Time'))
    duration_minutes = models.PositiveIntegerField(_('Duration (minutes)'))
    passing_percentage = models.DecimalField(_('Passing Percentage'), max_digits=5, decimal_places=2, default=50.00)
    total_marks = models.PositiveIntegerField(_('Total Marks'), default=0)
    negative_marking = models.BooleanField(_('Negative Marking'), default=False)
    negative_mark_value = models.DecimalField(_('Marks Deducted per Wrong Answer'), max_digits=5, decimal_places=2, default=0.00)
    is_randomized = models.BooleanField(_('Randomize Questions'), default=True)
    allow_attempt_review = models.BooleanField(_('Allow Attempt Review'), default=True)
    difficulty_level = models.CharField(_('Difficulty Level'), max_length=10, choices=DIFFICULTY_CHOICES, default='medium')
    
    # Settings
    is_published = models.BooleanField(_('Is Published'), default=False)
    status = models.CharField(_('Status'), max_length=15, choices=STATUS_CHOICES, default='draft')
    publish_results = models.BooleanField(_('Publish Results'), default=False)
    show_answer_key = models.BooleanField(_('Show Answer Key After Exam'), default=False)
    require_webcam = models.BooleanField(_('Require Webcam'), default=False)
    prevent_tab_switching = models.BooleanField(_('Prevent Tab Switching'), default=True)
    max_attempts = models.PositiveSmallIntegerField(_('Maximum Attempts Allowed'), default=1)
    
    # School association for multi-tenant support
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='online_exams', null=True, blank=True)
    
    # Metadata
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_exams')
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Online Exam')
        verbose_name_plural = _('Online Exams')
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        # Update status based on time
        now = timezone.now()
        if self.is_published:
            if now < self.start_time:
                self.status = 'published'
            elif self.start_time <= now <= self.end_time:
                self.status = 'in_progress'
            elif now > self.end_time:
                self.status = 'completed'
                
        super().save(*args, **kwargs)
    
    @property
    def is_past_due(self):
        return timezone.now() > self.end_time
    
    @property
    def has_started(self):
        return timezone.now() >= self.start_time
    
    @property
    def is_active(self):
        now = timezone.now()
        return self.is_published and self.start_time <= now <= self.end_time
    
    @property
    def question_count(self):
        return self.questions.count()
    
    @property
    def attempts_count(self):
        return self.attempts.count()
    
    @property
    def highest_score(self):
        highest = self.attempts.filter(is_completed=True).order_by('-score').first()
        return highest.score if highest else 0
    
    @property
    def average_score(self):
        from django.db.models import Avg
        return self.attempts.filter(is_completed=True).aggregate(avg=Avg('score'))['avg']


class ExamQuestion(models.Model):
    """Question for online exam"""
    QUESTION_TYPE_CHOICES = [
        ('mcq_single', 'Multiple Choice (Single Answer)'),
        ('mcq_multiple', 'Multiple Choice (Multiple Answers)'),
        ('true_false', 'True or False'),
        ('short_answer', 'Short Answer'),
        ('essay', 'Essay/Long Answer'),
        ('matching', 'Matching'),
        ('fill_blank', 'Fill in the Blank'),
    ]
    
    exam = models.ForeignKey(OnlineExam, on_delete=models.CASCADE, related_name='questions')
    question_text = RichTextField(_('Question'))
    question_type = models.CharField(_('Question Type'), max_length=15, choices=QUESTION_TYPE_CHOICES)
    image = models.ImageField(_('Question Image'), upload_to='exam_questions/', blank=True, null=True)
    marks = models.DecimalField(_('Marks'), max_digits=5, decimal_places=2, default=1.00)
    is_required = models.BooleanField(_('Is Required'), default=True)
    explanation = models.TextField(_('Explanation'), blank=True, help_text=_('Explanation of the correct answer'))
    order = models.PositiveIntegerField(_('Order'), default=0)
    
    # Metadata
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_questions')
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Exam Question')
        verbose_name_plural = _('Exam Questions')
        ordering = ['exam', 'order']
    
    def __str__(self):
        return f"{self.exam.title} - Q{self.order}"
    
    @property
    def has_choices(self):
        return self.question_type in ['mcq_single', 'mcq_multiple', 'true_false', 'matching']
    
    @property
    def correct_answers(self):
        if self.question_type == 'true_false':
            return [c.choice_text for c in self.choices.filter(is_correct=True)]
        elif self.question_type in ['mcq_single', 'mcq_multiple']:
            return [c.choice_text for c in self.choices.filter(is_correct=True)]
        return []


class QuestionChoice(models.Model):
    """Answer choice for a question"""
    question = models.ForeignKey(ExamQuestion, on_delete=models.CASCADE, related_name='choices')
    choice_text = models.CharField(_('Choice Text'), max_length=500)
    is_correct = models.BooleanField(_('Is Correct'), default=False)
    order = models.PositiveIntegerField(_('Order'), default=0)
    
    class Meta:
        verbose_name = _('Question Choice')
        verbose_name_plural = _('Question Choices')
        ordering = ['question', 'order']
    
    def __str__(self):
        return f"{self.question} - Choice {self.order}"


class ExamAttempt(models.Model):
    """Student's attempt at an exam"""
    STATUS_CHOICES = [
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('submitted', 'Submitted'),
        ('auto_submitted', 'Auto Submitted'),
        ('graded', 'Graded'),
    ]
    
    exam = models.ForeignKey(OnlineExam, on_delete=models.CASCADE, related_name='attempts')
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='exam_attempts')
    started_at = models.DateTimeField(_('Started At'), null=True, blank=True)
    submitted_at = models.DateTimeField(_('Submitted At'), null=True, blank=True)
    is_completed = models.BooleanField(_('Is Completed'), default=False)
    status = models.CharField(_('Status'), max_length=15, choices=STATUS_CHOICES, default='not_started')
    score = models.DecimalField(_('Score'), max_digits=8, decimal_places=2, default=0)
    percentage = models.DecimalField(_('Percentage'), max_digits=5, decimal_places=2, default=0)
    passed = models.BooleanField(_('Passed'), default=False)
    attempt_number = models.PositiveSmallIntegerField(_('Attempt Number'), default=1)
    questions_answered = models.PositiveIntegerField(_('Questions Answered'), default=0)
    questions_correct = models.PositiveIntegerField(_('Questions Correct'), default=0)
    time_taken_seconds = models.PositiveIntegerField(_('Time Taken (seconds)'), default=0)
    
    # Exam integrity monitoring
    browser_fingerprint = models.CharField(_('Browser Fingerprint'), max_length=255, blank=True)
    ip_address = models.GenericIPAddressField(_('IP Address'), blank=True, null=True)
    tab_switches = models.PositiveSmallIntegerField(_('Tab/Window Switches'), default=0)
    integrity_flags = models.PositiveSmallIntegerField(_('Integrity Flags'), default=0)
    
    # Metadata
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Exam Attempt')
        verbose_name_plural = _('Exam Attempts')
        ordering = ['-submitted_at', '-created_at']
        unique_together = ['exam', 'student', 'attempt_number']
    
    def __str__(self):
        return f"{self.student} - {self.exam.title} (Attempt {self.attempt_number})"
    
    def save(self, *args, **kwargs):
        # Calculate time taken if completed
        if self.is_completed and self.started_at and self.submitted_at:
            time_delta = self.submitted_at - self.started_at
            self.time_taken_seconds = int(time_delta.total_seconds())
            
        # Calculate percentage and check if passed
        if self.is_completed and self.exam.total_marks > 0:
            self.percentage = (self.score / self.exam.total_marks) * 100
            self.passed = self.percentage >= self.exam.passing_percentage
            
        super().save(*args, **kwargs)
    
    @property
    def time_remaining(self):
        if not self.started_at or self.is_completed:
            return 0
        
        duration = self.exam.duration_minutes * 60  # Convert to seconds
        elapsed = (timezone.now() - self.started_at).total_seconds()
        remaining = duration - elapsed
        
        return max(0, remaining)


class StudentAnswer(models.Model):
    """Student's answer to a question"""
    attempt = models.ForeignKey(ExamAttempt, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(ExamQuestion, on_delete=models.CASCADE, related_name='student_answers')
    selected_choices = models.ManyToManyField(QuestionChoice, related_name='selected_by')
    text_answer = models.TextField(_('Text Answer'), blank=True)
    is_correct = models.BooleanField(_('Is Correct'), null=True, blank=True)
    marks_awarded = models.DecimalField(_('Marks Awarded'), max_digits=5, decimal_places=2, default=0)
    answer_time = models.DateTimeField(_('Answer Time'), auto_now_add=True)
    
    # For manual grading
    graded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name='graded_answers', null=True, blank=True)
    feedback = models.TextField(_('Feedback'), blank=True)
    
    class Meta:
        verbose_name = _('Student Answer')
        verbose_name_plural = _('Student Answers')
        unique_together = ['attempt', 'question']
    
    def __str__(self):
        return f"{self.attempt.student} - {self.question}"
    
    def auto_evaluate(self):
        """Automatically evaluate MCQ and True/False answers"""
        if self.question.question_type in ['mcq_single', 'mcq_multiple', 'true_false']:
            # Get correct choices
            correct_choices = set(self.question.choices.filter(is_correct=True).values_list('id', flat=True))
            selected = set(self.selected_choices.values_list('id', flat=True))
            
            if self.question.question_type == 'mcq_single':
                # Single answer MCQ
                self.is_correct = correct_choices == selected
            elif self.question.question_type == 'mcq_multiple':
                # Multiple answers MCQ
                self.is_correct = correct_choices == selected
            elif self.question.question_type == 'true_false':
                # True/False
                self.is_correct = correct_choices == selected
            
            # Award marks if correct
            if self.is_correct:
                self.marks_awarded = self.question.marks
            elif self.question.exam.negative_marking and not self.is_correct:
                # Apply negative marking if wrong
                self.marks_awarded = -self.question.exam.negative_mark_value
            else:
                self.marks_awarded = 0
            
            self.save()
