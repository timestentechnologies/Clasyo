from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from tenants.models import School
from superadmin.models import SchoolPaymentConfiguration

User = get_user_model()

class Command(BaseCommand):
    help = 'Create sample school payment configuration data for testing'

    def handle(self, *args, **options):
        self.stdout.write('Creating sample payment configuration data...')
        
        # Get or create a test school
        school, created = School.objects.get_or_create(
            slug='demo-school',
            defaults={
                'name': 'Demo School',
                'email': 'demo@school.com',
                'phone': '+254 123 456 789',
                'address': '123 Demo Street',
                'city': 'Nairobi',
                'country': 'Kenya',
                'is_active': True,
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created school: {school.name}'))
        else:
            self.stdout.write(f'Using existing school: {school.name}')
        
        # Create sample payment configurations
        configs = [
            {
                'gateway': 'mpesa_stk',
                'mpesa_consumer_key': 'test_consumer_key',
                'mpesa_consumer_secret': 'test_consumer_secret',
                'mpesa_passkey': 'test_passkey',
                'mpesa_shortcode': '174379',
                'is_active': True,
            },
            {
                'gateway': 'mpesa_paybill',
                'mpesa_paybill_number': '123456',
                'mpesa_paybill_account_number': 'SCHOOL001',
                'mpesa_paybill_bank_name': 'Equity Bank',
                'is_active': True,
            },
            {
                'gateway': 'paypal',
                'paypal_email': 'demo@school.com',
                'is_active': True,
            },
            {
                'gateway': 'bank',
                'bank_name': 'Equity Bank',
                'bank_account_name': 'Demo School',
                'bank_account_number': '1234567890',
                'bank_branch': 'Main Branch',
                'is_active': False,
            },
            {
                'gateway': 'cash',
                'payment_instructions': 'Please visit the school office between 8am-4pm to make cash payments. Receipt will be provided immediately.',
                'is_active': True,
            }
        ]
        
        created_count = 0
        for config_data in configs:
            config, created = SchoolPaymentConfiguration.objects.get_or_create(
                school=school,
                gateway=config_data['gateway'],
                defaults=config_data
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'  Created {config.get_gateway_display()} configuration'))
            else:
                self.stdout.write(f'  {config.get_gateway_display()} configuration already exists')
        
        self.stdout.write(self.style.SUCCESS(f'\nDone! Created {created_count} new payment configurations for {school.name}'))
        self.stdout.write(f'Visit: http://127.0.0.1:8000/school/{school.slug}/payment-config/ to view them')
