from django.core.management.base import BaseCommand
from accounts.models import User


class Command(BaseCommand):
    help = 'Create a test teacher if none exist'

    def handle(self, *args, **options):
        # Check if any teachers exist
        teacher_count = User.objects.filter(role='teacher').count()
        
        self.stdout.write(f'Found {teacher_count} teacher(s) in the database')
        
        if teacher_count == 0:
            self.stdout.write('Creating test teacher...')
            teacher = User.objects.create_user(
                email='teacher@test.com',
                password='password123',
                first_name='John',
                last_name='Doe',
                role='teacher',
                is_active=True
            )
            self.stdout.write(self.style.SUCCESS(f'✓ Created teacher: {teacher.email}'))
        else:
            self.stdout.write(self.style.SUCCESS('Teachers already exist:'))
            for teacher in User.objects.filter(role='teacher'):
                self.stdout.write(f'  - {teacher.email}: {teacher.get_full_name()}')
