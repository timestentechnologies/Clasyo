import logging
from celery import shared_task
from django.utils import timezone
from django.contrib.auth import get_user_model
from .models import Subscription, Invoice
from tenants.models import School
from django.conf import settings
from datetime import timedelta
from core.services.notification_templates import send_notification_by_template

logger = logging.getLogger(__name__)


def recipients_for_school(school):
    """Collect unique contact and admin emails for a school"""
    User = get_user_model()
    admins = list(
        User.objects.filter(school=school, role__in=['admin', 'school_admin'], is_active=True)
        .values_list('email', flat=True)
    )
    base = [e for e in [school.email] if e]
    seen = set()
    ordered = []
    for e in base + admins:
        if e and e not in seen:
            seen.add(e)
            ordered.append(e)
    return ordered


@shared_task
def check_subscription_expiry():
    """Check for expiring subscriptions and send notifications"""
    today = timezone.now().date()
    warning_date = today + timedelta(days=7)
    
    # Get subscriptions expiring in 7 days
    expiring_soon = Subscription.objects.filter(
        status='active',
        end_date=warning_date
    )
    
    for subscription in expiring_soon:
        recipients = recipients_for_school(subscription.school)
        if not recipients:
            continue
        host = settings.ALLOWED_HOSTS[0] if (getattr(settings, 'ALLOWED_HOSTS', None) and settings.ALLOWED_HOSTS[0] not in ('*', 'localhost', '127.0.0.1')) else 'clasyo.co.ke'
        renewal_url = f"https://{host}/school/{subscription.school.slug}/billing/" if subscription.school.slug else f"https://{host}/"
        context = {
            'school_name': subscription.school.name,
            'plan_name': subscription.plan.name,
            'end_date': str(subscription.end_date),
            'renewal_url': renewal_url,
        }
        send_notification_by_template(
            code='subscription_expiring',
            channel='email',
            recipients=recipients,
            context=context,
            school=subscription.school,
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
        
        recipients = recipients_for_school(school)
        if recipients:
            host = settings.ALLOWED_HOSTS[0] if (getattr(settings, 'ALLOWED_HOSTS', None) and settings.ALLOWED_HOSTS[0] not in ('*', 'localhost', '127.0.0.1')) else 'clasyo.co.ke'
            renewal_url = f"https://{host}/school/{school.slug}/billing/" if school.slug else f"https://{host}/"
            context = {
                'school_name': school.name,
                'plan_name': subscription.plan.name,
                'end_date': str(subscription.end_date),
                'renewal_url': renewal_url,
            }
            send_notification_by_template(
                code='subscription_expired',
                channel='email',
                recipients=recipients,
                context=context,
                school=school,
                fail_silently=True,
            )
    
    return f"Processed {expiring_soon.count()} expiring and {expired.count()} expired subscriptions"


@shared_task
def auto_renew_subscriptions():
    """Auto-renew subscriptions where auto_renew is enabled"""
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
        
        recipients = recipients_for_school(subscription.school)
        if recipients:
            host = settings.ALLOWED_HOSTS[0] if (getattr(settings, 'ALLOWED_HOSTS', None) and settings.ALLOWED_HOSTS[0] not in ('*', 'localhost', '127.0.0.1')) else 'clasyo.co.ke'
            billing_url = f"https://{host}/school/{subscription.school.slug}/billing/" if subscription.school.slug else f"https://{host}/"
            context = {
                'school_name': subscription.school.name,
                'plan_name': subscription.plan.name,
                'end_date': str(new_end_date),
                'billing_url': billing_url,
            }
            send_notification_by_template(
                code='subscription_renewed',
                channel='email',
                recipients=recipients,
                context=context,
                school=subscription.school,
                fail_silently=True,
            )
    
    return f"Auto-renewed {renewed_count} subscriptions"


@shared_task
def send_invoice_reminders():
    """Send invoice reminders before, on, and after due date. Also ensure trial-end invoices exist.

    - Pre-due: 3 days before due date (status in draft/sent), send a reminder once.
    - Due today: send a due reminder once.
    - Overdue: mark as overdue (if not already) and send a reminder once.
    """
    today = timezone.now().date()
    pre_days = 3

    # Ensure trial-end invoices exist for schools currently on trial
    try:
        trial_schools = School.objects.filter(is_trial=True).exclude(trial_end_date__isnull=True)
        for school in trial_schools.select_related('subscription_plan'):
            plan = getattr(school, 'subscription_plan', None)
            due = getattr(school, 'trial_end_date', None)
            if not plan or not due:
                continue
            # If no existing trial_end invoice for this due date, create one
            existing = Invoice.objects.filter(
                school=school,
                invoice_type='trial_end',
                due_date=due,
                status__in=['draft', 'sent', 'overdue']
            ).first()
            if not existing:
                try:
                    amount = plan.price
                    inv = Invoice(
                        school=school,
                        subscription=None,
                        payment=None,
                        invoice_type='trial_end',
                        status='sent',
                        plan_name=plan.name,
                        plan_description=plan.description or '',
                        amount=amount,
                        tax_amount=0,
                        total_amount=amount,
                        invoice_date=today,
                        due_date=due,
                        notes=f"Trial ends on {due}. First billing due."
                    )
                    inv.save()
                except Exception:
                    pass
    except Exception:
        pass

    # Helper to collect recipient emails for a school
    def recipients_for_school(school):
        User = get_user_model()
        admins = list(
            User.objects.filter(school=school, role__in=['admin', 'school_admin'], is_active=True)
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

    # 1) Pre-due reminders (3 days before due date)
    pre_due_date = today + timedelta(days=pre_days)
    pre_due = Invoice.objects.filter(
        status__in=['draft', 'sent'],
        due_date=pre_due_date,
        pre_due_reminder_sent_at__isnull=True,
    )
    for inv in pre_due.select_related('school'):
        recipients = recipients_for_school(inv.school)
        if not recipients:
            continue
        host = settings.ALLOWED_HOSTS[0] if (getattr(settings, 'ALLOWED_HOSTS', None) and settings.ALLOWED_HOSTS[0] not in ('*', 'localhost', '127.0.0.1')) else 'clasyo.co.ke'
        invoice_url = f"https://{host}/school/{inv.school.slug}/billing/" if inv.school.slug else f"https://{host}/"
        context = {
            'school_name': inv.school.name,
            'invoice_number': inv.invoice_number,
            'plan_name': inv.plan_name,
            'currency': getattr(settings, 'DEFAULT_CURRENCY', 'KES'),
            'total_amount': f"{inv.total_amount:,.2f}" if inv.total_amount else "0.00",
            'due_date': str(inv.due_date),
            'invoice_url': invoice_url,
        }
        try:
            send_notification_by_template(
                code='invoice_reminder',
                channel='email',
                recipients=recipients,
                context=context,
                school=inv.school,
                fail_silently=True
            )
            inv.pre_due_reminder_sent_at = timezone.now()
            inv.save(update_fields=['pre_due_reminder_sent_at'])
        except Exception as e:
            logger.error(f"Error sending pre-due invoice reminder: {e}")

    # 2) Due today reminders
    due_today = Invoice.objects.filter(
        status__in=['draft', 'sent'],
        due_date=today,
        due_reminder_sent_at__isnull=True,
    )
    for inv in due_today.select_related('school'):
        recipients = recipients_for_school(inv.school)
        if not recipients:
            continue
        host = settings.ALLOWED_HOSTS[0] if (getattr(settings, 'ALLOWED_HOSTS', None) and settings.ALLOWED_HOSTS[0] not in ('*', 'localhost', '127.0.0.1')) else 'clasyo.co.ke'
        invoice_url = f"https://{host}/school/{inv.school.slug}/billing/" if inv.school.slug else f"https://{host}/"
        context = {
            'school_name': inv.school.name,
            'invoice_number': inv.invoice_number,
            'plan_name': inv.plan_name,
            'currency': getattr(settings, 'DEFAULT_CURRENCY', 'KES'),
            'total_amount': f"{inv.total_amount:,.2f}" if inv.total_amount else "0.00",
            'due_date': str(inv.due_date),
            'invoice_url': invoice_url,
        }
        try:
            send_notification_by_template(
                code='invoice_reminder',
                channel='email',
                recipients=recipients,
                context=context,
                school=inv.school,
                fail_silently=True
            )
            inv.due_reminder_sent_at = timezone.now()
            inv.save(update_fields=['due_reminder_sent_at'])
        except Exception as e:
            logger.error(f"Error sending due-today invoice reminder: {e}")

    # 3) Overdue reminders
    overdue = Invoice.objects.filter(
        status__in=['draft', 'sent', 'overdue'],
        due_date__lt=today,
        overdue_reminder_sent_at__isnull=True,
    )
    for inv in overdue.select_related('school'):
        recipients = recipients_for_school(inv.school)
        if not recipients:
            continue
        host = settings.ALLOWED_HOSTS[0] if (getattr(settings, 'ALLOWED_HOSTS', None) and settings.ALLOWED_HOSTS[0] not in ('*', 'localhost', '127.0.0.1')) else 'clasyo.co.ke'
        invoice_url = f"https://{host}/school/{inv.school.slug}/billing/" if inv.school.slug else f"https://{host}/"
        context = {
            'school_name': inv.school.name,
            'invoice_number': inv.invoice_number,
            'plan_name': inv.plan_name,
            'currency': getattr(settings, 'DEFAULT_CURRENCY', 'KES'),
            'total_amount': f"{inv.total_amount:,.2f}" if inv.total_amount else "0.00",
            'due_date': str(inv.due_date),
            'invoice_url': invoice_url,
        }
        try:
            send_notification_by_template(
                code='invoice_overdue',
                channel='email',
                recipients=recipients,
                context=context,
                school=inv.school,
                fail_silently=True
            )
            # Mark invoice as overdue if not already
            updated_fields = ['overdue_reminder_sent_at']
            inv.overdue_reminder_sent_at = timezone.now()
            if inv.status != 'overdue':
                inv.status = 'overdue'
                updated_fields.append('status')
            inv.save(update_fields=updated_fields)
        except Exception as e:
            logger.error(f"Error sending overdue invoice reminder: {e}")

    return f"Sent pre-due: {pre_due.count()}, due: {due_today.count()}, overdue: {overdue.count()}"
