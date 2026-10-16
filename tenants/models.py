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
                                         on_delete=models.SET_NULL, db_constraint=False, 
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
    
    CURRENCY_CHOICES = [
        ('KES', 'Kenyan Shilling (KES - KSh)'),
        ('USD', 'US Dollar (USD - $)'),
        ('EUR', 'Euro (EUR - €)'),
        ('GBP', 'British Pound (GBP - £)'),
        ('TZS', 'Tanzanian Shilling (TZS - TSh)'),
        ('UGX', 'Ugandan Shilling (UGX - USh)'),
        ('RWF', 'Rwandan Franc (RWF - FRw)'),
        ('ZAR', 'South African Rand (ZAR - R)'),
        ('NGN', 'Nigerian Naira (NGN - ₦)'),
        ('GHS', 'Ghanaian Cedi (GHS - GH₵)'),
        ('INR', 'Indian Rupee (INR - ₹)'),
        ('CAD', 'Canadian Dollar (CAD - CA$)'),
        ('AUD', 'Australian Dollar (AUD - A$)'),
        ('AED', 'UAE Dirham (AED)'),
        ('SAR', 'Saudi Riyal (SAR)'),
    ]

    LANGUAGE_CHOICES = [
        ('en', 'English'),
        ('sw', 'Swahili (Kiswahili)'),
        ('fr', 'French (Français)'),
        ('ar', 'Arabic (العربية)'),
        ('es', 'Spanish (Español)'),
        ('pt', 'Portuguese (Português)'),
        ('de', 'German (Deutsch)'),
    ]

    DEFAULT_CURRENCY_SYMBOLS = {
        'KES': 'KSh',
        'USD': '$',
        'EUR': '€',
        'GBP': '£',
        'TZS': 'TSh',
        'UGX': 'USh',
        'RWF': 'FRw',
        'ZAR': 'R',
        'NGN': '₦',
        'GHS': 'GH₵',
        'INR': '₹',
        'CAD': 'CA$',
        'AUD': 'A$',
        'AED': 'AED',
        'SAR': 'SAR',
    }

    # Settings
    academic_year_start_month = models.IntegerField(_("Academic Year Start Month"), default=4)  # April
    date_format = models.CharField(_("Date Format"), max_length=20, default='DD-MM-YYYY')
    time_format = models.CharField(_("Time Format"), max_length=20, default='12')  # 12 or 24
    currency = models.CharField(_("Currency"), max_length=10, default='USD')
    currency_symbol = models.CharField(_("Currency Symbol"), max_length=10, default='$')
    language = models.CharField(_("Language"), max_length=10, choices=LANGUAGE_CHOICES, default='en')
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

    # Platform / System Defaults Access (Controlled by Superadmin)
    allow_system_sms = models.BooleanField(
        _("Allow System SMS"), 
        default=False, 
        help_text=_("Allow this school to use the platform's central SMS gateway as default")
    )
    allow_system_email = models.BooleanField(
        _("Allow System Email"), 
        default=False, 
        help_text=_("Allow this school to use the platform's central Email gateway as default")
    )
    allow_system_ai = models.BooleanField(
        _("Allow System AI"), 
        default=False, 
        help_text=_("Allow this school to use the platform's central AI models as default")
    )
    allow_system_whatsapp = models.BooleanField(
        _("Allow System WhatsApp"), 
        default=False, 
        help_text=_("Allow this school to use the platform's central WhatsApp gateway as default")
    )

    # School-Specific Maintenance Mode (Controlled by School Admin)
    maintenance_mode = models.BooleanField(
        _("Maintenance Mode"), 
        default=False,
        help_text=_("When enabled, only administrators of this school can access the portal.")
    )
    maintenance_start = models.DateTimeField(_("Maintenance Start"), null=True, blank=True)
    maintenance_end = models.DateTimeField(_("Maintenance End"), null=True, blank=True)
    maintenance_message = models.TextField(
        _("Maintenance Message"),
        blank=True,
        default="We are currently performing scheduled maintenance on our school portal. Please check back shortly.",
        help_text=_("Custom message shown to students, parents, and teachers during maintenance.")
    )

    objects = models.Manager()

    class Meta:
        verbose_name = _("School")
        verbose_name_plural = _("Schools")

    def __str__(self) -> str:
        return str(self.name)

    @property
    def clean_currency(self):
        return (self.currency or 'USD').strip().upper()

    @property
    def clean_currency_symbol(self):
        sym = (self.currency_symbol or '').strip()
        if not sym:
            return self.DEFAULT_CURRENCY_SYMBOLS.get(self.clean_currency, '$')
        return sym

    @property
    def clean_language(self):
        return (self.language or 'en').strip().lower()

    def save(self, *args, **kwargs):
        if self.currency:
            self.currency = self.currency.strip().upper()
        if self.currency_symbol:
            self.currency_symbol = self.currency_symbol.strip()
        if hasattr(self, 'language') and self.language:
            self.language = self.language.strip().lower()
        super().save(*args, **kwargs)
    
    @property
    def has_valid_logo(self):
        """Check if school has a non-empty, valid logo configured"""
        return bool(self.logo and self.logo.name and self.logo.name.strip())

    @property
    def logo_url(self):
        """Safe logo URL fallback"""
        if self.has_valid_logo:
            try:
                return self.logo.url
            except Exception:
                pass
        return None

    
    @property
    def is_subscription_active(self):
        """Check if subscription is active"""
        from django.utils import timezone
        if self.slug in ('demo-school', 'demo') or 'demo' in str(self.slug).lower():
            if not self.is_active:
                return False
            if self.subscription_end_date:
                return timezone.now().date() <= self.subscription_end_date
            return True
        if self.is_trial and self.trial_end_date:
            return timezone.now().date() <= self.trial_end_date
        if self.subscription_end_date:
            return timezone.now().date() <= self.subscription_end_date
        return False

    @property
    def is_in_maintenance(self):
        """Check if this school is currently in maintenance mode, considering scheduled timeframe if specified."""
        if not self.maintenance_mode:
            return False
        from django.utils import timezone
        now = timezone.now()
        if self.maintenance_start and now < self.maintenance_start:
            return False
        if self.maintenance_end and now > self.maintenance_end:
            return False
        return True



class Domain(models.Model):
    """Domain Model for School Tenants"""
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='domains')
    domain = models.CharField(_("Domain"), max_length=255, unique=True)
    is_primary = models.BooleanField(_("Is Primary"), default=True)
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)

    objects = models.Manager()

    class Meta:
        verbose_name = _("Domain")
        verbose_name_plural = _("Domains")
    
    def __str__(self) -> str:
        return str(self.domain)
