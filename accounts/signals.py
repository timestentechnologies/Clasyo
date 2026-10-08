import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from .models import User
from core.services.notification_templates import send_notification_by_template

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def user_created(sender, instance, created, **kwargs):
    """Signal triggered when a new user is created"""
    if not created:
        return

    # Skip if caller handles credential emailing directly (e.g., SchoolCreateView, AdminCreateView)
    if getattr(instance, '_skip_welcome_email', False):
        return

    if not instance.email:
        return

    try:
        school = instance.school
        school_name = school.name if school else 'Clasyo School Management'
        role_name = instance.get_role_display() if instance.role else ('Super Admin' if instance.is_superuser else 'User')

        host = settings.ALLOWED_HOSTS[0] if (getattr(settings, 'ALLOWED_HOSTS', None) and settings.ALLOWED_HOSTS[0] not in ('*', 'localhost', '127.0.0.1')) else 'clasyo.co.ke'
        login_url = f"https://{host}/accounts/login/"

        context = {
            'user_full_name': instance.get_full_name() or instance.email,
            'name': instance.get_full_name() or instance.email,
            'school_name': school_name,
            'role': role_name,
            'email': instance.email,
            'username': instance.email,
            'temporary_password': '',
            'credentials_info': '',
            'school_slug': school.slug if school else '',
            'login_url': login_url,
        }

        send_notification_by_template(
            code='welcome_user',
            channel='email',
            recipients=[instance.email],
            context=context,
            school=school,
            fail_silently=True,
        )
    except Exception as e:
        logger.error(f"Error sending welcome email via notification template: {e}")
