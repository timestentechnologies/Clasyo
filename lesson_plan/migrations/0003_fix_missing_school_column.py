from django.db import migrations


def add_school_id_column_if_missing(apps, schema_editor):
    connection = schema_editor.connection
    if connection.vendor != "sqlite":
        return

    with connection.cursor() as cursor:
        cursor.execute("PRAGMA table_info(lesson_plan_lessonplan)")
        columns = {row[1] for row in cursor.fetchall()}
        if "school_id" in columns:
            return

        cursor.execute("ALTER TABLE lesson_plan_lessonplan ADD COLUMN school_id bigint NULL")


class Migration(migrations.Migration):

    dependencies = [
        ("lesson_plan", "0002_alter_lessonplan_options_and_more"),
    ]

    operations = [
        migrations.RunPython(add_school_id_column_if_missing, migrations.RunPython.noop),
    ]
