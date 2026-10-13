from django.db import migrations


def backfill_enrollments(apps, schema_editor):
    Student = apps.get_model('students', 'Student')
    StudentClassEnrollment = apps.get_model('students', 'StudentClassEnrollment')
    AcademicYear = apps.get_model('core', 'AcademicYear')

    for student in Student.objects.filter(current_class__isnull=False):
        ay = student.academic_year
        if not ay and student.school:
            ay = AcademicYear.objects.filter(school=student.school, is_active=True).first()
            if not ay:
                ay = AcademicYear.objects.filter(school=student.school).order_by('-start_date').first()
        if not ay:
            ay = AcademicYear.objects.filter(is_active=True).first()
        
        if not ay:
            continue
            
        enrolled_date = student.admission_date or ay.start_date
        status = 'active' if student.is_active else ('completed' if student.is_alumni else 'withdrawn')
        
        if not StudentClassEnrollment.objects.filter(student=student, academic_year=ay).exists():
            StudentClassEnrollment.objects.create(
                student=student,
                school=student.school or (student.current_class.school if student.current_class else None),
                academic_year=ay,
                class_name=student.current_class,
                section=student.section,
                roll_number=student.roll_number or '',
                status=status,
                enrolled_date=enrolled_date,
            )
            if not student.academic_year:
                student.academic_year = ay
                student.save(update_fields=['academic_year'])


def reverse_backfill(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('students', '0007_studentclassenrollment'),
    ]

    operations = [
        migrations.RunPython(backfill_enrollments, reverse_backfill),
    ]
