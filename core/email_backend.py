import logging
from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail.backends.smtp import EmailBackend as SmtpEmailBackend
from django.core.mail.backends.console import EmailBackend as ConsoleEmailBackend
from django.conf import settings

logger = logging.getLogger(__name__)


class DynamicEmailBackend(BaseEmailBackend):
    """
    Dynamic Email Backend that routes all outgoing emails through the
    active GlobalEmailConfiguration defined by the Super Admin in the database.
    Falls back gracefully to settings.py / environment configuration if no
    database configuration is active.
    """

    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently, **kwargs)
        self.init_kwargs = kwargs

    def _get_active_backend(self):
        """
        Determines the backend and default sender information from the active
        GlobalEmailConfiguration in the database or fallback environment settings.
        Returns (backend_instance, default_from_email)
        """
        try:
            from superadmin.models import GlobalEmailConfiguration
            active_config = GlobalEmailConfiguration.objects.using('default').filter(is_active=True).first()
            if active_config:
                provider = active_config.provider
                sender_email = active_config.default_from_email or getattr(settings, 'DEFAULT_FROM_EMAIL', '')
                sender_name = active_config.default_from_name or getattr(settings, 'DEFAULT_FROM_NAME', 'Clasyo')
                formatted_from = f"{sender_name} <{sender_email}>" if (sender_name and sender_email) else sender_email

                if provider == 'smtp':
                    backend = SmtpEmailBackend(
                        host=active_config.smtp_host or 'localhost',
                        port=active_config.smtp_port or 587,
                        username=active_config.smtp_username or '',
                        password=active_config.smtp_password or '',
                        use_tls=active_config.smtp_use_tls,
                        use_ssl=active_config.smtp_use_ssl,
                        timeout=getattr(settings, 'EMAIL_TIMEOUT', 15),
                        fail_silently=self.fail_silently,
                    )
                    return backend, formatted_from

                elif provider == 'sendgrid':
                    backend = SmtpEmailBackend(
                        host='smtp.sendgrid.net',
                        port=587,
                        username='apikey',
                        password=active_config.sendgrid_api_key or '',
                        use_tls=True,
                        use_ssl=False,
                        timeout=getattr(settings, 'EMAIL_TIMEOUT', 15),
                        fail_silently=self.fail_silently,
                    )
                    sendgrid_sender = active_config.sendgrid_sender_email or sender_email
                    sendgrid_name = active_config.sendgrid_sender_name or sender_name
                    from_addr = f"{sendgrid_name} <{sendgrid_sender}>" if (sendgrid_name and sendgrid_sender) else sendgrid_sender
                    return backend, from_addr

                elif provider == 'mailgun':
                    backend = SmtpEmailBackend(
                        host='smtp.mailgun.org',
                        port=587,
                        username=f"postmaster@{active_config.mailgun_domain}" if active_config.mailgun_domain else '',
                        password=active_config.mailgun_api_key or '',
                        use_tls=True,
                        use_ssl=False,
                        timeout=getattr(settings, 'EMAIL_TIMEOUT', 15),
                        fail_silently=self.fail_silently,
                    )
                    mg_sender = active_config.mailgun_sender_email or sender_email
                    from_addr = f"{sender_name} <{mg_sender}>" if (sender_name and mg_sender) else mg_sender
                    return backend, from_addr

                elif provider == 'ses':
                    region = active_config.ses_region or 'us-east-1'
                    backend = SmtpEmailBackend(
                        host=f"email-smtp.{region}.amazonaws.com",
                        port=587,
                        username=active_config.ses_access_key or '',
                        password=active_config.ses_secret_key or '',
                        use_tls=True,
                        use_ssl=False,
                        timeout=getattr(settings, 'EMAIL_TIMEOUT', 15),
                        fail_silently=self.fail_silently,
                    )
                    ses_sender = active_config.ses_sender_email or sender_email
                    from_addr = f"{sender_name} <{ses_sender}>" if (sender_name and ses_sender) else ses_sender
                    return backend, from_addr

                elif provider == 'postmark':
                    backend = SmtpEmailBackend(
                        host='smtp.postmarkapp.com',
                        port=587,
                        username=active_config.postmark_api_key or '',
                        password=active_config.postmark_api_key or '',
                        use_tls=True,
                        use_ssl=False,
                        timeout=getattr(settings, 'EMAIL_TIMEOUT', 15),
                        fail_silently=self.fail_silently,
                    )
                    pm_sender = active_config.postmark_sender_email or sender_email
                    pm_name = active_config.postmark_sender_name or sender_name
                    from_addr = f"{pm_name} <{pm_sender}>" if (pm_name and pm_sender) else pm_sender
                    return backend, from_addr

        except Exception as e:
            logger.warning(f"Error querying active GlobalEmailConfiguration: {e}")

        # Fallback to standard settings
        fallback_from = getattr(settings, 'DEFAULT_FROM_EMAIL', '')
        if getattr(settings, 'EMAIL_HOST_USER', None):
            backend = SmtpEmailBackend(
                host=getattr(settings, 'EMAIL_HOST', 'smtp.gmail.com'),
                port=getattr(settings, 'EMAIL_PORT', 587),
                username=getattr(settings, 'EMAIL_HOST_USER', ''),
                password=getattr(settings, 'EMAIL_HOST_PASSWORD', ''),
                use_tls=getattr(settings, 'EMAIL_USE_TLS', True),
                use_ssl=getattr(settings, 'EMAIL_USE_SSL', False),
                timeout=getattr(settings, 'EMAIL_TIMEOUT', 15),
                fail_silently=self.fail_silently,
            )
        else:
            backend = ConsoleEmailBackend(fail_silently=self.fail_silently)

        return backend, fallback_from

    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        backend, default_from = self._get_active_backend()

        # Ensure from_email is set to valid configured sender if blank
        for message in email_messages:
            if not message.from_email or message.from_email == 'webmaster@localhost':
                if default_from:
                    message.from_email = default_from

        try:
            return backend.send_messages(email_messages)
        except Exception as e:
            logger.error(f"DynamicEmailBackend failed to deliver messages: {e}")
            if not self.fail_silently:
                raise
            return 0
