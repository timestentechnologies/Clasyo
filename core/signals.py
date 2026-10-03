"""
Signal handlers for automatic notifications
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .notifications import NotificationService

User = get_user_model()


@receiver(post_save, sender=User)
def user_created_notification(sender, instance, created, **kwargs):
    """Send notification when a user is created"""
    if created and not instance.is_superuser:
        pass


try:
    from communication.models import Notice

    @receiver(post_save, sender=Notice)
    def auto_notice_notification(sender, instance, created, **kwargs):
        """Automatically dispatch notifications when a notice is created"""
        if created:
            try:
                from core.services.automated_reminders import dispatch_notice_notifications
                dispatch_notice_notifications(instance)
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Signal failed to dispatch notice {instance.pk}: {e}")
except Exception:
    pass


try:
    from core.models import CalendarEvent

    @receiver(post_save, sender=CalendarEvent)
    def auto_calendar_event_notification(sender, instance, created, **kwargs):
        """Automatically dispatch invitations when a calendar event is created"""
        if created:
            try:
                from core.services.automated_reminders import dispatch_event_invitation
                dispatch_event_invitation(instance)
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Signal failed to dispatch event {instance.pk}: {e}")
except Exception:
    pass

