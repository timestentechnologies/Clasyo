from celery import shared_task
from django.utils import timezone
from django.contrib.auth import get_user_model
from .models import Subscription, Invoice
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


@shared_task
def send_invoice_reminders():
    """Send email notifications for invoices that are due today and those that became overdue.

    - For invoices due today (status in draft/sent), send a due reminder once.
    - For invoices past due and not paid, mark as overdue (if not already) and send an overdue reminder once.
    """
    today = timezone.now().date()

    # Helper to collect recipient emails for a school
    def recipients_for_school(school):
        User = get_user_model()
        admins = list(
            User.objects.filter(school=school, role='admin', is_active=True)
            .values_list('email', flat=True)
        )
        base = [e for e in [school.email] if e]
        # Deduplicate while preserving order
        seen = set()
        ordered = []
        for e in base + admins:
            if e and e not in seen:
                seen.add(e)
                ordered.append(e)
        return ordered

    # 1) Due today reminders
    due_today = Invoice.objects.filter(
        status__in=['draft', 'sent'],
        due_date=today,
        due_reminder_sent_at__isnull=True,
    )
    for inv in due_today.select_related('school'):
        recipients = recipients_for_school(inv.school)
        if not recipients:
            continue
        subject = f"Invoice Due Today: {inv.invoice_number}"
        message = (
            f"Hello {inv.school.name},\n\n"
            f"This is a reminder that your invoice {inv.invoice_number} for plan '{inv.plan_name}' is due today ({inv.due_date}).\n"
            f"Amount Due: {inv.total_amount}\n\n"
            f"Please make payment to avoid service interruption.\n\n"
            f"Thank you,\nClasyo Billing"
        )
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', settings.EMAIL_HOST_USER),
                recipient_list=recipients,
                fail_silently=True,
            )
            inv.due_reminder_sent_at = timezone.now()
            inv.save(update_fields=['due_reminder_sent_at'])
        except Exception:
            # Ignore email errors but don't mark as sent
            pass

    # 2) Overdue reminders
    overdue = Invoice.objects.filter(
        status__in=['draft', 'sent', 'overdue'],
        due_date__lt=today,
        overdue_reminder_sent_at__isnull=True,
    )
    for inv in overdue.select_related('school'):
        recipients = recipients_for_school(inv.school)
        if not recipients:
            continue
        subject = f"Overdue Invoice: {inv.invoice_number}"
        message = (
            f"Hello {inv.school.name},\n\n"
            f"Your invoice {inv.invoice_number} for plan '{inv.plan_name}' is overdue.\n"
            f"Due Date: {inv.due_date}\n"
            f"Amount Due: {inv.total_amount}\n\n"
            f"Please make payment as soon as possible to avoid any disruption.\n\n"
            f"Thank you,\nClasyo Billing"
        )
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', settings.EMAIL_HOST_USER),
                recipient_list=recipients,
                fail_silently=True,
            )
            # Mark invoice as overdue if not already
            updated_fields = ['overdue_reminder_sent_at']
            inv.overdue_reminder_sent_at = timezone.now()
            if inv.status != 'overdue':
                inv.status = 'overdue'
                updated_fields.append('status')
            inv.save(update_fields=updated_fields)
        except Exception:
            pass

    return f"Sent due reminders: {due_today.count()}, overdue reminders: {overdue.count()}"
