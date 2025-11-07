from django.db import models
from django.utils.translation import gettext_lazy as _


class PricingPlan(models.Model):
    """Pricing plans for the platform"""
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration = models.CharField(max_length=50, default='Monthly', help_text='e.g., Monthly, Yearly')
    max_students = models.IntegerField(null=True, blank=True, help_text='Leave blank for unlimited')
    max_teachers = models.IntegerField(null=True, blank=True, help_text='Leave blank for unlimited')
    max_staff = models.IntegerField(null=True, blank=True, help_text='Leave blank for unlimited')
    features = models.TextField(help_text='Enter features separated by new lines')
    is_active = models.BooleanField(default=True)
    is_popular = models.BooleanField(default=False, help_text='Mark as popular/recommended plan')
    order = models.IntegerField(default=0, help_text='Display order')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'price']
    
    def __str__(self):
        return f"{self.name} - ${self.price}/{self.duration}"
    
    def get_features_list(self):
        """Return features as a list"""
        return [f.strip() for f in self.features.split('\n') if f.strip()]


class FAQ(models.Model):
    """Frequently Asked Questions"""
    question = models.CharField(max_length=255)
    answer = models.TextField()
    category = models.CharField(max_length=100, default='General')
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'category', 'question']
        verbose_name = 'FAQ'
        verbose_name_plural = 'FAQs'
    
    def __str__(self):
        return self.question


class PageContent(models.Model):
    """Manage static page content"""
    PAGE_CHOICES = [
        ('about', 'About Us'),
        ('home_hero', 'Home - Hero Section'),
        ('home_features', 'Home - Features'),
        ('contact', 'Contact Info'),
    ]
    
    page = models.CharField(max_length=50, choices=PAGE_CHOICES, unique=True)
    title = models.CharField(max_length=255)
    subtitle = models.CharField(max_length=255, blank=True)
    content = models.TextField()
    extra_data = models.JSONField(null=True, blank=True, help_text='Additional structured data')
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Page Content'
        verbose_name_plural = 'Page Contents'
    
    def __str__(self):
        return f"{self.get_page_display()} - {self.title}"


class ContactMessage(models.Model):
    """Contact form submissions"""
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    subject = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    replied = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} - {self.subject}"
