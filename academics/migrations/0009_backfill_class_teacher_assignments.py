# Generated manually to safely backfill historical ClassTeacherAssignment records from existing Section.class_teacher

from django.db import migrations


def backfill_class_teacher_assignments(apps, schema_editor):
    Section = apps.get_model('academics', 'Section')
    AcademicYear = apps.get_model('core', 'AcademicYear')
    ClassTeacherAssignment = apps.get_model('academics', 'ClassTeacherAssignment')

    sections_with_teacher = Section.objects.filter(class_teacher__isnull=False).select_related('class_name')

    for section in sections_with_teacher:
        school = getattr(section.class_name, 'school', None)
        year_qs = AcademicYear.objects.filter(is_active=True)
        if school:
            year_qs = year_qs.filter(school=school)
        active_year = year_qs.first()

        if not active_year and school:
            active_year = AcademicYear.objects.filter(school=school).order_by('-start_date').first()
        elif not active_year:
            active_year = AcademicYear.objects.order_by('-start_date').first()

        if active_year:
            ClassTeacherAssignment.objects.get_or_create(
                section=section,
                academic_year=active_year,
                teacher_id=section.class_teacher_id,
                defaults={'is_active': True}
            )


def reverse_backfill(apps, schema_editor):
    # No rollback required to preserve data integrity
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('academics', '0008_classteacherassignment'),
    ]

    operations = [
        migrations.RunPython(backfill_class_teacher_assignments, reverse_backfill),
    ]
