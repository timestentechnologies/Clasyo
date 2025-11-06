from celery import shared_task
from django.core.management import call_command
from django.conf import settings
import os
from datetime import datetime


@shared_task
def auto_backup():
    """Automated database backup task"""
    try:
        # Create backup directory if not exists
        backup_dir = os.path.join(settings.BASE_DIR, 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        
        # Generate backup filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = os.path.join(backup_dir, f'backup_{timestamp}.json')
        
        # Run dumpdata command
        with open(backup_file, 'w') as f:
            call_command('dumpdata', '--natural-foreign', '--natural-primary', 
                        '--indent=2', stdout=f)
        
        return f"Backup created successfully: {backup_file}"
    
    except Exception as e:
        return f"Backup failed: {str(e)}"


@shared_task
def cleanup_old_notifications():
    """Clean up old read notifications"""
    from django.utils import timezone
    from datetime import timedelta
    from .models import Notification
    
    # Delete read notifications older than 30 days
    cutoff_date = timezone.now() - timedelta(days=30)
    deleted_count = Notification.objects.filter(
        is_read=True,
        read_at__lt=cutoff_date
    ).delete()[0]
    
    return f"Deleted {deleted_count} old notifications"


@shared_task
def send_event_reminders():
    """Send reminders for upcoming events"""
    from django.utils import timezone
    from datetime import timedelta
    from .models import CalendarEvent, Notification
    
    # Get events happening in next 24 hours with reminders enabled
    tomorrow = timezone.now() + timedelta(days=1)
    events = CalendarEvent.objects.filter(
        start_date__lte=tomorrow,
        start_date__gte=timezone.now(),
        reminder_enabled=True
    )
    
    notifications_created = 0
    
    for event in events:
        # Create notification for event creator
        Notification.objects.create(
            user=event.created_by,
            title=f"Upcoming Event: {event.title}",
            message=f"Event '{event.title}' is scheduled for {event.start_date}",
            notification_type='info',
            link=f'/calendar/'
        )
        
        # Create notifications for participants
        for participant in event.participants.all():
            Notification.objects.create(
                user=participant,
                title=f"Upcoming Event: {event.title}",
                message=f"Event '{event.title}' is scheduled for {event.start_date}",
                notification_type='info',
                link=f'/calendar/'
            )
            notifications_created += 1
    
    return f"Sent {notifications_created} event reminders"
