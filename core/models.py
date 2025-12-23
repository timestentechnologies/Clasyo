from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator


class AcademicYear(models.Model):
    """Academic Year Model"""
    name = models.CharField(_("Academic Year"), max_length=100)
    start_date = models.DateField(_("Start Date"))
    end_date = models.DateField(_("End Date"))
    is_active = models.BooleanField(_("Is Active"), default=False)
    
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)
    
    class Meta:
        verbose_name = _("Academic Year")
        verbose_name_plural = _("Academic Years")
        ordering = ['-start_date']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if self.is_active:
            # Deactivate all other academic years
            AcademicYear.objects.filter(is_active=True).update(is_active=False)
        super().save(*args, **kwargs)


class Session(models.Model):
    """Session/Semester Model"""
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, related_name='sessions')
    name = models.CharField(_("Session Name"), max_length=100)
    start_date = models.DateField(_("Start Date"))
    end_date = models.DateField(_("End Date"))
    is_active = models.BooleanField(_("Is Active"), default=False)
    
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    
    class Meta:
        verbose_name = _("Session")
        verbose_name_plural = _("Sessions")
        ordering = ['start_date']
    
    def __str__(self):
        return f"{self.academic_year.name} - {self.name}"


class Holiday(models.Model):
    """Holiday Model"""
    HOLIDAY_TYPE_CHOICES = [
        ('public', 'Public Holiday'),
        ('festival', 'Festival'),
        ('school', 'School Holiday'),
        ('optional', 'Optional Holiday'),
    ]
    
    title = models.CharField(_("Holiday Title"), max_length=200)
    description = models.TextField(_("Description"), blank=True)
    holiday_type = models.CharField(_("Holiday Type"), max_length=20, choices=HOLIDAY_TYPE_CHOICES)
    
    from_date = models.DateField(_("From Date"))
    to_date = models.DateField(_("To Date"))
    
    is_active = models.BooleanField(_("Is Active"), default=True)
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    
    class Meta:
        verbose_name = _("Holiday")
        verbose_name_plural = _("Holidays")
        ordering = ['from_date']
    
    def __str__(self):
        return self.title


class Weekend(models.Model):
    """Weekend Configuration"""
    WEEKDAY_CHOICES = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]
    
    day = models.IntegerField(_("Day"), choices=WEEKDAY_CHOICES, unique=True)
    is_weekend = models.BooleanField(_("Is Weekend"), default=True)
    
    class Meta:
        verbose_name = _("Weekend")
        verbose_name_plural = _("Weekends")
        ordering = ['day']
    
    def __str__(self):
        return self.get_day_display()


class SystemSetting(models.Model):
    """System Settings Model"""
    # School Information
    school_name = models.CharField(_("School Name"), max_length=255, blank=True)
    school_code = models.CharField(_("School Code"), max_length=50, blank=True)
    school_email = models.EmailField(_("School Email"), blank=True)
    school_phone = models.CharField(_("School Phone"), max_length=20, blank=True)
    school_address = models.TextField(_("School Address"), blank=True)
    
    # Logos and Images
    school_logo = models.ImageField(_("School Logo"), upload_to='settings/', blank=True, null=True)
    school_favicon = models.ImageField(_("School Favicon"), upload_to='settings/', blank=True, null=True)
    
    # Academic Settings
    promote_without_exam = models.BooleanField(_("Promote Students Without Exam"), default=False)
    
    # Date and Time Settings
    date_format = models.CharField(_("Date Format"), max_length=20, default='DD-MM-YYYY')
    time_format = models.CharField(_("Time Format"), max_length=10, default='12', choices=[('12', '12 Hour'), ('24', '24 Hour')])
    timezone = models.CharField(_("Timezone"), max_length=50, default='UTC')
    
    # Currency Settings
    currency_code = models.CharField(_("Currency Code"), max_length=10, default='USD')
    currency_symbol = models.CharField(_("Currency Symbol"), max_length=5, default='$')
    
    # Features Enable/Disable
    enable_online_admission = models.BooleanField(_("Enable Online Admission"), default=True)
    enable_email_notification = models.BooleanField(_("Enable Email Notifications"), default=True)
    enable_sms_notification = models.BooleanField(_("Enable SMS Notifications"), default=False)
    
    # Social Media Links
    facebook_url = models.URLField(_("Facebook URL"), blank=True)
    twitter_url = models.URLField(_("Twitter URL"), blank=True)
    instagram_url = models.URLField(_("Instagram URL"), blank=True)
    linkedin_url = models.URLField(_("LinkedIn URL"), blank=True)
    youtube_url = models.URLField(_("YouTube URL"), blank=True)
    
    # Session Settings
    session_timeout = models.IntegerField(_("Session Timeout (minutes)"), default=30)
    
    # Language Settings
    default_language = models.CharField(_("Default Language"), max_length=10, default='en')
    
    # Backup Settings
    auto_backup = models.BooleanField(_("Auto Backup"), default=True)
    backup_time = models.TimeField(_("Backup Time"), null=True, blank=True)
    
    # Maintenance Mode
    maintenance_mode = models.BooleanField(_("Maintenance Mode"), default=False,
                                           help_text="When enabled, only administrators can access the system.")
    
    # Student Settings
    admission_number_prefix = models.CharField(_("Admission Number Prefix"), max_length=10, default='STU',
                                               help_text="Prefix for auto-generated admission numbers (e.g., STU, AD, etc.)")
    
    # Notification Settings
    email_notifications = models.BooleanField(_("Email Notifications"), default=True)
    sms_notifications = models.BooleanField(_("SMS Notifications"), default=True)
    parent_notifications = models.BooleanField(_("Parent Notifications"), default=True)
    teacher_notifications = models.BooleanField(_("Teacher Notifications"), default=True)
    
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)
    
    class Meta:
        verbose_name = _("System Setting")
        verbose_name_plural = _("System Settings")
    
    def __str__(self):
        return "System Settings"
    
    def save(self, *args, **kwargs):
        # Ensure only one instance exists
        self.pk = 1
        super().save(*args, **kwargs)
    
    @classmethod
    def get_settings(cls):
        """Get or create system settings"""
        obj, created = cls.objects.get_or_create(pk=1)
        return obj


