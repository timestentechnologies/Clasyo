from django.db import models
from django.utils.translation import gettext_lazy as _
from academics.models import Class, Subject
from students.models import Student


class Exam(models.Model):
    """Model for examinations"""
    EXAM_TYPES = (
        ('midterm', 'Midterm'),
        ('final', 'Final'),
        ('quiz', 'Quiz'),
        ('assignment', 'Assignment'),
        ('online', 'Online Exam'),
    )
    
    name = models.CharField(max_length=200)
    exam_type = models.CharField(max_length=50, choices=EXAM_TYPES, default='midterm')
    start_date = models.DateField()
    end_date = models.DateField()
    note = models.TextField(blank=True)
    is_published = models.BooleanField(default=False)
    
    # Online exam fields
    is_online = models.BooleanField(default=False)
    duration_minutes = models.IntegerField(null=True, blank=True, help_text="Duration for online exam in minutes")
    passing_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=40.00)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.get_exam_type_display()})"


class ExamQuestion(models.Model):
    """Model for online exam questions"""
    QUESTION_TYPES = (
        ('multiple_choice', 'Multiple Choice'),
        ('true_false', 'True/False'),
        ('short_answer', 'Short Answer'),
        ('essay', 'Essay'),
    )
    
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    question_type = models.CharField(max_length=50, choices=QUESTION_TYPES, default='multiple_choice')
    points = models.DecimalField(max_digits=5, decimal_places=2, default=1.00)
    order = models.IntegerField(default=0)
    
    # For multiple choice and true/false
    option_a = models.CharField(max_length=500, blank=True)
    option_b = models.CharField(max_length=500, blank=True)
    option_c = models.CharField(max_length=500, blank=True)
    option_d = models.CharField(max_length=500, blank=True)
    correct_answer = models.CharField(max_length=500, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['order', 'id']
    
    def __str__(self):
        return f"Q{self.order}: {self.question_text[:50]}"


class ExamFile(models.Model):
    """Model for exam-related files (question papers, answer sheets, etc.)"""
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='files')
    file = models.FileField(upload_to='exam_files/')
    description = models.CharField(max_length=200, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"File for {self.exam.name}"


class Grade(models.Model):
    """Model for grade ranges"""
    name = models.CharField(max_length=10)  # A+, A, B+, etc.
    min_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    max_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    point = models.DecimalField(max_digits=3, decimal_places=2)
    note = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-min_percentage']
    
    def __str__(self):
        return f"{self.name} ({self.min_percentage}% - {self.max_percentage}%)"


class ExamMark(models.Model):
    """Model for student exam marks"""
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='marks')
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='exam_marks')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    marks_obtained = models.DecimalField(max_digits=6, decimal_places=2)
    total_marks = models.DecimalField(max_digits=6, decimal_places=2, default=100)
    grade = models.ForeignKey(Grade, on_delete=models.SET_NULL, null=True, blank=True)
    remarks = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['exam', 'student', 'subject']
        ordering = ['exam', 'student']
    
    def __str__(self):
        return f"{self.student} - {self.exam} - {self.subject}: {self.marks_obtained}/{self.total_marks}"
    
    @property
    def percentage(self):
        if self.total_marks > 0:
            return (self.marks_obtained / self.total_marks) * 100
        return 0


class ExamResult(models.Model):
    """Model for overall exam results"""
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='results')
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='exam_results')
    total_marks = models.DecimalField(max_digits=8, decimal_places=2)
    marks_obtained = models.DecimalField(max_digits=8, decimal_places=2)
    percentage = models.DecimalField(max_digits=5, decimal_places=2)
    grade = models.ForeignKey(Grade, on_delete=models.SET_NULL, null=True, blank=True)
    remarks = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['exam', 'student']
        ordering = ['-percentage']
    
    def __str__(self):
        return f"{self.student} - {self.exam}: {self.percentage}%"
