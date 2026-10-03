from django.db import models
from django.utils.translation import gettext_lazy as _
from tenants.models import School
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator


SMS_PROVIDER_CHOICES = [
    ('mobilesasa', _('MobileSasa')),
    ('twilio', _('Twilio')),
    ('africastalking', _('Africa\'s Talking')),
    ('infobip', _('Infobip')),
    ('clickatell', _('Clickatell')),
    ('nexmo', _('Nexmo (Vonage)')),
]

EMAIL_PROVIDER_CHOICES = [
    ('smtp', _('SMTP')),
    ('sendgrid', _('SendGrid')),
    ('mailgun', _('Mailgun')),
    ('ses', _('Amazon SES')),
    ('postmark', _('Postmark')),
]

WHATSAPP_PROVIDER_CHOICES = [
    ('mobilesasa', _('MobileSasa WhatsApp')),
    ('meta', _('Meta WhatsApp Cloud API')),
    ('twilio', _('Twilio WhatsApp')),
    ('africastalking', _('Africa\'s Talking WhatsApp')),
    ('infobip', _('Infobip WhatsApp')),
]

GATEWAY_CHOICES = [
    ('mpesa_stk', _('M-Pesa STK Push')),
    ('mpesa_paybill', _('M-Pesa Manual Paybill')),
    ('mpesa_buygoods', _('Lipa na M-Pesa (Buy Goods & Services)')),
    ('mpesa_send_money', _('M-Pesa Send Money')),
    ('mpesa_pochi', _('M-Pesa Pochi la Biashara')),
    ('paypal', _('PayPal')),
    ('stripe', _('Stripe')),
    ('bank', _('Bank Transfer')),
    ('cash', _('Cash')),
    ('cheque', _('Cheque')),
]


class GlobalSMSConfiguration(models.Model):
    """Global SMS configuration for all schools"""
    
    provider = models.CharField(
        max_length=20, 
        choices=SMS_PROVIDER_CHOICES, 
        unique=True,
        verbose_name=_('SMS Provider')
    )
    
    is_active = models.BooleanField(default=False, verbose_name=_('Is Active'))
    
    # Twilio fields
    twilio_account_sid = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('Twilio Account SID')
    )
    twilio_auth_token = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('Twilio Auth Token')
    )
    twilio_phone_number = models.CharField(
        max_length=20, 
        blank=True, 
        null=True,
        verbose_name=_('Twilio Phone Number')
    )
    
    # Africa's Talking fields
    africastalking_username = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('Africa\'s Talking Username')
    )
    africastalking_api_key = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('Africa\'s Talking API Key')
    )
    africastalking_sender_id = models.CharField(
        max_length=20, 
        blank=True, 
        null=True,
        verbose_name=_('Africa\'s Talking Sender ID')
    )
    
    # Infobip fields
    infobip_api_key = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('Infobip API Key')
    )
    infobip_base_url = models.URLField(
        blank=True, 
        null=True,
        verbose_name=_('Infobip Base URL'),
        default='https://api.infobip.com'
    )
    infobip_sender = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        verbose_name=_('Infobip Sender ID')
    )
    
    # Clickatell fields
    clickatell_api_key = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('Clickatell API Key')
    )
    
    # Nexmo fields
    nexmo_api_key = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('Nexmo API Key')
    )
    nexmo_api_secret = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('Nexmo API Secret')
    )
    nexmo_from_number = models.CharField(
        max_length=20, 
        blank=True, 
        null=True,
        verbose_name=_('Nexmo From Number')
    )
    
    # MobileSasa fields
    mobilesasa_api_token = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name=_('MobileSasa API Token'),
        help_text=_('Bearer token from MobileSasa dashboard (e.g. mbs_...)')
    )
    mobilesasa_sender_id = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name=_('MobileSasa Sender ID'),
        help_text=_('Approved Sender ID from MobileSasa')
    )
    
    # Common settings
    default_sender_id = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        verbose_name=_('Default Sender ID'),
        help_text=_('Default sender ID for SMS messages')
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated At'))
    
    class Meta:
        verbose_name = _('Global SMS Configuration')
        verbose_name_plural = _('Global SMS Configurations')
    
    def __str__(self):
        return f"{self.get_provider_display()} ({'Active' if self.is_active else 'Inactive'})"
    
    def get_config_data(self):
        """Return configuration data as dictionary"""
        config = {
            'provider': self.provider,
            'is_active': self.is_active,
            'default_sender_id': self.default_sender_id,
        }
        
        if self.provider == 'mobilesasa':
            config.update({
                'api_token': self.mobilesasa_api_token,
                'sender_id': self.mobilesasa_sender_id or self.default_sender_id,
            })
        elif self.provider == 'twilio':
            config.update({
                'account_sid': self.twilio_account_sid,
                'auth_token': self.twilio_auth_token,
                'phone_number': self.twilio_phone_number,
            })
        elif self.provider == 'africastalking':
            config.update({
                'username': self.africastalking_username,
                'api_key': self.africastalking_api_key,
                'sender_id': self.africastalking_sender_id,
            })
        elif self.provider == 'infobip':
            config.update({
                'api_key': self.infobip_api_key,
                'base_url': self.infobip_base_url,
                'sender': self.infobip_sender,
            })
        elif self.provider == 'clickatell':
            config.update({
                'api_key': self.clickatell_api_key,
            })
        elif self.provider == 'nexmo':
            config.update({
                'api_key': self.nexmo_api_key,
                'api_secret': self.nexmo_api_secret,
                'from_number': self.nexmo_from_number,
            })
        
        return config


class GlobalEmailConfiguration(models.Model):
    """Global email configuration for all schools"""
    
    provider = models.CharField(
        max_length=20, 
        choices=EMAIL_PROVIDER_CHOICES, 
        unique=True,
        verbose_name=_('Email Provider')
    )
    
    is_active = models.BooleanField(default=False, verbose_name=_('Is Active'))
    
    # SMTP fields
    smtp_host = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('SMTP Host')
    )
    smtp_port = models.PositiveIntegerField(
        blank=True, 
        null=True,
        verbose_name=_('SMTP Port')
    )
    smtp_username = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('SMTP Username')
    )
    smtp_password = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('SMTP Password')
    )
    smtp_use_tls = models.BooleanField(
        default=True, 
        verbose_name=_('Use TLS')
    )
    smtp_use_ssl = models.BooleanField(
        default=False, 
        verbose_name=_('Use SSL')
    )
    
    # SendGrid fields
    sendgrid_api_key = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('SendGrid API Key')
    )
    sendgrid_sender_email = models.EmailField(
        blank=True, 
        null=True,
        verbose_name=_('SendGrid Sender Email')
    )
    sendgrid_sender_name = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('SendGrid Sender Name')
    )
    
    # Mailgun fields
    mailgun_api_key = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('Mailgun API Key')
    )
    mailgun_domain = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('Mailgun Domain')
    )
    mailgun_sender_email = models.EmailField(
        blank=True, 
        null=True,
        verbose_name=_('Mailgun Sender Email')
    )
    
    # Amazon SES fields
    ses_access_key = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('AWS Access Key')
    )
    ses_secret_key = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('AWS Secret Key')
    )
    ses_region = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        default='us-east-1',
        verbose_name=_('AWS Region')
    )
    ses_sender_email = models.EmailField(
        blank=True, 
        null=True,
        verbose_name=_('SES Sender Email')
    )
    
    # Postmark fields
    postmark_api_key = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('Postmark API Key')
    )
    postmark_sender_email = models.EmailField(
        blank=True, 
        null=True,
        verbose_name=_('Postmark Sender Email')
    )
    postmark_sender_name = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('Postmark Sender Name')
    )
    
    # Common settings
    default_from_email = models.EmailField(
        blank=True, 
        null=True,
        verbose_name=_('Default From Email'),
        help_text=_('Default from email address for all emails')
    )
    default_from_name = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('Default From Name'),
        help_text=_('Default from name for all emails')
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated At'))
    
    class Meta:
        verbose_name = _('Global Email Configuration')
        verbose_name_plural = _('Global Email Configurations')
    
    def __str__(self):
        return f"{self.get_provider_display()} ({'Active' if self.is_active else 'Inactive'})"
    
    def get_config_data(self):
        """Return configuration data as dictionary"""
        config = {
            'provider': self.provider,
            'is_active': self.is_active,
            'default_from_email': self.default_from_email,
            'default_from_name': self.default_from_name,
        }
        
        if self.provider == 'smtp':
            config.update({
                'host': self.smtp_host,
                'port': self.smtp_port,
                'username': self.smtp_username,
                'password': self.smtp_password,
                'use_tls': self.smtp_use_tls,
                'use_ssl': self.smtp_use_ssl,
            })
        elif self.provider == 'sendgrid':
            config.update({
                'api_key': self.sendgrid_api_key,
                'sender_email': self.sendgrid_sender_email,
                'sender_name': self.sendgrid_sender_name,
            })
        elif self.provider == 'mailgun':
            config.update({
                'api_key': self.mailgun_api_key,
                'domain': self.mailgun_domain,
                'sender_email': self.mailgun_sender_email,
            })
        elif self.provider == 'ses':
            config.update({
                'access_key': self.ses_access_key,
                'secret_key': self.ses_secret_key,
                'region': self.ses_region,
                'sender_email': self.ses_sender_email,
            })
        elif self.provider == 'postmark':
            config.update({
                'api_key': self.postmark_api_key,
                'sender_email': self.postmark_sender_email,
                'sender_name': self.postmark_sender_name,
            })
        
        return config