class Notification(models.Model):
    """Notification Model"""
    NOTIFICATION_TYPE_CHOICES = [
        ('info', 'Information'),
        ('success', 'Success'),
        ('warning', 'Warning'),
        ('error', 'Error'),
    ]
    
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(_("Title"), max_length=200)
    message = models.TextField(_("Message"))
    notification_type = models.CharField(_("Type"), max_length=20, choices=NOTIFICATION_TYPE_CHOICES, default='info')
    link = models.CharField(_("Link"), max_length=500, blank=True)
    
    is_read = models.BooleanField(_("Is Read"), default=False)
    read_at = models.DateTimeField(_("Read At"), null=True, blank=True)
    
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    
    class Meta:
        verbose_name = _("Notification")
        verbose_name_plural = _("Notifications")
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title
    
    def mark_as_read(self):
        from django.utils import timezone
        self.is_read = True
        self.read_at = timezone.now()
        self.save()


class ToDoList(models.Model):
    """To-Do List Model"""
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='todos')
    title = models.CharField(_("Title"), max_length=200)
    description = models.TextField(_("Description"), blank=True)
    priority = models.CharField(_("Priority"), max_length=20, choices=PRIORITY_CHOICES, default='medium')
    due_date = models.DateField(_("Due Date"), null=True, blank=True)
    
    is_completed = models.BooleanField(_("Is Completed"), default=False)
    completed_at = models.DateTimeField(_("Completed At"), null=True, blank=True)
    
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)
    
    class Meta:
        verbose_name = _("To-Do Item")
        verbose_name_plural = _("To-Do List")
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title


class CalendarEvent(models.Model):
    """Calendar Event Model"""
    EVENT_TYPE_CHOICES = [
        ('meeting', 'Meeting'),
        ('exam', 'Examination'),
        ('holiday', 'Holiday'),
        ('event', 'Event'),
        ('reminder', 'Reminder'),
        ('other', 'Other'),
    ]
    
    title = models.CharField(_("Title"), max_length=200)
    description = models.TextField(_("Description"), blank=True)
    event_type = models.CharField(_("Event Type"), max_length=20, choices=EVENT_TYPE_CHOICES)
    
    start_date = models.DateTimeField(_("Start Date"))
    end_date = models.DateTimeField(_("End Date"))
    all_day = models.BooleanField(_("All Day Event"), default=False)
    
    location = models.CharField(_("Location"), max_length=255, blank=True)
    
    # Participants
    created_by = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='created_events')
    participants = models.ManyToManyField('accounts.User', related_name='calendar_events', blank=True)
    
    # Visibility
    is_public = models.BooleanField(_("Is Public"), default=True)
    
    # Reminders
    reminder_enabled = models.BooleanField(_("Reminder Enabled"), default=False)
    reminder_time = models.DurationField(_("Reminder Time"), null=True, blank=True)
    
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)
    
    class Meta:
        verbose_name = _("Calendar Event")
        verbose_name_plural = _("Calendar Events")
        ordering = ['start_date']
    
    def __str__(self):
        return self.title
