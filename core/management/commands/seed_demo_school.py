from django.core.management.base import BaseCommand
from core.sample_data import wipe_and_reseed_demo_school, generate_all_sample_data_for_school
from tenants.models import School


class Command(BaseCommand):
    help = 'Erase existing operational/test data and seed comprehensive sample demo data for Demo School'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clean',
            action='store_true',
            help='Wipe all existing data first before generating sample records',
        )

    def handle(self, *args, **options):
        clean = options.get('clean', True)
        demo_school = School.objects.using('default').filter(slug='demo-school').first()
        if not demo_school:
            self.stdout.write(self.style.ERROR("Demo School ('demo-school') does not exist in master DB."))
            return

        self.stdout.write(f"Processing Demo School (slug='{demo_school.slug}')...")
        if clean:
            self.stdout.write(self.style.WARNING("Erasing old data and generating fresh sample records..."))
            stats = wipe_and_reseed_demo_school(demo_school)
        else:
            self.stdout.write("Generating sample records without wiping...")
            stats = generate_all_sample_data_for_school(demo_school)

        self.stdout.write(self.style.SUCCESS(f"Successfully generated Demo School sample data: {stats}"))