class GlobalGoogleAuthConfiguration(models.Model):
    """Global Google OAuth 2.0 configuration for Sign-in and Register with Google"""
    
    client_id = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('Google Client ID'),
        help_text=_('OAuth 2.0 Client ID from Google Cloud Console (e.g. xxxxxxxx.apps.googleusercontent.com)')
    )
    client_secret = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('Google Client Secret'),
        help_text=_('OAuth 2.0 Client Secret from Google Cloud Console (e.g. GOCSPX-xxxxxxxx)')
    )
    is_active = models.BooleanField(
        default=True, 
        verbose_name=_('Enable Google Sign-In'),
        help_text=_('Enable or disable Google Sign-In on login and register modals')
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated At'))

    class Meta:
        verbose_name = _('Global Google Auth Configuration')
        verbose_name_plural = _('Global Google Auth Configurations')

    def __str__(self):
        status = 'Active' if self.is_active else 'Inactive'
        return f"Google Auth ({status})"

    def sync_to_social_app(self):
        """Synchronize settings with Django Allauth SocialApp and Sites"""
        try:
            from allauth.socialaccount.models import SocialApp
            from django.contrib.sites.models import Site

            apps = list(SocialApp.objects.using('default').filter(provider='google').order_by('id'))
            if apps:
                app = apps[0]
                # Clean up any duplicates
                for extra_app in apps[1:]:
                    extra_app.delete()
            else:
                app = SocialApp(provider='google')

            app.name = 'Google Web Client'
            app.client_id = (self.client_id or '').strip()
            app.secret = (self.client_secret or '').strip()
            app.save(using='default')

            current_site = Site.objects.using('default').first()
            if current_site and not app.sites.filter(id=current_site.id).exists():
                app.sites.add(current_site)
            return app
        except Exception:
            return None


class GlobalDatabaseConfiguration(models.Model):
    """Global database configuration settings"""
    
    name = models.CharField(
        max_length=100, 
        unique=True,
        verbose_name=_('Configuration Name')
    )
    
    is_active = models.BooleanField(default=False, verbose_name=_('Is Active'))
    
    # Database connection settings
    db_host = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('Database Host')
    )
    db_port = models.PositiveIntegerField(
        blank=True, 
        null=True,
        verbose_name=_('Database Port')
    )
    db_name = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('Database Name')
    )
    db_user = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('Database User')
    )
    db_password = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('Database Password')
    )
    
    # Backup settings
    backup_enabled = models.BooleanField(
        default=True,
        verbose_name=_('Enable Backups')
    )
    backup_frequency = models.CharField(
        max_length=20,
        choices=[
            ('daily', _('Daily')),
            ('weekly', _('Weekly')),
            ('monthly', _('Monthly')),
        ],
        default='daily',
        verbose_name=_('Backup Frequency')
    )
    backup_retention_days = models.PositiveIntegerField(
        default=30,
        verbose_name=_('Backup Retention Days')
    )
    backup_storage_path = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name=_('Backup Storage Path')
    )
    
    # Performance settings
    max_connections = models.PositiveIntegerField(
        default=100,
        verbose_name=_('Max Connections')
    )
    connection_timeout = models.PositiveIntegerField(
        default=30,
        verbose_name=_('Connection Timeout (seconds)')
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated At'))
    
    class Meta:
        verbose_name = _('Global Database Configuration')
        verbose_name_plural = _('Global Database Configurations')
    
    def __str__(self):
        return f"{self.name} ({'Active' if self.is_active else 'Inactive'})"
    
    def get_config_data(self):
        """Return configuration data as dictionary"""
        return {
            'name': self.name,
            'is_active': self.is_active,
            'db_host': self.db_host,
            'db_port': self.db_port,
            'db_name': self.db_name,
            'db_user': self.db_user,
            'db_password': self.db_password,
            'backup_enabled': self.backup_enabled,
            'backup_frequency': self.backup_frequency,
            'backup_retention_days': self.backup_retention_days,
            'backup_storage_path': self.backup_storage_path,
            'max_connections': self.max_connections,
            'connection_timeout': self.connection_timeout,
        }


class GlobalWhatsAppConfiguration(models.Model):
    """Global WhatsApp configuration for all schools"""
    
    provider = models.CharField(
        max_length=20, 
        choices=WHATSAPP_PROVIDER_CHOICES, 
        unique=True,
        verbose_name=_('WhatsApp Provider')
    )
    
    is_active = models.BooleanField(default=False, verbose_name=_('Is Active'))
    
    # Meta WhatsApp Cloud API fields
    meta_phone_number_id = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        verbose_name=_('Meta Phone Number ID')
    )
    meta_waba_id = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        verbose_name=_('WhatsApp Business Account ID (WABA)')
    )
    meta_access_token = models.CharField(
        max_length=500, 
        blank=True, 
        null=True,
        verbose_name=_('Meta Access Token')
    )
    meta_app_id = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        verbose_name=_('Meta App ID')
    )
    meta_app_secret = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        verbose_name=_('Meta App Secret')
    )
    meta_webhook_verify_token = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        verbose_name=_('Webhook Verify Token')
    )
    
    # Twilio WhatsApp fields
    twilio_account_sid = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('Twilio Account SID')
    )
    twilio_auth_token = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('Twilio Auth Token')
    )
    twilio_from_number = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        verbose_name=_('Twilio From WhatsApp Number'),
        help_text=_('Format: whatsapp:+14155238886')
    )
    
    # Africa's Talking WhatsApp fields
    africastalking_username = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('Africa\'s Talking Username')
    )
    africastalking_api_key = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('Africa\'s Talking API Key')
    )
    africastalking_sender_phone = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        verbose_name=_('Africa\'s Talking Sender Phone')
    )
    
    # Infobip WhatsApp fields
    infobip_api_key = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('Infobip API Key')
    )
    infobip_base_url = models.URLField(
        blank=True, 
        null=True,
        verbose_name=_('Infobip Base URL'),
        default='https://api.infobip.com'
    )
    infobip_sender_phone = models.CharField(
        max_length=50, 
        blank=True, 
        null=True, 
        verbose_name=_('Infobip Sender Phone Number')
    )
    
    # MobileSasa WhatsApp fields
    mobilesasa_api_token = models.CharField(
        max_length=255, 
        blank=True, 
        null=True, 
        verbose_name=_('MobileSasa API Token'),
        help_text=_('Bearer token from MobileSasa dashboard (e.g. mbs_...)')
    )
    mobilesasa_account_uuid = models.CharField(
        max_length=100, 
        blank=True, 
        null=True, 
        verbose_name=_('MobileSasa WhatsApp Account UUID'),
        help_text=_('UUID of the connected WhatsApp account in MobileSasa')
    )
    mobilesasa_sender_phone = models.CharField(
        max_length=50, 
        blank=True, 
        null=True, 
        verbose_name=_('MobileSasa Sender Phone Number'),
        help_text=_('Phone number registered on WhatsApp account')
    )
    
    # Common settings
    default_sender_phone = models.CharField(
        max_length=50, 
        blank=True, 
        null=True, 
        verbose_name=_('Default Sender Phone Number'),
        help_text=_('Default outgoing phone number for WhatsApp notifications')
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated At'))
    
    class Meta:
        verbose_name = _('Global WhatsApp Configuration')
        verbose_name_plural = _('Global WhatsApp Configurations')
        
    def __str__(self):
        return f"{self.get_provider_display()} ({'Active' if self.is_active else 'Inactive'})"
        
    def get_config_data(self):
        """Return configuration data as dictionary"""
        config = {
            'provider': self.provider,
            'is_active': self.is_active,
            'default_sender_phone': self.default_sender_phone,
        }
        if self.provider == 'mobilesasa':
            config.update({
                'api_token': self.mobilesasa_api_token,
                'account_uuid': self.mobilesasa_account_uuid,
                'sender_phone': self.mobilesasa_sender_phone or self.default_sender_phone,
            })
        elif self.provider == 'meta':
            config.update({
                'phone_number_id': self.meta_phone_number_id,
                'waba_id': self.meta_waba_id,
                'access_token': self.meta_access_token,
                'app_id': self.meta_app_id,
                'app_secret': self.meta_app_secret,
                'webhook_verify_token': self.meta_webhook_verify_token,
            })
        elif self.provider == 'twilio':
            config.update({
                'account_sid': self.twilio_account_sid,
                'auth_token': self.twilio_auth_token,
                'from_number': self.twilio_from_number,
            })
        elif self.provider == 'africastalking':
            config.update({
                'username': self.africastalking_username,
                'api_key': self.africastalking_api_key,
                'sender_phone': self.africastalking_sender_phone,
            })
        elif self.provider == 'infobip':
            config.update({
                'api_key': self.infobip_api_key,
                'base_url': self.infobip_base_url,
                'sender_phone': self.infobip_sender_phone,
            })
        return config


class PaymentConfiguration(models.Model):
    """Global payment gateway configurations"""
    
    ENVIRONMENT_CHOICES = [
        ('sandbox', _('Sandbox')),
        ('live', _('Live')),
    ]
    
    gateway = models.CharField(
        max_length=50,
        choices=GATEWAY_CHOICES,
        unique=True,
        verbose_name=_('Payment Gateway')
    )
    
    environment = models.CharField(
        max_length=10, 
        choices=ENVIRONMENT_CHOICES, 
        default='sandbox',
        verbose_name=_('Environment')
    )
    
    is_active = models.BooleanField(default=True, verbose_name=_('Is Active'))
    
    # M-Pesa fields
    mpesa_consumer_key = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('M-Pesa Consumer Key')
    )
    mpesa_consumer_secret = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('M-Pesa Consumer Secret')
    )
    mpesa_passkey = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('M-Pesa Passkey')
    )
    mpesa_shortcode = models.CharField(
        max_length=10, 
        blank=True, 
        null=True,
        verbose_name=_('M-Pesa Shortcode')
    )
    mpesa_paybill_number = models.CharField(
        max_length=10, 
        blank=True, 
        null=True,
        verbose_name=_('M-Pesa Paybill Number')
    )
    # Additional M-Pesa manual variants (global)
    mpesa_paybill_account_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name=_('M-Pesa Paybill Account Name')
    )
    mpesa_paybill_instructions = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('M-Pesa Paybill Instructions')
    )
    mpesa_till_number = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        verbose_name=_('M-Pesa Till Number')
    )
    mpesa_buygoods_instructions = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('M-Pesa Buy Goods Instructions')
    )
    mpesa_send_money_recipient = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name=_('M-Pesa Send Money Recipient')
    )
    mpesa_send_money_instructions = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('M-Pesa Send Money Instructions')
    )
    mpesa_pochi_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name=_('Pochi la Biashara Number')
    )
    mpesa_pochi_instructions = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('M-Pesa Pochi Instructions')
    )
    
    # PayPal fields
    paypal_client_id = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('PayPal Client ID')
    )
    paypal_client_secret = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('PayPal Client Secret')
    )
    paypal_webhook_id = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('PayPal Webhook ID')
    )
    
    # Stripe fields
    stripe_publishable_key = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('Stripe Publishable Key')
    )
    stripe_secret_key = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('Stripe Secret Key')
    )
    stripe_webhook_secret = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('Stripe Webhook Secret')
    )
    
    # Bank fields
    bank_name = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('Bank Name')
    )
    bank_account_name = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('Bank Account Name')
    )
    bank_account_number = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        verbose_name=_('Bank Account Number')
    )
    bank_branch = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('Bank Branch')
    )
    bank_swift_code = models.CharField(
        max_length=20, 
        blank=True, 
        null=True,
        verbose_name=_('Bank SWIFT Code')
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated At'))
    
    class Meta:
        verbose_name = _('Payment Configuration')
        verbose_name_plural = _('Payment Configurations')
    
    def __str__(self):
        return f"{self.get_gateway_display()} ({self.get_environment_display()})"
    
    def get_config_data(self):
        """Return configuration data as dictionary"""
        config = {
            'gateway': self.gateway,
            'environment': self.environment,
            'is_active': self.is_active,
        }
        
        if self.gateway == 'mpesa_stk':
            config.update({
                'consumer_key': self.mpesa_consumer_key,
                'consumer_secret': self.mpesa_consumer_secret,
                'passkey': self.mpesa_passkey,
                'shortcode': self.mpesa_shortcode,
            })
        elif self.gateway == 'mpesa_paybill':
            config.update({
                'paybill_number': self.mpesa_paybill_number,
                'account_name': self.mpesa_paybill_account_name,
                'instructions': self.mpesa_paybill_instructions,
            })
        elif self.gateway == 'mpesa_buygoods':
            config.update({
                'till_number': self.mpesa_till_number,
                'instructions': self.mpesa_buygoods_instructions,
            })
        elif self.gateway == 'mpesa_send_money':
            config.update({
                'recipient': self.mpesa_send_money_recipient,
                'instructions': self.mpesa_send_money_instructions,
            })
        elif self.gateway == 'mpesa_pochi':
            config.update({
                'pochi_number': self.mpesa_pochi_number,
                'instructions': self.mpesa_pochi_instructions,
            })
        elif self.gateway == 'paypal':
            config.update({
                'client_id': self.paypal_client_id,
                'client_secret': self.paypal_client_secret,
                'webhook_id': self.paypal_webhook_id,
            })
        elif self.gateway == 'stripe':
            config.update({
                'publishable_key': self.stripe_publishable_key,
                'secret_key': self.stripe_secret_key,
                'webhook_secret': self.stripe_webhook_secret,
            })
        elif self.gateway == 'bank':
            config.update({
                'bank_name': self.bank_name,
                'account_name': self.bank_account_name,
                'account_number': self.bank_account_number,
                'branch': self.bank_branch,
                'swift_code': self.bank_swift_code,
            })
        
        return config

    @property
    def is_configured(self):
        """Return True if gateway has required credentials configured"""
        if self.gateway == 'mpesa_stk':
            return bool(self.mpesa_consumer_key and self.mpesa_consumer_secret and self.mpesa_passkey and self.mpesa_shortcode)
        elif self.gateway == 'mpesa_paybill':
            return bool(self.mpesa_paybill_number)
        elif self.gateway == 'mpesa_buygoods':
            return bool(self.mpesa_till_number)
        elif self.gateway == 'mpesa_send_money':
            return bool(self.mpesa_send_money_recipient)
        elif self.gateway == 'mpesa_pochi':
            return bool(self.mpesa_pochi_number)
        elif self.gateway == 'paypal':
            return bool(self.paypal_client_id and self.paypal_client_secret)
        elif self.gateway == 'stripe':
            return bool(self.stripe_publishable_key and self.stripe_secret_key)
        elif self.gateway == 'bank':
            return bool(self.bank_name and self.bank_account_name and self.bank_account_number)
        elif self.gateway in ['cash', 'cheque']:
            return True
        return False

    @property
    def account_identifier(self):
        """Return the primary account number, till, business number, or shortcode"""
        if self.gateway == 'mpesa_stk':
            return f"Shortcode: {self.mpesa_shortcode}" if self.mpesa_shortcode else "No Shortcode"
        elif self.gateway == 'mpesa_paybill':
            paybill = f"Paybill: {self.mpesa_paybill_number}" if self.mpesa_paybill_number else "No Paybill"
            acc = self.mpesa_paybill_account_name
            return f"{paybill} (A/C: {acc})" if acc else paybill
        elif self.gateway == 'mpesa_buygoods':
            return f"Till: {self.mpesa_till_number}" if self.mpesa_till_number else "No Till"
        elif self.gateway == 'mpesa_send_money':
            return f"Phone: {self.mpesa_send_money_recipient}" if self.mpesa_send_money_recipient else "No Phone"
        elif self.gateway == 'mpesa_pochi':
            return f"Pochi: {self.mpesa_pochi_number}" if self.mpesa_pochi_number else "No Pochi"
        elif self.gateway == 'bank':
            parts = []
            if self.bank_name:
                parts.append(self.bank_name)
            if self.bank_account_number:
                parts.append(f"A/C: {self.bank_account_number}")
            return " - ".join(parts) if parts else "No Account"
        elif self.gateway == 'paypal':
            if self.paypal_client_id:
                return f"Client ID: {self.paypal_client_id[:12]}..."
            return "PayPal"
        elif self.gateway == 'stripe':
            if self.stripe_publishable_key:
                return f"Key: {self.stripe_publishable_key[:14]}..."
            return "Stripe"
        return self.get_gateway_display()


class SchoolPaymentConfiguration(models.Model):
    """School-specific payment gateway configurations"""
    
    ENVIRONMENT_CHOICES = [
        ('sandbox', _('Sandbox')),
        ('live', _('Live')),
    ]
    
    school = models.ForeignKey(
        School, 
        on_delete=models.CASCADE, 
        verbose_name=_('School'),
        related_name='payment_configurations'
    )
    
    gateway = models.CharField(max_length=50, choices=GATEWAY_CHOICES, verbose_name=_('Payment Gateway'))
    
    environment = models.CharField(
        max_length=10, 
        choices=ENVIRONMENT_CHOICES, 
        default='sandbox',
        verbose_name=_('Environment')
    )
    
    is_active = models.BooleanField(default=True, verbose_name=_('Is Active'))
    
    # M-Pesa STK Push fields
    mpesa_consumer_key = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('M-Pesa Consumer Key'),
        help_text=_('Your M-Pesa API consumer key for STK Push')
    )
    mpesa_consumer_secret = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('M-Pesa Consumer Secret'),
        help_text=_('Your M-Pesa API consumer secret for STK Push')
    )
    mpesa_passkey = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('M-Pesa Passkey'),
        help_text=_('Your M-Pesa API passkey for STK Push')
    )
    mpesa_shortcode = models.CharField(
        max_length=10, 
        blank=True, 
        null=True,
        verbose_name=_('M-Pesa Shortcode'),
        help_text=_('Your M-Pesa business shortcode for STK Push')
    )
    
    # M-Pesa Manual Paybill fields
    mpesa_paybill_number = models.CharField(
        max_length=10, 
        blank=True, 
        null=True,
        verbose_name=_('M-Pesa Paybill Number'),
        help_text=_('Your M-Pesa paybill number for manual payments')
    )
    mpesa_paybill_account_number = models.CharField(
        max_length=20, 
        blank=True, 
        null=True,
        verbose_name=_('M-Pesa Paybill Account Number'),
        help_text=_('Account number for M-Pesa paybill payments (visible to parents)')
    )
    mpesa_paybill_bank_name = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('M-Pesa Paybill Bank Name'),
        help_text=_('Bank name associated with M-Pesa paybill (visible to parents)')
    )
    mpesa_paybill_account_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name=_('M-Pesa Paybill Account Name')
    )
    mpesa_paybill_instructions = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('M-Pesa Paybill Instructions')
    )

    # M-Pesa Buy Goods & Services (Till)
    mpesa_till_number = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        verbose_name=_('M-Pesa Till Number'),
        help_text=_('Your M-Pesa till number for Buy Goods & Services payments')
    )
    mpesa_buygoods_instructions = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('M-Pesa Buy Goods Instructions')
    )

    # M-Pesa Send Money recipient phone
    mpesa_send_money_recipient = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name=_('M-Pesa Send Money Recipient'),
        help_text=_('Phone number to receive M-Pesa Send Money payments')
    )
    mpesa_send_money_instructions = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('M-Pesa Send Money Instructions')
    )

    # M-Pesa Pochi la Biashara number
    mpesa_pochi_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name=_('Pochi la Biashara Number'),
        help_text=_('Pochi account phone number for receiving payments')
    )
    mpesa_pochi_instructions = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('M-Pesa Pochi Instructions')
    )
    
    # PayPal fields
    paypal_email = models.EmailField(
        blank=True, 
        null=True,
        verbose_name=_('PayPal Email'),
        help_text=_('Your PayPal business email')
    )
    
    # Bank fields
    bank_name = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('Bank Name')
    )
    bank_account_name = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('Account Name')
    )
    bank_account_number = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        verbose_name=_('Account Number')
    )
    bank_branch = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('Bank Branch')
    )
    
    # Instructions for manual payments
    payment_instructions = models.TextField(
        blank=True, 
        null=True,
        verbose_name=_('Payment Instructions'),
        help_text=_('Instructions for parents on how to make payments')
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated At'))
    
    class Meta:
        verbose_name = _('School Payment Configuration')
        verbose_name_plural = _('School Payment Configurations')
        unique_together = ['school', 'gateway']
    
    def __str__(self):
        return f"{self.school.name} - {self.get_gateway_display()}"
    
    def get_config_data(self):
        """Return configuration data as dictionary"""
        config = {
            'gateway': self.gateway,
            'environment': self.environment,
            'is_active': self.is_active,
        }
        
        if self.gateway == 'mpesa':
            config.update({
                'shortcode': self.mpesa_shortcode,
                'paybill_number': self.mpesa_paybill_number,
            })
        elif self.gateway == 'paypal':
            config.update({
                'email': self.paypal_email,
            })
        elif self.gateway == 'bank':
            config.update({
                'bank_name': self.bank_name,
                'account_name': self.bank_account_name,
                'account_number': self.bank_account_number,
                'branch': self.bank_branch,
            })
        elif self.gateway in ['cash', 'cheque']:
            config.update({
                'instructions': self.payment_instructions,
            })
        elif self.gateway == 'mpesa_buygoods':
            config.update({
                'till_number': self.mpesa_till_number,
                'instructions': self.mpesa_buygoods_instructions,
            })
        elif self.gateway == 'mpesa_send_money':
            config.update({
                'recipient': self.mpesa_send_money_recipient,
                'instructions': self.mpesa_send_money_instructions,
            })
        elif self.gateway == 'mpesa_pochi':
            config.update({
                'pochi_number': self.mpesa_pochi_number,
                'instructions': self.mpesa_pochi_instructions,
            })
        elif self.gateway == 'mpesa_paybill':
            config.update({
                'paybill_number': self.mpesa_paybill_number,
                'account_number': self.mpesa_paybill_account_number,
                'account_name': self.mpesa_paybill_account_name,
                'instructions': self.mpesa_paybill_instructions,
            })
        
        return config

    @property
    def is_configured(self):
        """Return True if school gateway has required credentials configured"""
        if self.gateway == 'mpesa_stk':
            return bool(self.mpesa_consumer_key and self.mpesa_consumer_secret and self.mpesa_passkey and self.mpesa_shortcode)
        elif self.gateway == 'mpesa_paybill':
            return bool(self.mpesa_paybill_number)
        elif self.gateway == 'mpesa_buygoods':
            return bool(self.mpesa_till_number)
        elif self.gateway == 'mpesa_send_money':
            return bool(self.mpesa_send_money_recipient)
        elif self.gateway == 'mpesa_pochi':
            return bool(self.mpesa_pochi_number)
        elif self.gateway == 'paypal':
            return bool(self.paypal_email)
        elif self.gateway == 'bank':
            return bool(self.bank_name and self.bank_account_name and self.bank_account_number)
        elif self.gateway in ['cash', 'cheque']:
            return True
        return False

    @property
    def account_identifier(self):
        """Return the primary account number, till, business number, or shortcode"""
        if self.gateway == 'mpesa_stk':
            return f"Shortcode: {self.mpesa_shortcode}" if self.mpesa_shortcode else "No Shortcode"
        elif self.gateway == 'mpesa_paybill':
            paybill = f"Paybill: {self.mpesa_paybill_number}" if self.mpesa_paybill_number else "No Paybill"
            acc = self.mpesa_paybill_account_number or self.mpesa_paybill_account_name
            return f"{paybill} (A/C: {acc})" if acc else paybill
        elif self.gateway == 'mpesa_buygoods':
            return f"Till: {self.mpesa_till_number}" if self.mpesa_till_number else "No Till"
        elif self.gateway == 'mpesa_send_money':
            return f"Phone: {self.mpesa_send_money_recipient}" if self.mpesa_send_money_recipient else "No Phone"
        elif self.gateway == 'mpesa_pochi':
            return f"Pochi: {self.mpesa_pochi_number}" if self.mpesa_pochi_number else "No Pochi"
        elif self.gateway == 'bank':
            parts = []
            if self.bank_name:
                parts.append(self.bank_name)
            if self.bank_account_number:
                parts.append(f"A/C: {self.bank_account_number}")
            return " - ".join(parts) if parts else "No Account"
        elif self.gateway == 'paypal':
            if self.paypal_email:
                return f"Email: {self.paypal_email}"
            return "PayPal"
        return self.get_gateway_display()


class GlobalAIConfiguration(models.Model):
    """Global AI configuration for all schools"""
    
    provider = models.CharField(
        max_length=50,
        default='openai',
        choices=[
            ('openai', 'OpenAI'),
            ('azure', 'Azure OpenAI'),
            ('anthropic', 'Anthropic'),
            ('google', 'Google Gemini'),
            ('local', 'Local Model'),
        ],
        verbose_name=_('AI Provider')
    )
    
    is_active = models.BooleanField(
        default=False, 
        verbose_name=_('Is Active'),
        help_text=_('Enable AI features across all schools')
    )
    
    # OpenAI settings
    openai_api_key = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('OpenAI API Key'),
        help_text=_('Your OpenAI API key')
    )
    
    openai_model = models.CharField(
        max_length=100,
        default='gpt-4',
        blank=True,
        null=True,
        verbose_name=_('OpenAI Model'),
        help_text=_('Default model to use for OpenAI (e.g., gpt-4, gpt-3.5-turbo)')
    )
    
    # Azure OpenAI settings
    azure_openai_api_key = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('Azure OpenAI API Key')
    )
    
    azure_openai_endpoint = models.URLField(
        blank=True, 
        null=True,
        verbose_name=_('Azure OpenAI Endpoint')
    )
    
    azure_openai_deployment = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name=_('Azure OpenAI Deployment')
    )
    
    # Anthropic settings
    anthropic_api_key = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('Anthropic API Key')
    )
    
    anthropic_model = models.CharField(
        max_length=100,
        default='claude-2',
        blank=True,
        null=True,
        verbose_name=_('Anthropic Model')
    )
    
    # Google Gemini settings
    google_api_key = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('Google API Key'),
        help_text=_('Your Google AI Studio API key')
    )
    
    google_model = models.CharField(
        max_length=100,
        default='gemini-1.5-flash',
        blank=True,
        null=True,
        verbose_name=_('Google Model'),
        help_text=_('Default model to use for Google Gemini (e.g., gemini-1.5-flash, gemini-1.5-pro)')
    )
    
    # Local model settings
    local_model_path = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name=_('Local Model Path'),
        help_text=_('Path to the local model files')
    )
    
    # General settings
    temperature = models.FloatField(
        default=0.7,
        validators=[MinValueValidator(0.0), MaxValueValidator(2.0)],
        verbose_name=_('Temperature'),
        help_text=_('Controls randomness in the AI responses (0.0 to 2.0)')
    )
    
    max_tokens = models.PositiveIntegerField(
        default=1000,
        verbose_name=_('Max Tokens'),
        help_text=_('Maximum number of tokens to generate in the response')
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated At'))
    
    class Meta:
        verbose_name = _('Global AI Configuration')
        verbose_name_plural = _('Global AI Configurations')
    
    def __str__(self):
        return f"Global AI Configuration ({self.get_provider_display()})"
    
    def get_config_data(self):
        """Return configuration data as dictionary"""
        return {
            'provider': self.provider,
            'is_active': self.is_active,
            'openai_api_key': self.openai_api_key,
            'openai_model': self.openai_model,
            'azure_openai_api_key': self.azure_openai_api_key,
            'azure_openai_endpoint': self.azure_openai_endpoint,
            'azure_openai_deployment': self.azure_openai_deployment,
            'anthropic_api_key': self.anthropic_api_key,
            'anthropic_model': self.anthropic_model,
            'google_api_key': self.google_api_key,
            'google_model': self.google_model,
            'local_model_path': self.local_model_path,
            'temperature': self.temperature,
            'max_tokens': self.max_tokens,
        }


class SchoolAIConfiguration(models.Model):
    """School-specific AI configuration"""
    
    school = models.ForeignKey(
        School, 
        on_delete=models.CASCADE, 
        verbose_name=_('School'),
        related_name='ai_configurations'
    )
    
    is_active = models.BooleanField(
        default=False, 
        verbose_name=_('Is Active'),
        help_text=_('Enable AI features for this school')
    )
    
    use_global_settings = models.BooleanField(
        default=True,
        verbose_name=_('Use Global Settings'),
        help_text=_('Use global AI configuration settings')
    )
    
    # Provider override
    provider = models.CharField(
        max_length=50,
        default='openai',
        choices=[
            ('openai', 'OpenAI'),
            ('azure', 'Azure OpenAI'),
            ('anthropic', 'Anthropic'),
            ('google', 'Google Gemini'),
            ('local', 'Local Model'),
        ],
        blank=True,
        null=True,
        verbose_name=_('AI Provider Override'),
        help_text=_('Override global AI provider settings')
    )
    
    # OpenAI overrides
    openai_api_key = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('OpenAI API Key (Override)'),
        help_text=_('Override global OpenAI API key')
    )
    
    openai_model = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name=_('OpenAI Model (Override)'),
        help_text=_('Override global OpenAI model')
    )
    
    # Azure OpenAI overrides
    azure_openai_api_key = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('Azure OpenAI API Key (Override)')
    )
    
    azure_openai_endpoint = models.URLField(
        blank=True, 
        null=True,
        verbose_name=_('Azure OpenAI Endpoint (Override)')
    )
    
    azure_openai_deployment = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name=_('Azure OpenAI Deployment (Override)')
    )
    
    # Anthropic overrides
    anthropic_api_key = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('Anthropic API Key (Override)')
    )
    
    anthropic_model = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name=_('Anthropic Model (Override)')
    )
    
    # Google Gemini overrides
    google_api_key = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('Google API Key (Override)'),
        help_text=_('Override global Google API key')
    )
    
    google_model = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name=_('Google Model (Override)'),
        help_text=_('Override global Google model')
    )
    
    # Local model overrides
    local_model_path = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name=_('Local Model Path (Override)')
    )
    
    # General settings overrides
    temperature = models.FloatField(
        blank=True,
        null=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(2.0)],
        verbose_name=_('Temperature (Override)'),
        help_text=_('Override global temperature setting')
    )
    
    max_tokens = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name=_('Max Tokens (Override)'),
        help_text=_('Override global max tokens setting')
    )
    
    # Context settings
    include_student_data = models.BooleanField(
        default=True,
        verbose_name=_('Include Student Data'),
        help_text=_('Allow AI to access student data for context')
    )
    
    include_academic_data = models.BooleanField(
        default=True,
        verbose_name=_('Include Academic Data'),
        help_text=_('Allow AI to access academic records for context')
    )
    
    include_financial_data = models.BooleanField(
        default=False,
        verbose_name=_('Include Financial Data'),
        help_text=_('Allow AI to access financial data for context')
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated At'))
    
    class Meta:
        verbose_name = _('School AI Configuration')
        verbose_name_plural = _('School AI Configurations')
        unique_together = ('school',)
    
    def __str__(self):
        return f"AI Configuration - {self.school.name}"
    
    def get_effective_config(self):
        """Get the effective configuration, merging global and school-specific settings"""
        global_config = GlobalAIConfiguration.objects.first()
        
        # If no global config, build from school config only
        if not global_config:
            config = {
                'provider': self.provider or 'openai',
                'is_active': self.is_active,
                'openai_api_key': self.openai_api_key,
                'openai_model': self.openai_model or 'gpt-3.5-turbo',
                'azure_openai_api_key': self.azure_openai_api_key,
                'azure_openai_endpoint': self.azure_openai_endpoint,
                'azure_openai_deployment': self.azure_openai_deployment,
                'anthropic_api_key': self.anthropic_api_key,
                'anthropic_model': self.anthropic_model,
                'google_api_key': self.google_api_key,
                'google_model': self.google_model,
                'local_model_path': self.local_model_path,
                'temperature': self.temperature if self.temperature is not None else 0.7,
                'max_tokens': self.max_tokens if self.max_tokens is not None else 1000,
            }
            return config
            
        if self.use_global_settings:
            return global_config.get_config_data()
            
        config = global_config.get_config_data()
        
        # Override with school-specific settings if they exist
        if self.provider:
            config['provider'] = self.provider
            
        if self.openai_api_key:
            config['openai_api_key'] = self.openai_api_key
        if self.openai_model:
            config['openai_model'] = self.openai_model
            
        if self.azure_openai_api_key:
            config['azure_openai_api_key'] = self.azure_openai_api_key
        if self.azure_openai_endpoint:
            config['azure_openai_endpoint'] = self.azure_openai_endpoint
        if self.azure_openai_deployment:
            config['azure_openai_deployment'] = self.azure_openai_deployment
            
        if self.anthropic_api_key:
            config['anthropic_api_key'] = self.anthropic_api_key
        if self.anthropic_model:
            config['anthropic_model'] = self.anthropic_model
            
        if self.google_api_key:
            config['google_api_key'] = self.google_api_key
        if self.google_model:
            config['google_model'] = self.google_model
            
        if self.local_model_path:
            config['local_model_path'] = self.local_model_path
            
        if self.temperature is not None:
            config['temperature'] = self.temperature
        if self.max_tokens is not None:
            config['max_tokens'] = self.max_tokens
            
        return config


class SchoolSMSConfiguration(models.Model):
    """School-specific SMS configuration"""
    
    school = models.ForeignKey(
        School, 
        on_delete=models.CASCADE, 
        verbose_name=_('School'),
        related_name='sms_configurations'
    )
    
    provider = models.CharField(
        max_length=20, 
        choices=SMS_PROVIDER_CHOICES, 
        verbose_name=_('SMS Provider')
    )
    
    is_active = models.BooleanField(default=False, verbose_name=_('Is Active'))
    
    # Override global settings
    use_global_settings = models.BooleanField(
        default=True,
        verbose_name=_('Use Global Settings'),
        help_text=_('Use global SMS configuration settings')
    )
    
    # Twilio fields
    twilio_account_sid = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('Twilio Account SID'),
        help_text=_('Override global Twilio Account SID')
    )
    twilio_auth_token = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('Twilio Auth Token'),
        help_text=_('Override global Twilio Auth Token')
    )
    twilio_phone_number = models.CharField(
        max_length=20, 
        blank=True, 
        null=True,
        verbose_name=_('Twilio Phone Number'),
        help_text=_('Override global Twilio Phone Number')
    )
    
    # Africa's Talking fields
    africastalking_username = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('Africa\'s Talking Username'),
        help_text=_('Override global Africa\'s Talking Username')
    )
    africastalking_api_key = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('Africa\'s Talking API Key'),
        help_text=_('Override global Africa\'s Talking API Key')
    )
    africastalking_sender_id = models.CharField(
        max_length=20, 
        blank=True, 
        null=True,
        verbose_name=_('Africa\'s Talking Sender ID'),
        help_text=_('Override global Africa\'s Talking Sender ID')
    )
    
    # Infobip fields
    infobip_api_key = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('Infobip API Key'),
        help_text=_('Override global Infobip API Key')
    )
    infobip_base_url = models.URLField(
        blank=True, 
        null=True,
        verbose_name=_('Infobip Base URL'),
        help_text=_('Override global Infobip Base URL')
    )
    infobip_sender = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        verbose_name=_('Infobip Sender ID'),
        help_text=_('Override global Infobip Sender ID')
    )
    
    # Clickatell fields
    clickatell_api_key = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('Clickatell API Key'),
        help_text=_('Override global Clickatell API Key')
    )
    
    # Nexmo fields
    nexmo_api_key = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('Nexmo API Key'),
        help_text=_('Override global Nexmo API Key')
    )
    nexmo_api_secret = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('Nexmo API Secret'),
        help_text=_('Override global Nexmo API Secret')
    )
    nexmo_from_number = models.CharField(
        max_length=20, 
        blank=True, 
        null=True, 
        verbose_name=_('Nexmo From Number'),
        help_text=_('Override global Nexmo From Number')
    )
    
    # MobileSasa fields
    mobilesasa_api_token = models.CharField(
        max_length=255, 
        blank=True, 
        null=True, 
        verbose_name=_('MobileSasa API Token'),
        help_text=_('Override global MobileSasa API Token')
    )
    mobilesasa_sender_id = models.CharField(
        max_length=50, 
        blank=True, 
        null=True, 
        verbose_name=_('MobileSasa Sender ID'),
        help_text=_('Override global MobileSasa Sender ID')
    )
    
    # School-specific settings
    custom_sender_id = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        verbose_name=_('Custom Sender ID'),
        help_text=_('School-specific sender ID for SMS messages')
    )
    
    # Usage limits
    daily_sms_limit = models.PositiveIntegerField(
        blank=True, 
        null=True,
        verbose_name=_('Daily SMS Limit'),
        help_text=_('Maximum number of SMS messages per day')
    )
    monthly_sms_limit = models.PositiveIntegerField(
        blank=True, 
        null=True,
        verbose_name=_('Monthly SMS Limit'),
        help_text=_('Maximum number of SMS messages per month')
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated At'))
    
    class Meta:
        verbose_name = _('School SMS Configuration')
        verbose_name_plural = _('School SMS Configurations')
        unique_together = ['school', 'provider']
    
    def __str__(self):
        return f"{self.school.name} - {self.get_provider_display()}"
    
    def get_config_data(self):
        """Return configuration data as dictionary"""
        config = {
            'provider': self.provider,
            'is_active': self.is_active,
            'use_global_settings': self.use_global_settings,
            'custom_sender_id': self.custom_sender_id,
            'daily_sms_limit': self.daily_sms_limit,
            'monthly_sms_limit': self.monthly_sms_limit,
        }
        
        if not self.use_global_settings:
            if self.provider == 'mobilesasa':
                config.update({
                    'api_token': self.mobilesasa_api_token,
                    'sender_id': self.mobilesasa_sender_id or self.custom_sender_id,
                })
            elif self.provider == 'twilio':
                config.update({
                    'account_sid': self.twilio_account_sid,
                    'auth_token': self.twilio_auth_token,
                    'phone_number': self.twilio_phone_number,
                })
            elif self.provider == 'africastalking':
                config.update({
                    'username': self.africastalking_username,
                    'api_key': self.africastalking_api_key,
                    'sender_id': self.africastalking_sender_id,
                })
            elif self.provider == 'infobip':
                config.update({
                    'api_key': self.infobip_api_key,
                    'base_url': self.infobip_base_url,
                    'sender': self.infobip_sender,
                })
            elif self.provider == 'clickatell':
                config.update({
                    'api_key': self.clickatell_api_key,
                })
            elif self.provider == 'nexmo':
                config.update({
                    'api_key': self.nexmo_api_key,
                    'api_secret': self.nexmo_api_secret,
                    'from_number': self.nexmo_from_number,
                })
        
        return config


class SchoolEmailConfiguration(models.Model):
    """School-specific email configuration"""
    
    school = models.ForeignKey(
        School, 
        on_delete=models.CASCADE, 
        verbose_name=_('School'),
        related_name='email_configurations'
    )
    
    provider = models.CharField(
        max_length=20, 
        choices=EMAIL_PROVIDER_CHOICES, 
        verbose_name=_('Email Provider')
    )
    
    is_active = models.BooleanField(default=False, verbose_name=_('Is Active'))
    
    # Override global settings
    use_global_settings = models.BooleanField(
        default=True,
        verbose_name=_('Use Global Settings'),
        help_text=_('Use global email configuration settings')
    )
    
    # SMTP fields
    smtp_host = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('SMTP Host'),
        help_text=_('Override global SMTP Host')
    )
    smtp_port = models.PositiveIntegerField(
        blank=True, 
        null=True,
        verbose_name=_('SMTP Port'),
        help_text=_('Override global SMTP Port')
    )
    smtp_username = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('SMTP Username'),
        help_text=_('Override global SMTP Username')
    )
    smtp_password = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('SMTP Password'),
        help_text=_('Override global SMTP Password')
    )
    smtp_use_tls = models.BooleanField(
        default=True, 
        verbose_name=_('Use TLS'),
        help_text=_('Override global TLS setting')
    )
    smtp_use_ssl = models.BooleanField(
        default=False, 
        verbose_name=_('Use SSL'),
        help_text=_('Override global SSL setting')
    )
    
    # SendGrid fields
    sendgrid_api_key = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('SendGrid API Key'),
        help_text=_('Override global SendGrid API Key')
    )
    sendgrid_sender_email = models.EmailField(
        blank=True, 
        null=True,
        verbose_name=_('SendGrid Sender Email'),
        help_text=_('Override global SendGrid Sender Email')
    )
    sendgrid_sender_name = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('SendGrid Sender Name'),
        help_text=_('Override global SendGrid Sender Name')
    )
    
    # Mailgun fields
    mailgun_api_key = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('Mailgun API Key'),
        help_text=_('Override global Mailgun API Key')
    )
    mailgun_domain = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('Mailgun Domain'),
        help_text=_('Override global Mailgun Domain')
    )
    mailgun_sender_email = models.EmailField(
        blank=True, 
        null=True,
        verbose_name=_('Mailgun Sender Email'),
        help_text=_('Override global Mailgun Sender Email')
    )
    
    # Amazon SES fields
    ses_access_key = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('AWS Access Key'),
        help_text=_('Override global AWS Access Key')
    )
    ses_secret_key = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('AWS Secret Key'),
        help_text=_('Override global AWS Secret Key')
    )
    ses_region = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        default='us-east-1',
        verbose_name=_('AWS Region'),
        help_text=_('Override global AWS Region')
    )
    ses_sender_email = models.EmailField(
        blank=True, 
        null=True,
        verbose_name=_('SES Sender Email'),
        help_text=_('Override global SES Sender Email')
    )
    
    # Postmark fields
    postmark_api_key = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('Postmark API Key'),
        help_text=_('Override global Postmark API Key')
    )
    postmark_sender_email = models.EmailField(
        blank=True, 
        null=True,
        verbose_name=_('Postmark Sender Email'),
        help_text=_('Override global Postmark Sender Email')
    )
    postmark_sender_name = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('Postmark Sender Name'),
        help_text=_('Override global Postmark Sender Name')
    )
    
    # School-specific settings
    custom_from_email = models.EmailField(
        blank=True, 
        null=True,
        verbose_name=_('Custom From Email'),
        help_text=_('School-specific from email address')
    )
    custom_from_name = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('Custom From Name'),
        help_text=_('School-specific from name')
    )
    
    # Usage limits
    daily_email_limit = models.PositiveIntegerField(
        blank=True, 
        null=True,
        verbose_name=_('Daily Email Limit'),
        help_text=_('Maximum number of emails per day')
    )
    monthly_email_limit = models.PositiveIntegerField(
        blank=True, 
        null=True,
        verbose_name=_('Monthly Email Limit'),
        help_text=_('Maximum number of emails per month')
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated At'))
    
    class Meta:
        verbose_name = _('School Email Configuration')
        verbose_name_plural = _('School Email Configurations')
        unique_together = ['school', 'provider']
    
    def __str__(self):
        return f"{self.school.name} - {self.get_provider_display()}"
    
    def get_config_data(self):
        """Return configuration data as dictionary"""
        config = {
            'provider': self.provider,
            'is_active': self.is_active,
            'use_global_settings': self.use_global_settings,
            'custom_from_email': self.custom_from_email,
            'custom_from_name': self.custom_from_name,
            'daily_email_limit': self.daily_email_limit,
            'monthly_email_limit': self.monthly_email_limit,
        }
        
        if not self.use_global_settings:
            if self.provider == 'smtp':
                config.update({
                    'host': self.smtp_host,
                    'port': self.smtp_port,
                    'username': self.smtp_username,
                    'password': self.smtp_password,
                    'use_tls': self.smtp_use_tls,
                    'use_ssl': self.smtp_use_ssl,
                })
            elif self.provider == 'sendgrid':
                config.update({
                    'api_key': self.sendgrid_api_key,
                    'sender_email': self.sendgrid_sender_email,
                    'sender_name': self.sendgrid_sender_name,
                })
            elif self.provider == 'mailgun':
                config.update({
                    'api_key': self.mailgun_api_key,
                    'domain': self.mailgun_domain,
                    'sender_email': self.mailgun_sender_email,
                })
            elif self.provider == 'ses':
                config.update({
                    'access_key': self.ses_access_key,
                    'secret_key': self.ses_secret_key,
                    'region': self.ses_region,
                    'sender_email': self.ses_sender_email,
                })
            elif self.provider == 'postmark':
                config.update({
                    'api_key': self.postmark_api_key,
                    'sender_email': self.postmark_sender_email,
                    'sender_name': self.postmark_sender_name,
                })
        
        return config


class SchoolWhatsAppConfiguration(models.Model):
    """School-specific WhatsApp configuration"""
    
    school = models.ForeignKey(
        School, 
        on_delete=models.CASCADE, 
        verbose_name=_('School'),
        related_name='whatsapp_configurations'
    )
    
    provider = models.CharField(
        max_length=20, 
        choices=WHATSAPP_PROVIDER_CHOICES, 
        verbose_name=_('WhatsApp Provider')
    )
    
    is_active = models.BooleanField(default=False, verbose_name=_('Is Active'))
    
    # Override global settings
    use_global_settings = models.BooleanField(
        default=True,
        verbose_name=_('Use Global Settings'),
        help_text=_('Use global WhatsApp configuration settings')
    )
    
    # Meta WhatsApp Cloud API fields
    meta_phone_number_id = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        verbose_name=_('Meta Phone Number ID'),
        help_text=_('Override global Meta Phone Number ID')
    )
    meta_waba_id = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        verbose_name=_('WhatsApp Business Account ID (WABA)'),
        help_text=_('Override global WABA ID')
    )
    meta_access_token = models.CharField(
        max_length=500, 
        blank=True, 
        null=True,
        verbose_name=_('Meta Access Token'),
        help_text=_('Override global Meta Access Token')
    )
    meta_app_id = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        verbose_name=_('Meta App ID'),
        help_text=_('Override global Meta App ID')
    )
    meta_app_secret = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        verbose_name=_('Meta App Secret'),
        help_text=_('Override global Meta App Secret')
    )
    meta_webhook_verify_token = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        verbose_name=_('Webhook Verify Token'),
        help_text=_('Override global Webhook Verify Token')
    )
    
    # Twilio WhatsApp fields
    twilio_account_sid = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('Twilio Account SID'),
        help_text=_('Override global Twilio Account SID')
    )
    twilio_auth_token = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('Twilio Auth Token'),
        help_text=_('Override global Twilio Auth Token')
    )
    twilio_from_number = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        verbose_name=_('Twilio From WhatsApp Number'),
        help_text=_('Format: whatsapp:+14155238886')
    )
    
    # Africa's Talking WhatsApp fields
    africastalking_username = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('Africa\'s Talking Username'),
        help_text=_('Override global Africa\'s Talking Username')
    )
    africastalking_api_key = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('Africa\'s Talking API Key'),
        help_text=_('Override global Africa\'s Talking API Key')
    )
    africastalking_sender_phone = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        verbose_name=_('Africa\'s Talking Sender Phone'),
        help_text=_('Override global Africa\'s Talking Sender Phone')
    )
    
    # Infobip WhatsApp fields
    infobip_api_key = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_('Infobip API Key'),
        help_text=_('Override global Infobip API Key')
    )
    infobip_base_url = models.URLField(
        blank=True, 
        null=True,
        verbose_name=_('Infobip Base URL'),
        default='https://api.infobip.com'
    )
    infobip_sender_phone = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        verbose_name=_('Infobip Sender Phone Number'),
        help_text=_('Override global Infobip Sender Phone Number')
    )
    
    # MobileSasa WhatsApp fields
    mobilesasa_api_token = models.CharField(
        max_length=255, 
        blank=True, 
        null=True, 
        verbose_name=_('MobileSasa API Token'),
        help_text=_('Override global MobileSasa API Token')
    )
    mobilesasa_account_uuid = models.CharField(
        max_length=100, 
        blank=True, 
        null=True, 
        verbose_name=_('MobileSasa WhatsApp Account UUID'),
        help_text=_('Override global MobileSasa WhatsApp Account UUID')
    )
    mobilesasa_sender_phone = models.CharField(
        max_length=50, 
        blank=True, 
        null=True, 
        verbose_name=_('MobileSasa Sender Phone Number'),
        help_text=_('Override global MobileSasa Sender Phone Number')
    )
    
    # School-specific settings
    custom_sender_phone = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        verbose_name=_('Custom Sender Phone'),
        help_text=_('School-specific sender phone for WhatsApp messages')
    )
    
    # Usage limits
    daily_whatsapp_limit = models.PositiveIntegerField(
        blank=True, 
        null=True,
        verbose_name=_('Daily WhatsApp Limit'),
        help_text=_('Maximum number of WhatsApp messages per day (0 = unlimited)')
    )
    monthly_whatsapp_limit = models.PositiveIntegerField(
        blank=True, 
        null=True,
        verbose_name=_('Monthly WhatsApp Limit'),
        help_text=_('Maximum number of WhatsApp messages per month (0 = unlimited)')
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated At'))
    
    class Meta:
        verbose_name = _('School WhatsApp Configuration')
        verbose_name_plural = _('School WhatsApp Configurations')
        unique_together = ['school', 'provider']
    
    def __str__(self):
        return f"{self.school.name} - {self.get_provider_display()}"
    
    def get_config_data(self):
        """Return configuration data as dictionary"""
        config = {
            'provider': self.provider,
            'is_active': self.is_active,
            'use_global_settings': self.use_global_settings,
            'custom_sender_phone': self.custom_sender_phone,
            'daily_whatsapp_limit': self.daily_whatsapp_limit,
            'monthly_whatsapp_limit': self.monthly_whatsapp_limit,
        }
        
        if not self.use_global_settings:
            if self.provider == 'mobilesasa':
                config.update({
                    'api_token': self.mobilesasa_api_token,
                    'account_uuid': self.mobilesasa_account_uuid,
                    'sender_phone': self.mobilesasa_sender_phone or self.custom_sender_phone,
                })
            elif self.provider == 'meta':
                config.update({
                    'phone_number_id': self.meta_phone_number_id,
                    'waba_id': self.meta_waba_id,
                    'access_token': self.meta_access_token,
                    'app_id': self.meta_app_id,
                    'app_secret': self.meta_app_secret,
                    'webhook_verify_token': self.meta_webhook_verify_token,
                })
            elif self.provider == 'twilio':
                config.update({
                    'account_sid': self.twilio_account_sid,
                    'auth_token': self.twilio_auth_token,
                    'from_number': self.twilio_from_number,
                })
            elif self.provider == 'africastalking':
                config.update({
                    'username': self.africastalking_username,
                    'api_key': self.africastalking_api_key,
                    'sender_phone': self.africastalking_sender_phone,
                })
            elif self.provider == 'infobip':
                config.update({
                    'api_key': self.infobip_api_key,
                    'base_url': self.infobip_base_url,
                    'sender_phone': self.infobip_sender_phone,
                })
        return config


class DatabaseBackup(models.Model):
    """Stores metadata for database backups (both Master and Tenant databases)"""
    BACKUP_TYPE_CHOICES = [
        ('master', _('Master Database')),
        ('tenant', _('Tenant Database')),
    ]
    STATUS_CHOICES = [
        ('completed', _('Completed')),
        ('failed', _('Failed')),
        ('in_progress', _('In Progress')),
    ]

    school = models.ForeignKey(
        School, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='database_backups',
        help_text=_("Associated school tenant. Null indicates the master database.")
    )
    db_alias = models.CharField(max_length=100, default='default', verbose_name=_("Database Alias"))
    backup_type = models.CharField(max_length=20, choices=BACKUP_TYPE_CHOICES, default='tenant', verbose_name=_("Backup Type"))
    file_name = models.CharField(max_length=255, verbose_name=_("File Name"))
    file_path = models.CharField(max_length=500, verbose_name=_("File Path"))
    file_size_bytes = models.BigIntegerField(default=0, verbose_name=_("File Size (Bytes)"))
    engine = models.CharField(max_length=50, default='sqlite3', verbose_name=_("Database Engine"))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='completed', verbose_name=_("Status"))
    error_message = models.TextField(blank=True, null=True, verbose_name=_("Error Message"))
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='created_database_backups',
        verbose_name=_("Created By")
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))

    class Meta:
        verbose_name = _("Database Backup")
        verbose_name_plural = _("Database Backups")
        ordering = ['-created_at']

    def __str__(self):
        target = self.school.name if self.school else f"Master ({self.db_alias})"
        return f"Backup - {target} - {self.created_at.strftime('%Y-%m-%d %H:%M:%S')}"

    @property
    def file_size_display(self):
        """Format byte size into human readable string"""
        bytes_val = self.file_size_bytes or 0
        if bytes_val < 1024:
            return f"{bytes_val} B"
        elif bytes_val < 1024 * 1024:
            return f"{round(bytes_val / 1024, 1)} KB"
        elif bytes_val < 1024 * 1024 * 1024:
            return f"{round(bytes_val / (1024 * 1024), 2)} MB"
        else:
            return f"{round(bytes_val / (1024 * 1024 * 1024), 2)} GB"


