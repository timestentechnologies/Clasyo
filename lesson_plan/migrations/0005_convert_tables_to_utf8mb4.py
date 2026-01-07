# Generated manually to fix table charset for lesson_plan app

from django.db import migrations, connection


def convert_tables_to_utf8mb4(apps, schema_editor):
    """
    Convert lesson_plan tables to utf8mb4 charset to support Unicode characters
    """
    with connection.cursor() as cursor:
        # Convert main lesson_plan table
        cursor.execute("""
            ALTER TABLE lesson_plan_lessonplan 
            CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
        """)
        
        # Convert lesson_plan_template table
        cursor.execute("""
            ALTER TABLE lesson_plan_lessonplantemplate 
            CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
        """)
        
        # Convert lesson_plan_standard table
        cursor.execute("""
            ALTER TABLE lesson_plan_lessonplanstandard 
            CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
        """)
        
        # Convert lesson_plan_feedback table
        cursor.execute("""
            ALTER TABLE lesson_plan_lessonplanfeedback 
            CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
        """)
        
        # Convert lesson_plan_resource table
        cursor.execute("""
            ALTER TABLE lesson_plan_lessonplanresource 
            CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
        """)


def reverse_convert_tables(apps, schema_editor):
    """
    Reverse operation - convert back to default charset (not recommended)
    """
    # Keeping as placeholder for migration reversibility
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('lesson_plan', '0004_fix_textfield_charset'),
    ]

    operations = [
        migrations.RunPython(
            convert_tables_to_utf8mb4,
            reverse_convert_tables,
        ),
    ]
