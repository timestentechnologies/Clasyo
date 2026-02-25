from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('students', '0002_student_school'),
        ('core', '0001_initial'),
        ('academics', '0002_initial'),
        ('tenants', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='StudentSubject',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_active', models.BooleanField(default=True, verbose_name='Is Active')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created At')),
                ('academic_year', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='student_subjects', to='core.academicyear')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_student_subjects', to=settings.AUTH_USER_MODEL)),
                ('school', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='student_subjects', to='tenants.school')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='subject_enrollments', to='students.student')),
                ('subject', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='student_enrollments', to='academics.subject')),
            ],
            options={
                'verbose_name': 'Student Subject',
                'verbose_name_plural': 'Student Subjects',
                'ordering': ['student', 'subject'],
                'unique_together': {('student', 'subject', 'academic_year')},
            },
        ),
        migrations.AddIndex(
            model_name='studentsubject',
            index=models.Index(fields=['student', 'academic_year'], name='students_stu_student_6c7f98_idx'),
        ),
        migrations.AddIndex(
            model_name='studentsubject',
            index=models.Index(fields=['subject', 'academic_year'], name='students_stu_subject_e2b339_idx'),
        ),
    ]
