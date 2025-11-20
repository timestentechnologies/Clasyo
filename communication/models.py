from django.db import models
from django.utils.translation import gettext_lazy as _
from accounts.models import User


class Notice(models.Model):
    """Model for notice board posts"""
    PRIORITY_CHOICES = (
        ('normal', 'Normal'),
        ('medium', 'Medium'),
        ('high', 'High'),
    )
    
    AUDIENCE_CHOICES = (
        ('all', 'All'),
        ('teacher', 'Teachers'),
        ('student', 'Students'),
        ('parent', 'Parents'),
        ('staff', 'Staff'),
    )
    
    title = models.CharField(max_length=200)
    content = models.TextField()
    target_audience = models.CharField(max_length=20, choices=AUDIENCE_CHOICES, default='all')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='normal')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notices_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Notices'
    
    def __str__(self):
        return f"{self.title} ({self.get_priority_display()})"


class Message(models.Model):
    """Model for internal messaging"""
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    subject = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    parent_message = models.ForeignKey('self', on_delete=models.CASCADE, 
                                     null=True, blank=True, 
                                     related_name='replies')
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.subject} - {self.sender} to {self.recipient}"
        
    @property
    def has_replies(self):
        return self.replies.exists()
        return f"{self.subject} - From {self.sender} to {self.receiver}"
