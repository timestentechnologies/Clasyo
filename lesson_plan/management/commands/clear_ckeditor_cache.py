from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.conf import settings
import os
import shutil


class Command(BaseCommand):
    help = 'Clear CKEditor cache and static files to fix security warnings'

    def handle(self, *args, **options):
        self.stdout.write('Clearing CKEditor cache and static files...')
        
        # Clear static files
        try:
            static_root = settings.STATIC_ROOT
            if static_root and os.path.exists(static_root):
                ckeditor_path = os.path.join(static_root, 'ckeditor')
                if os.path.exists(ckeditor_path):
                    shutil.rmtree(ckeditor_path)
                    self.stdout.write(self.style.SUCCESS(f'Removed CKEditor static files from {ckeditor_path}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error clearing static files: {e}'))
        
        # Collect static files
        try:
            call_command('collectstatic', '--noinput')
            self.stdout.write(self.style.SUCCESS('Static files collected successfully'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error collecting static files: {e}'))
        
        self.stdout.write(self.style.SUCCESS('CKEditor cache cleared successfully!'))
