from django.core.management.base import BaseCommand
from django.contrib.sessions.models import Session
import pickle
from django.conf import settings


class Command(BaseCommand):
    help = 'Clear all sessions with impersonation data'

    def handle(self, *args, **options):
        cleared_count = 0
        total_sessions = Session.objects.all().count()
        
        self.stdout.write(f'Scanning {total_sessions} sessions...')
        
        for session in Session.objects.all():
            try:
                session_data = session.get_decoded()
                
                # Check if this session has impersonation data
                if 'impersonated_user_id' in session_data or 'original_user_id' in session_data:
                    session.delete()
                    cleared_count += 1
                    self.stdout.write(f'  Cleared session with impersonation data')
            except Exception as e:
                # Skip invalid sessions
                pass
        
        if cleared_count > 0:
            self.stdout.write(self.style.SUCCESS(f'\n✓ Cleared {cleared_count} session(s) with impersonation data'))
        else:
            self.stdout.write(self.style.SUCCESS('\n✓ No sessions with impersonation data found'))
        
        self.stdout.write(f'Total sessions remaining: {Session.objects.count()}')
