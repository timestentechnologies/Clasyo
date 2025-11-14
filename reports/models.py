from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from tenants.models import School
from django.utils import timezone
import json


class ReportType(models.Model):
    """Report type model"""
    name = models.CharField(_('Report Name'), max_length=100)
    description = models.TextField(_('Description'), blank=True)
    module = models.CharField(_('Module'), max_length=50, help_text=_('e.g., academics, attendance, finance'))
    icon = models.CharField(_('Icon Class'), max_length=50, default='fa fa-file-alt')
    
    # Configuration for report generation
    data_source = models.CharField(_('Data Source'), max_length=255, help_text=_('Name of Django model or SQL view'))
    query_params = models.JSONField(_('Query Parameters'), default=dict, 
                                 help_text=_('Parameters required for filtering data'))
    date_range_required = models.BooleanField(_('Date Range Required'), default=False)
    
    # Display configuration
    columns = models.JSONField(_('Columns'), default=list, 
                             help_text=_('Columns to display in the report'))
    chart_types = models.JSONField(_('Chart Types'), default=list, 
                                 help_text=_('Available chart types for this report'))
    
    # Permissions
    available_to_roles = models.JSONField(_('Available To Roles'), default=list, 
                                        help_text=_('User roles that can access this report'))
    is_system = models.BooleanField(_('System Report'), default=False, 
                                  help_text=_('Built-in system report that cannot be deleted'))
    
    # School association for multi-tenant support
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='report_types', null=True, blank=True)
    
    # Metadata
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, 
                                 related_name='created_report_types')
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Report Type')
        verbose_name_plural = _('Report Types')
        ordering = ['module', 'name']
    
    def __str__(self):
        return self.name


class SavedReport(models.Model):
    """Saved report model for storing generated reports"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('generating', 'Generating'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    title = models.CharField(_('Report Title'), max_length=200)
    report_type = models.ForeignKey(ReportType, on_delete=models.CASCADE, related_name='saved_reports')
    
    # Parameters used for generation
    parameters = models.JSONField(_('Parameters'), default=dict)
    date_range_start = models.DateField(_('Date Range Start'), null=True, blank=True)
    date_range_end = models.DateField(_('Date Range End'), null=True, blank=True)
    
    # Report content
    data = models.JSONField(_('Report Data'), default=dict)
    summary = models.JSONField(_('Report Summary'), default=dict)
    notes = models.TextField(_('Notes'), blank=True)
    
    # File exports
    pdf_file = models.FileField(_('PDF Export'), upload_to='reports/pdf/', null=True, blank=True)
    excel_file = models.FileField(_('Excel Export'), upload_to='reports/excel/', null=True, blank=True)
    
    # Status and scheduling
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default='pending')
    is_scheduled = models.BooleanField(_('Is Scheduled'), default=False)
    schedule_frequency = models.CharField(_('Schedule Frequency'), max_length=20, 
                                        choices=[('daily', 'Daily'), ('weekly', 'Weekly'), 
                                                ('monthly', 'Monthly'), ('quarterly', 'Quarterly')], 
                                        blank=True, null=True)
    last_generated = models.DateTimeField(_('Last Generated'), null=True, blank=True)
    
    # Sharing and visibility
    is_public = models.BooleanField(_('Is Public'), default=False, 
                                  help_text=_('Visible to all users with appropriate permissions'))
    shared_with = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='shared_reports', blank=True)
    
    # School association for multi-tenant support
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='saved_reports', null=True, blank=True)
    
    # Metadata
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, 
                                 related_name='created_reports')
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Saved Report')
        verbose_name_plural = _('Saved Reports')
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title
    
    def get_data_as_list(self):
        """Convert JSON data to list for template rendering"""
        try:
            if isinstance(self.data, str):
                return json.loads(self.data)
            return self.data
        except (json.JSONDecodeError, AttributeError):
            return []
    
    def get_summary_items(self):
        """Get summary items as list of key-value pairs"""
        try:
            if isinstance(self.summary, str):
                return json.loads(self.summary).items()
            return self.summary.items()
        except (json.JSONDecodeError, AttributeError):
            return []


class ReportDistribution(models.Model):
    """Distribution settings for reports"""
    FREQUENCY_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
    ]
    
    report = models.ForeignKey(SavedReport, on_delete=models.CASCADE, related_name='distributions')
    name = models.CharField(_('Distribution Name'), max_length=100)
    
    # Recipients
    recipients = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='report_distributions')
    email_addresses = models.TextField(_('Additional Email Addresses'), blank=True, 
                                     help_text=_('Comma-separated list of email addresses'))
    
    # Schedule
    frequency = models.CharField(_('Frequency'), max_length=20, choices=FREQUENCY_CHOICES)
    day_of_week = models.PositiveSmallIntegerField(_('Day of Week'), null=True, blank=True, 
                                                 help_text=_('1-7, where 1 is Monday (for weekly)'))
    day_of_month = models.PositiveSmallIntegerField(_('Day of Month'), null=True, blank=True, 
                                                  help_text=_('1-31 (for monthly)'))
    time_of_day = models.TimeField(_('Time of Day'))
    
    # Content format
    include_pdf = models.BooleanField(_('Include PDF'), default=True)
    include_excel = models.BooleanField(_('Include Excel'), default=False)
    
    # Status
    is_active = models.BooleanField(_('Is Active'), default=True)
    last_sent = models.DateTimeField(_('Last Sent'), null=True, blank=True)
    
    # Metadata
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, 
                                 related_name='created_report_distributions')
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Report Distribution')
        verbose_name_plural = _('Report Distributions')
    
    def __str__(self):
        return f"{self.name} ({self.get_frequency_display()})"
