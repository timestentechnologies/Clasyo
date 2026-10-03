"""
Management Command: run_automated_reminders
Triggers automated reminders for upcoming events, overdue & pending fees,
and scheduled school notifications across Email, SMS, and WhatsApp channels.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from tenants.models import School
from core.services.automated_reminders import trigger_all_automated_reminders, trigger_event_reminders, trigger_fee_reminders


class Command(BaseCommand):
    help = "Run automated reminder jobs for upcoming events, pending fees, and notices across Email, SMS, and WhatsApp"

    def add_arguments(self, parser):
        parser.add_argument(
            '--school',
            type=str,
            help='Optional school slug to target a specific school only'
        )
        parser.add_argument(
            '--job',
            type=str,
            choices=['all', 'events', 'fees'],
            default='all',
            help='Specify which automated reminder job to run (all, events, fees)'
        )
        parser.add_argument(
            '--hours-ahead',
            type=int,
            default=48,
            help='Hours ahead to look for upcoming events (default: 48)'
        )

    def handle(self, *args, **options):
        school_slug = options.get('school')
        job = options.get('job', 'all')
        hours_ahead = options.get('hours_ahead', 48)

        target_school = None
        if school_slug:
            try:
                target_school = School.objects.get(slug=school_slug)
                self.stdout.write(self.style.SUCCESS(f"Targeting school: {target_school.name}"))
            except School.DoesNotExist:
                self.stderr.write(self.style.ERROR(f"School with slug '{school_slug}' not found."))
                return

        self.stdout.write(f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting automated reminder job: '{job}'...")

        if job == 'events':
            res = trigger_event_reminders(school=target_school, hours_ahead=hours_ahead)
            self.stdout.write(self.style.SUCCESS(
                f"Event Reminders Completed: {res.get('events_processed', 0)} events processed, "
                f"{res.get('reminders_dispatched', 0)} reminders dispatched."
            ))
        elif job == 'fees':
            res = trigger_fee_reminders(school=target_school)
            self.stdout.write(self.style.SUCCESS(
                f"Fee Reminders Completed: {res.get('reminders_sent', 0)} student fee reminders sent."
            ))
        else:
            res = trigger_all_automated_reminders(school=target_school)
            ev_count = res.get('events', {}).get('reminders_dispatched', 0)
            fee_count = res.get('fees', {}).get('reminders_sent', 0)
            self.stdout.write(self.style.SUCCESS(
                f"All Reminders Executed Successfully! Event Reminders: {ev_count} | Fee Reminders: {fee_count}"
            ))
