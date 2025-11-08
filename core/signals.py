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
        # Get the creator from the request (if available in thread local)
        # This would need to be set in middleware or view
        # For now, we'll handle this in views directly
        pass


# Note: Other model signals will be added in their respective apps
# For example: Student signals in students/signals.py
# This keeps the code modular and organized