class NotificationTemplate(models.Model):
    """
    Unified Notification Template model for Email, SMS, and WhatsApp.
    Supports both Global (system-wide) templates (school=None)
    and School-specific templates (school=School instance).
    """
    CHANNEL_CHOICES = [
        ('email', _('Email')),
        ('sms', _('SMS')),
        ('whatsapp', _('WhatsApp')),
    ]

    CATEGORY_CHOICES = [
        ('fees', _('Fees & Finance')),
        ('academics', _('Academics & Exams')),
        ('attendance', _('Attendance')),
        ('notices', _('Notices & Announcements')),
        ('events', _('Events & Activities')),
        ('system', _('System & Account')),
        ('other', _('Other')),
    ]

    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notification_templates',
        verbose_name=_('School'),
        help_text=_('If empty, this is a global system template')
    )
    code = models.CharField(
        max_length=100,
        db_index=True,
        verbose_name=_('Template Code'),
        help_text=_('Unique identifier code, e.g. fee_reminder, payment_receipt, welcome_user')
    )
    name = models.CharField(
        max_length=255,
        verbose_name=_('Template Name'),
        help_text=_('Descriptive name, e.g. Fee Balance Reminder')
    )
    channel = models.CharField(
        max_length=20,
        choices=CHANNEL_CHOICES,
        default='email',
        verbose_name=_('Channel')
    )
    category = models.CharField(
        max_length=30,
        choices=CATEGORY_CHOICES,
        default='other',
        verbose_name=_('Category')
    )
    
    # Email-specific fields
    subject = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_('Subject'),
        help_text=_('Email subject line. Supports dynamic tags like {{ student_name }}')
    )
    heading = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_('Headline / Title'),
        help_text=_('Main title displayed inside email body above content')
    )
    body = models.TextField(
        verbose_name=_('Message Body / Content'),
        help_text=_('Body text with dynamic tags (e.g., {{ student_name }}, {{ balance }})')
    )
    hero_image = models.ImageField(
        upload_to='templates/banners/',
        blank=True,
        null=True,
        verbose_name=_('Hero / Feature Banner Image')
    )
    button_text = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Action Button Text'),
        help_text=_('e.g. READ MORE HERE, PAY NOW, VIEW INVOICE')
    )
    button_url = models.CharField(
        max_length=500,
        blank=True,
        verbose_name=_('Action Button URL'),
        help_text=_('Target URL or dynamic tag e.g. {{ payment_url }}')
    )
    
    # Metadata & Tags
    available_tags = models.CharField(
        max_length=500,
        blank=True,
        verbose_name=_('Available Tags'),
        help_text=_('Comma-separated list of tags, e.g. student_name, balance, due_date, school_name')
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Is Active')
    )
    is_system = models.BooleanField(
        default=False,
        verbose_name=_('Built-in System Template')
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated At'))

    objects = models.Manager()

    class Meta:
        verbose_name = _('Notification Template')
        verbose_name_plural = _('Notification Templates')
        ordering = ['channel', 'category', 'name']
        constraints = [
            models.UniqueConstraint(
                fields=['school', 'code', 'channel'],
                name='unique_school_channel_code'
            )
        ]

    def __str__(self):
        scope = self.school.name if self.school else 'Global'
        return f"[{scope}] {self.name} ({self.get_channel_display()})"

    def get_tags_list(self):
        """Return list of available tags"""
        if not self.available_tags:
            return []
        return [t.strip() for t in self.available_tags.split(',') if t.strip()]

    def interpolate(self, text, context):
        """Safely interpolate tags like {{ key }} or {key} from context"""
        if not text:
            return ''
        result = str(text)
        for key, value in context.items():
            str_val = '' if value is None else str(value)
            result = result.replace(f'{{{{ {key} }}}}', str_val)
            result = result.replace(f'{{{{{key}}}}}', str_val)
            result = result.replace(f'{{{key}}}', str_val)
        return result

    def render_content(self, context):
        """Render subject, heading, body, and button_url with context"""
        return {
            'subject': self.interpolate(self.subject, context),
            'heading': self.interpolate(self.heading, context),
            'body': self.interpolate(self.body, context),
            'button_text': self.interpolate(self.button_text, context),
            'button_url': self.interpolate(self.button_url, context),
        }

