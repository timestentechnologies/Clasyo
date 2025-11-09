from django.core.management.base import BaseCommand
from django.contrib.sessions.models import Session
from accounts.models import User


class Command(BaseCommand):
    help = 'Clear all sessions and display superadmin info'

    def handle(self, *args, **options):
        # Clear all sessions
        session_count = Session.objects.all().count()
        Session.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(f'✓ Cleared {session_count} sessions'))
        
        # Display superadmin info
        superadmins = User.objects.filter(role='superadmin')
        
        if superadmins.exists():
            self.stdout.write(self.style.SUCCESS(f'\n✓ Found {superadmins.count()} superadmin(s):'))
            for admin in superadmins:
                self.stdout.write(f'  - Email: {admin.email}')
                self.stdout.write(f'    Name: {admin.get_full_name()}')
                self.stdout.write(f'    Role: {admin.role}')
                self.stdout.write(f'    Active: {admin.is_active}')
                self.stdout.write('')
        else:
            self.stdout.write(self.style.WARNING('✗ No superadmin users found!'))
            
            # Check for users with wrong role name
            wrong_role = User.objects.filter(role='super_admin')
            if wrong_role.exists():
                self.stdout.write(self.style.ERROR(f'\n✗ Found {wrong_role.count()} user(s) with incorrect role "super_admin"'))
                for user in wrong_role:
                    self.stdout.write(f'  - {user.email}')
                self.stdout.write(self.style.WARNING('\nRun: python manage.py fix_superadmin_role'))
