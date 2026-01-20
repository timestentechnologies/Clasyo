# Generated manually: Add school FK to Student and backfill existing records
from django.db import migrations, models
import django.db.models.deletion


def backfill_student_school(apps, schema_editor):
    Student = apps.get_model('students', 'Student')
    Class = apps.get_model('academics', 'Class')
    User = apps.get_model('accounts', 'User')

    qs = Student.objects.filter(school__isnull=True)
    for s in qs.iterator():
        school_id = None
        try:
            # Prefer the class' school
            if getattr(s, 'current_class_id', None):
                try:
                    cls = Class.objects.only('id', 'school_id').get(id=s.current_class_id)
                    school_id = cls.school_id
                except Exception:
                    pass
            # Then user's school
            if not school_id and getattr(s, 'user_id', None):
                try:
                    u = User.objects.only('id', 'school_id').get(id=s.user_id)
                    school_id = u.school_id
                except Exception:
                    pass
            # Then created_by's school
            if not school_id and getattr(s, 'created_by_id', None):
                try:
                    cb = User.objects.only('id', 'school_id').get(id=s.created_by_id)
                    school_id = cb.school_id
                except Exception:
                    pass
            # Then parent_user's school
            if not school_id and getattr(s, 'parent_user_id', None):
                try:
                    pu = User.objects.only('id', 'school_id').get(id=s.parent_user_id)
                    school_id = pu.school_id
                except Exception:
                    pass
        except Exception:
            school_id = None
        if school_id:
            Student.objects.filter(id=s.id).update(school_id=school_id)


def noop_reverse(apps, schema_editor):
    # No reverse migration for backfill
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('students', '0001_initial'),
        ('tenants', '0001_initial'),
        ('academics', '0002_initial'),
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='student',
            name='school',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='students', to='tenants.school'),
        ),
        migrations.RunPython(backfill_student_school, reverse_code=noop_reverse),
    ]
