from django.db import models
from django.utils.translation import gettext_lazy as _
from accounts.models import User
from students.models import Student
from tenants.models import School


class LeaveType(models.Model):
    """Leave Type Model"""
    school = models.ForeignKey(School, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(_("Leave Type"), max_length=100)
    description = models.TextField(_("Description"), blank=True)
    max_days = models.IntegerField(_("Maximum Days"), default=10)
    is_active = models.BooleanField(_("Is Active"), default=True)
    
    class Meta:
        verbose_name = _("Leave Type")
        verbose_name_plural = _("Leave Types")
    
    def __str__(self):
        return self.name


class Leave(models.Model):
    """Leave Application Model"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ]
    
    APPLICANT_TYPE_CHOICES = [
        ('teacher', 'Teacher'),
        ('student', 'Student'),
        ('staff', 'Staff'),
    ]
    
    school = models.ForeignKey(School, on_delete=models.CASCADE, null=True, blank=True)
    
    # Applicant (can be teacher, student, or staff)
    applicant_type = models.CharField(_("Applicant Type"), max_length=20, choices=APPLICANT_TYPE_CHOICES)
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, 
                               related_name='leave_applications_teacher', limit_choices_to={'role': 'teacher'})
    student = models.ForeignKey(Student, on_delete=models.CASCADE, null=True, blank=True,
                               related_name='leave_applications')
    staff = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True,
                             related_name='leave_applications_staff', limit_choices_to={'role': 'staff'})
    
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE, related_name='leaves')
    from_date = models.DateField(_("From Date"))
    to_date = models.DateField(_("To Date"))
    total_days = models.IntegerField(_("Total Days"))
    reason = models.TextField(_("Reason"))
    
    status = models.CharField(_("Status"), max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Approval details
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='approved_leaves')
    approval_date = models.DateTimeField(_("Approval Date"), null=True, blank=True)
    admin_note = models.TextField(_("Admin Note"), blank=True)
    
    # Attachments
    attachment = models.FileField(_("Attachment"), upload_to='leave_attachments/', null=True, blank=True)
    
    created_at = models.DateTimeField(_("Applied On"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)
    
    class Meta:
        verbose_name = _("Leave Application")
        verbose_name_plural = _("Leave Applications")
        ordering = ['-created_at']
    
    def __str__(self):
        if self.applicant_type == 'teacher' and self.teacher:
            return f"{self.teacher.get_full_name()} - {self.leave_type.name}"
        elif self.applicant_type == 'student' and self.student:
            return f"{self.student.get_full_name()} - {self.leave_type.name}"
        elif self.applicant_type == 'staff' and self.staff:
            return f"{self.staff.get_full_name()} - {self.leave_type.name}"
        return f"Leave - {self.leave_type.name}"
    
    def save(self, *args, **kwargs):
        # Calculate total days
        if self.from_date and self.to_date:
            delta = self.to_date - self.from_date
            self.total_days = delta.days + 1
        super().save(*args, **kwargs)
