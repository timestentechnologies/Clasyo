from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0001_initial'),
        ('tenants', '0002_school_institution_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='itemcategory',
            name='school',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='item_categories', to='tenants.school'),
        ),
        migrations.AddField(
            model_name='item',
            name='school',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='items', to='tenants.school'),
        ),
        migrations.AddField(
            model_name='supplier',
            name='school',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='suppliers', to='tenants.school'),
        ),
        migrations.AddField(
            model_name='purchaseorder',
            name='school',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='purchase_orders', to='tenants.school'),
        ),
        migrations.AddField(
            model_name='itemdistribution',
            name='school',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='item_distributions', to='tenants.school'),
        ),
        migrations.AddField(
            model_name='expense',
            name='school',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='expenses', to='tenants.school'),
        ),
        migrations.AddField(
            model_name='staffpayment',
            name='school',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='staff_payments', to='tenants.school'),
        ),
    ]
