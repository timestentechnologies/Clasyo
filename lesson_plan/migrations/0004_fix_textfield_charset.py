# Generated manually to fix charset issue with text fields containing Unicode characters

from django.db import migrations, connection


def convert_text_fields_to_utf8mb4(apps, schema_editor):
    """
    Convert text fields in lesson_plan_lessonplan table to utf8mb4 charset
    to support Unicode characters like fractions (⅓, ⅔, etc.)
    """
    with connection.cursor() as cursor:
        # List of text fields that need charset conversion
        text_fields = [
            'description',
            'learning_objectives', 
            'materials_resources',
            'introduction',
            'main_content',
            'activities',
            'assessment',
            'differentiation',
            'conclusion',
            'homework',
            'notes',
            'execution_notes'
        ]
        
        for field in text_fields:
            # Convert each text field to utf8mb4 charset
            cursor.execute("""
                ALTER TABLE lesson_plan_lessonplan 
                MODIFY COLUMN {} LONGTEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
            """.format(field))


def reverse_convert_text_fields(apps, schema_editor):
    """
    Reverse operation - convert back to default charset (not recommended)
    """
    with connection.cursor() as cursor:
        # This would convert back to utf8 - but we don't want to do this
        # Keeping as placeholder for migration reversibility
        pass


class Migration(migrations.Migration):

    dependencies = [
        ('lesson_plan', '0003_lessonplan_grade_level_lessonplan_unit_title'),
    ]

    operations = [
        migrations.RunPython(
            convert_text_fields_to_utf8mb4,
            reverse_convert_text_fields,
        ),
    ]
