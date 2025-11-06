from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from .models import User


@receiver(post_save, sender=User)
def user_created(sender, instance, created, **kwargs):
    """Signal triggered when a new user is created"""
    if created:
        # Send welcome email
        if instance.email:
            subject = 'Welcome to School Management System'
            message = f"""
            Dear {instance.get_full_name()},
            
            Welcome to our School Management System!
            
            Your account has been created successfully.
            Role: {instance.get_role_display()}
            Email: {instance.email}
            
            Please login to access your dashboard.
            
            Best regards,
            School Management Team
            """
            
            try:
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [instance.email],
                    fail_silently=True,
                )
            except Exception as e:
                print(f"Error sending welcome email: {e}")
