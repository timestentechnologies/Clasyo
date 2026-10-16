from django.db import migrations


def backfill_enrollment_statuses(apps, schema_editor):
    Student = apps.get_model('students', 'Student')

    for s in Student.objects.all():
        updated_fields = []
        
        # 1. Backfill intake cohort from academic year if empty
        if not s.intake_cohort and s.academic_year:
            s.intake_cohort = s.academic_year.name
            updated_fields.append('intake_cohort')

        # 2. Backfill enrollment status
        target_status = 'enrolled'
        if s.is_alumni or getattr(s, 'exit_type', '') == 'graduation':
            target_status = 'graduated'
        elif 'transfer' in getattr(s, 'exit_type', ''):
            target_status = 'transferred'
        elif not s.is_active:
            target_status = 'withdrawn'
        else:
            target_status = 'enrolled'

        if s.enrollment_status != target_status:
            s.enrollment_status = target_status
            updated_fields.append('enrollment_status')

        if updated_fields:
            s.save(update_fields=updated_fields)


def reverse_backfill(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('students', '0011_student_enrollment_status_student_intake_cohort_and_more'),
    ]

    operations = [
        migrations.RunPython(backfill_enrollment_statuses, reverse_backfill),
    ]
