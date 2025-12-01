# Generated migration for M-Pesa STK Push fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('superadmin', '0003_add_mpessa_paybill_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='schoolpaymentconfiguration',
            name='mpesa_consumer_key',
            field=models.CharField(blank=True, help_text='Your M-Pesa API consumer key for STK Push', max_length=255, null=True, verbose_name='M-Pesa Consumer Key'),
        ),
        migrations.AddField(
            model_name='schoolpaymentconfiguration',
            name='mpesa_consumer_secret',
            field=models.CharField(blank=True, help_text='Your M-Pesa API consumer secret for STK Push', max_length=255, null=True, verbose_name='M-Pesa Consumer Secret'),
        ),
        migrations.AddField(
            model_name='schoolpaymentconfiguration',
            name='mpesa_passkey',
            field=models.CharField(blank=True, help_text='Your M-Pesa API passkey for STK Push', max_length=255, null=True, verbose_name='M-Pesa Passkey'),
        ),
        migrations.AlterField(
            model_name='schoolpaymentconfiguration',
            name='gateway',
            field=models.CharField(choices=[('mpesa_stk', 'M-Pesa STK Push'), ('mpesa_paybill', 'M-Pesa Manual Paybill'), ('paypal', 'PayPal'), ('stripe', 'Stripe'), ('bank', 'Bank Transfer'), ('cash', 'Cash'), ('cheque', 'Cheque')], max_length=50, verbose_name='Payment Gateway'),
        ),
    ]
