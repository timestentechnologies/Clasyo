# Generated migration for additional M-Pesa fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('superadmin', '0002_schoolpaymentconfiguration'),
    ]

    operations = [
        migrations.AddField(
            model_name='schoolpaymentconfiguration',
            name='mpesa_paybill_account_number',
            field=models.CharField(blank=True, help_text='Account number for M-Pesa paybill payments', max_length=20, null=True, verbose_name='M-Pesa Paybill Account Number'),
        ),
        migrations.AddField(
            model_name='schoolpaymentconfiguration',
            name='mpesa_paybill_bank_name',
            field=models.CharField(blank=True, help_text='Bank name associated with M-Pesa paybill', max_length=255, null=True, verbose_name='M-Pesa Paybill Bank Name'),
        ),
    ]
