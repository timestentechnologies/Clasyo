import os
from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_saas.settings')

app = Celery('school_saas')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Celery Beat Schedule
app.conf.beat_schedule = {
    'check-subscription-expiry': {
        'task': 'subscriptions.tasks.check_subscription_expiry',
        'schedule': crontab(hour=0, minute=0),  # Run daily at midnight
    },
    'send-invoice-reminders': {
        'task': 'subscriptions.tasks.send_invoice_reminders',
        'schedule': crontab(hour=8, minute=0),  # Daily at 8 AM
    },
    'send-fee-reminders': {
        'task': 'fees.tasks.send_fee_reminders',
        'schedule': crontab(hour=9, minute=0, day_of_month=1),  # First day of month at 9 AM
    },
    'auto-backup': {
        'task': 'core.tasks.auto_backup',
        'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM
    },
}


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
