from django.db import migrations

def update_site_domain(apps, schema_editor):
    Site = apps.get_model('sites', 'Site')
    domain = 'clasyo.timestentechnologies.co.ke'
    
    # Update or create the default site
    Site.objects.update_or_create(
        id=1,
        defaults={
            'domain': domain,
            'name': 'Clasyo School Management System'
        }
    )

class Migration(migrations.Migration):
    dependencies = [
        ('frontend', '0001_initial'),
        ('sites', '0002_alter_domain_unique'),
    ]

    operations = [
        migrations.RunPython(update_site_domain),
    ]
