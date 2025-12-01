from django import forms
from .models import PaymentConfiguration, SchoolPaymentConfiguration


class PaymentConfigurationForm(forms.ModelForm):
    """Form for creating and editing payment configurations"""
    
    class Meta:
        model = PaymentConfiguration
        fields = [
            'gateway', 'environment', 'is_active',
            'mpesa_consumer_key', 'mpesa_consumer_secret', 'mpesa_passkey', 
            'mpesa_shortcode', 'mpesa_paybill_number',
            'paypal_client_id', 'paypal_client_secret', 'paypal_webhook_id',
            'stripe_publishable_key', 'stripe_secret_key', 'stripe_webhook_secret',
            'bank_name', 'bank_account_name', 'bank_account_number', 
            'bank_branch', 'bank_swift_code'
        ]
        widgets = {
            'mpesa_consumer_key': forms.TextInput(attrs={'class': 'form-control'}),
            'mpesa_consumer_secret': forms.PasswordInput(attrs={'class': 'form-control'}),
            'mpesa_passkey': forms.PasswordInput(attrs={'class': 'form-control'}),
            'mpesa_shortcode': forms.TextInput(attrs={'class': 'form-control'}),
            'mpesa_paybill_number': forms.TextInput(attrs={'class': 'form-control'}),
            'paypal_client_id': forms.TextInput(attrs={'class': 'form-control'}),
            'paypal_client_secret': forms.PasswordInput(attrs={'class': 'form-control'}),
            'paypal_webhook_id': forms.TextInput(attrs={'class': 'form-control'}),
            'stripe_publishable_key': forms.TextInput(attrs={'class': 'form-control'}),
            'stripe_secret_key': forms.PasswordInput(attrs={'class': 'form-control'}),
            'stripe_webhook_secret': forms.PasswordInput(attrs={'class': 'form-control'}),
            'bank_name': forms.TextInput(attrs={'class': 'form-control'}),
            'bank_account_name': forms.TextInput(attrs={'class': 'form-control'}),
            'bank_account_number': forms.TextInput(attrs={'class': 'form-control'}),
            'bank_branch': forms.TextInput(attrs={'class': 'form-control'}),
            'bank_swift_code': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        gateway = cleaned_data.get('gateway')
        
        if gateway == 'mpesa':
            if not cleaned_data.get('mpesa_consumer_key'):
                raise forms.ValidationError('Consumer Key is required for M-Pesa')
            if not cleaned_data.get('mpesa_consumer_secret'):
                raise forms.ValidationError('Consumer Secret is required for M-Pesa')
            if not cleaned_data.get('mpesa_passkey'):
                raise forms.ValidationError('Passkey is required for M-Pesa')
        elif gateway == 'paypal':
            if not cleaned_data.get('paypal_client_id'):
                raise forms.ValidationError('Client ID is required for PayPal')
            if not cleaned_data.get('paypal_client_secret'):
                raise forms.ValidationError('Client Secret is required for PayPal')
        elif gateway == 'stripe':
            if not cleaned_data.get('stripe_publishable_key'):
                self.add_error('stripe_publishable_key', 'Publishable key is required for Stripe')
            if not cleaned_data.get('stripe_secret_key'):
                self.add_error('stripe_secret_key', 'Secret key is required for Stripe')
        elif gateway == 'bank':
            if not cleaned_data.get('bank_name'):
                self.add_error('bank_name', 'Bank name is required for Bank Transfer')
            if not cleaned_data.get('bank_account_name'):
                self.add_error('bank_account_name', 'Account name is required for Bank Transfer')
            if not cleaned_data.get('bank_account_number'):
                self.add_error('bank_account_number', 'Account number is required for Bank Transfer')
        
        return cleaned_data


class SchoolPaymentConfigurationForm(forms.ModelForm):
    """Form for creating and editing school payment configurations"""
    
    class Meta:
        model = SchoolPaymentConfiguration
        fields = [
            'gateway', 'environment', 'is_active',
            'mpesa_consumer_key', 'mpesa_consumer_secret', 'mpesa_passkey', 'mpesa_shortcode',
            'mpesa_paybill_number', 'mpesa_paybill_account_number', 'mpesa_paybill_bank_name',
            'paypal_email',
            'bank_name', 'bank_account_name', 'bank_account_number', 'bank_branch',
            'payment_instructions'
        ]
        widgets = {
            'gateway': forms.Select(attrs={'class': 'form-control'}),
            'environment': forms.Select(attrs={'class': 'form-control'}),
            'mpesa_consumer_key': forms.TextInput(attrs={'class': 'form-control'}),
            'mpesa_consumer_secret': forms.PasswordInput(attrs={'class': 'form-control'}),
            'mpesa_passkey': forms.PasswordInput(attrs={'class': 'form-control'}),
            'mpesa_shortcode': forms.TextInput(attrs={'class': 'form-control'}),
            'mpesa_paybill_number': forms.TextInput(attrs={'class': 'form-control'}),
            'mpesa_paybill_account_number': forms.TextInput(attrs={'class': 'form-control'}),
            'mpesa_paybill_bank_name': forms.TextInput(attrs={'class': 'form-control'}),
            'paypal_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'bank_name': forms.TextInput(attrs={'class': 'form-control'}),
            'bank_account_name': forms.TextInput(attrs={'class': 'form-control'}),
            'bank_account_number': forms.TextInput(attrs={'class': 'form-control'}),
            'bank_branch': forms.TextInput(attrs={'class': 'form-control'}),
            'payment_instructions': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        gateway = cleaned_data.get('gateway')
        
        if gateway == 'mpesa_stk':
            if not cleaned_data.get('mpesa_consumer_key'):
                raise forms.ValidationError('Consumer Key is required for M-Pesa STK Push')
            if not cleaned_data.get('mpesa_consumer_secret'):
                raise forms.ValidationError('Consumer Secret is required for M-Pesa STK Push')
            if not cleaned_data.get('mpesa_passkey'):
                raise forms.ValidationError('Passkey is required for M-Pesa STK Push')
            if not cleaned_data.get('mpesa_shortcode'):
                raise forms.ValidationError('Shortcode is required for M-Pesa STK Push')
        elif gateway == 'mpesa_paybill':
            if not cleaned_data.get('mpesa_paybill_number'):
                raise forms.ValidationError('Paybill Number is required for M-Pesa Manual Paybill')
            if not cleaned_data.get('mpesa_paybill_account_number'):
                raise forms.ValidationError('Account Number is required for M-Pesa Manual Paybill')
            if not cleaned_data.get('mpesa_paybill_bank_name'):
                raise forms.ValidationError('Bank Name is required for M-Pesa Manual Paybill')
        elif gateway == 'paypal':
            if not cleaned_data.get('paypal_email'):
                raise forms.ValidationError('PayPal Email is required for PayPal')
        elif gateway == 'bank':
            if not cleaned_data.get('bank_name'):
                raise forms.ValidationError('Bank Name is required for Bank Transfer')
            if not cleaned_data.get('bank_account_name'):
                raise forms.ValidationError('Account Name is required for Bank Transfer')
            if not cleaned_data.get('bank_account_number'):
                raise forms.ValidationError('Account Number is required for Bank Transfer')
        elif gateway in ['cash', 'cheque']:
            if not cleaned_data.get('payment_instructions'):
                raise forms.ValidationError('Payment Instructions are required for Cash/Cheque payments')
        
        return cleaned_data
