from django.db import models
from django.utils.translation import gettext_lazy as _


class School(models.Model):
    """School (Tenant) Model"""
    INSTITUTION_TYPE_CHOICES = [
        ('unspecified', 'Unspecified'),
        ('pre_primary_primary', 'Pre-Primary & Primary'),
        ('primary_junior_secondary', 'Primary & Junior Secondary'),
        ('junior_secondary_only', 'Junior Secondary Only'),
        ('senior_secondary', 'Senior Secondary'),
        ('tvet_college', 'TVET / College'),
        ('mixed', 'Mixed School (Multiple Levels)'),
    ]
    name = models.CharField(_("School Name"), max_length=255)
    slug = models.SlugField(_("Slug"), unique=True)
    
    # Contact Information
    email = models.EmailField(_("Email"), unique=True)
    phone = models.CharField(_("Phone Number"), max_length=20)
    address = models.TextField(_("Address"))
    city = models.CharField(_("City"), max_length=100)
    state = models.CharField(_("State"), max_length=100)
    country = models.CharField(_("Country"), max_length=100)
    postal_code = models.CharField(_("Postal Code"), max_length=20)
    
    # School Details
    logo = models.ImageField(_("School Logo"), upload_to='school_logos/', null=True, blank=True)
    website = models.URLField(_("Website"), null=True, blank=True)
    established_date = models.DateField(_("Established Date"), null=True, blank=True)
    registration_number = models.CharField(_("Registration Number"), max_length=100, null=True, blank=True)
    institution_type = models.CharField(_("Institution Type"), max_length=50,
                                       choices=INSTITUTION_TYPE_CHOICES, default='unspecified')
    
    # Subscription Details
    subscription_plan = models.ForeignKey('subscriptions.SubscriptionPlan', 
                                         on_delete=models.SET_NULL, 
                                         null=True, blank=True,
                                         related_name='schools')
    subscription_start_date = models.DateField(_("Subscription Start Date"), null=True, blank=True)
    subscription_end_date = models.DateField(_("Subscription End Date"), null=True, blank=True)
    is_trial = models.BooleanField(_("Is Trial"), default=False)
    trial_end_date = models.DateField(_("Trial End Date"), null=True, blank=True)
    
    # Status
    is_active = models.BooleanField(_("Is Active"), default=True)
    is_verified = models.BooleanField(_("Is Verified"), default=False)
    
    # Metadata
    created_on = models.DateTimeField(_("Created On"), auto_now_add=True)
    updated_on = models.DateTimeField(_("Updated On"), auto_now=True)
    
    # Limits
    max_students = models.IntegerField(_("Maximum Students"), default=100)
    max_teachers = models.IntegerField(_("Maximum Teachers"), default=20)
    max_staff = models.IntegerField(_("Maximum Staff"), default=10)
    
    # Settings
    academic_year_start_month = models.IntegerField(_("Academic Year Start Month"), default=4)  # April
    date_format = models.CharField(_("Date Format"), max_length=20, default='DD-MM-YYYY')
    time_format = models.CharField(_("Time Format"), max_length=20, default='12')  # 12 or 24
    currency = models.CharField(_("Currency"), max_length=10, default='USD')
    currency_symbol = models.CharField(_("Currency Symbol"), max_length=5, default='$')
    timezone = models.CharField(_("Timezone"), max_length=50, default='UTC')
    
    # Features Enabled
    enable_online_exam = models.BooleanField(_("Enable Online Exam"), default=True)
    enable_online_payment = models.BooleanField(_("Enable Online Payment"), default=True)
    enable_chat = models.BooleanField(_("Enable Chat"), default=True)
    enable_sms = models.BooleanField(_("Enable SMS"), default=True)
    enable_library = models.BooleanField(_("Enable Library"), default=True)
    enable_transport = models.BooleanField(_("Enable Transport"), default=True)
    enable_dormitory = models.BooleanField(_("Enable Dormitory"), default=True)
    enable_inventory = models.BooleanField(_("Enable Inventory"), default=True)

    class Meta:
        verbose_name = _("School")
        verbose_name_plural = _("Schools")

    def __str__(self):
        return self.name
    
    @property
    def is_subscription_active(self):
        """Check if subscription is active"""
        from django.utils import timezone
        if self.is_trial and self.trial_end_date:
            return timezone.now().date() <= self.trial_end_date
        if self.subscription_end_date:
            return timezone.now().date() <= self.subscription_end_date
        return False


class Domain(models.Model):
    """Domain Model for School Tenants"""
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='domains')
    domain = models.CharField(_("Domain"), max_length=255, unique=True)
    is_primary = models.BooleanField(_("Is Primary"), default=True)
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)

    class Meta:
        verbose_name = _("Domain")
        verbose_name_plural = _("Domains")
    
    def __str__(self):
        return self.domain
