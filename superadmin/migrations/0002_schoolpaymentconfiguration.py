# Generated migration for SchoolPaymentConfiguration model

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tenants', '0001_initial'),
        ('superadmin', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='SchoolPaymentConfiguration',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('gateway', models.CharField(choices=[('mpesa', 'M-Pesa'), ('paypal', 'PayPal'), ('stripe', 'Stripe'), ('bank', 'Bank Transfer'), ('cash', 'Cash'), ('cheque', 'Cheque')], max_length=50, verbose_name='Payment Gateway')),
                ('environment', models.CharField(choices=[('sandbox', 'Sandbox'), ('live', 'Live')], default='sandbox', max_length=10, verbose_name='Environment')),
                ('is_active', models.BooleanField(default=True, verbose_name='Is Active')),
                ('mpesa_shortcode', models.CharField(blank=True, help_text='Your M-Pesa business shortcode', max_length=10, null=True, verbose_name='M-Pesa Shortcode')),
                ('mpesa_paybill_number', models.CharField(blank=True, help_text='Your M-Pesa paybill number', max_length=10, null=True, verbose_name='M-Pesa Paybill Number')),
                ('paypal_email', models.EmailField(blank=True, help_text='Your PayPal business email', null=True, verbose_name='PayPal Email')),
                ('bank_name', models.CharField(blank=True, max_length=255, null=True, verbose_name='Bank Name')),
                ('bank_account_name', models.CharField(blank=True, max_length=255, null=True, verbose_name='Account Name')),
                ('bank_account_number', models.CharField(blank=True, max_length=50, null=True, verbose_name='Account Number')),
                ('bank_branch', models.CharField(blank=True, max_length=255, null=True, verbose_name='Bank Branch')),
                ('payment_instructions', models.TextField(blank=True, help_text='Instructions for parents on how to make payments', null=True, verbose_name='Payment Instructions')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated At')),
                ('school', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payment_configurations', to='tenants.school', verbose_name='School')),
            ],
            options={
                'verbose_name': 'School Payment Configuration',
                'verbose_name_plural': 'School Payment Configurations',
            },
        ),
        migrations.AlterUniqueTogether(
            name='schoolpaymentconfiguration',
            unique_together={('school', 'gateway')},
        ),
    ]
