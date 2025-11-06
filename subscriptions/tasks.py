from celery import shared_task
from django.utils import timezone
from .models import Subscription
from django.core.mail import send_mail
from django.conf import settings


@shared_task
def check_subscription_expiry():
    """Check for expiring subscriptions and send notifications"""
    from datetime import timedelta
    
    today = timezone.now().date()
    warning_date = today + timedelta(days=7)
    
    # Get subscriptions expiring in 7 days
    expiring_soon = Subscription.objects.filter(
        status='active',
        end_date=warning_date
    )
    
    for subscription in expiring_soon:
        # Send email notification
        send_mail(
            subject='Your subscription is expiring soon',
            message=f'Your subscription for {subscription.plan.name} will expire on {subscription.end_date}. Please renew to continue using our services.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[subscription.school.email],
            fail_silently=True,
        )
    
    # Expire subscriptions
    expired = Subscription.objects.filter(
        status='active',
        end_date__lt=today
    )
    
    for subscription in expired:
        subscription.status = 'expired'
        subscription.save()
        
        # Deactivate school
        school = subscription.school
        school.is_active = False
        school.save()
        
        # Send expiration email
        send_mail(
            subject='Your subscription has expired',
            message=f'Your subscription for {subscription.plan.name} has expired. Please renew to continue using our services.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[school.email],
            fail_silently=True,
        )
    
    return f"Processed {expiring_soon.count()} expiring and {expired.count()} expired subscriptions"


@shared_task
def auto_renew_subscriptions():
    """Auto-renew subscriptions where auto_renew is enabled"""
    from datetime import timedelta
    
    today = timezone.now().date()
    
    subscriptions = Subscription.objects.filter(
        status='active',
        auto_renew=True,
        end_date=today
    )
    
    renewed_count = 0
    
    for subscription in subscriptions:
        # Create new subscription
        new_end_date = subscription.end_date + timedelta(days=365)  # Assuming yearly renewal
        
        new_subscription = Subscription.objects.create(
            school=subscription.school,
            plan=subscription.plan,
            start_date=subscription.end_date,
            end_date=new_end_date,
            status='active',
            auto_renew=True,
            is_trial=False
        )
        
        # Mark old subscription as completed
        subscription.status = 'expired'
        subscription.save()
        
        renewed_count += 1
        
        # Send confirmation email
        send_mail(
            subject='Subscription Auto-Renewed',
            message=f'Your subscription for {subscription.plan.name} has been automatically renewed until {new_end_date}.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[subscription.school.email],
            fail_silently=True,
        )
    
    return f"Auto-renewed {renewed_count} subscriptions"
