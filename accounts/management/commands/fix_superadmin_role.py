from django.core.management.base import BaseCommand
from accounts.models import User


class Command(BaseCommand):
    help = 'Fix users with incorrect "super_admin" role to "superadmin"'

    def handle(self, *args, **options):
        # Find users with wrong role
        wrong_role_users = User.objects.filter(role='super_admin')
        
        if not wrong_role_users.exists():
            self.stdout.write(self.style.SUCCESS('✓ No users found with incorrect role'))
            return
        
        count = wrong_role_users.count()
        self.stdout.write(f'Found {count} user(s) with role="super_admin"')
        
        for user in wrong_role_users:
            self.stdout.write(f'  Fixing: {user.email}')
            user.role = 'superadmin'
            user.save(update_fields=['role'])
        
        self.stdout.write(self.style.SUCCESS(f'\n✓ Fixed {count} user(s)'))
        self.stdout.write(self.style.SUCCESS('All users now have role="superadmin"'))
