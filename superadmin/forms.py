from django import forms
from .models import (
    PaymentConfiguration, SchoolPaymentConfiguration,
    GlobalAIConfiguration, SchoolAIConfiguration,
    GlobalEmailConfiguration, GlobalSMSConfiguration,
    GlobalDatabaseConfiguration, GlobalWhatsAppConfiguration,
    GlobalGoogleAuthConfiguration,
    SchoolWhatsAppConfiguration, SchoolSMSConfiguration,
    SchoolEmailConfiguration, NotificationTemplate,
)


class PaymentConfigurationForm(forms.ModelForm):
    """Form for creating and editing payment configurations"""
    
    class Meta:
        model = PaymentConfiguration
        fields = [
            'gateway', 'environment', 'is_active',
            'mpesa_consumer_key', 'mpesa_consumer_secret', 'mpesa_passkey', 
            'mpesa_shortcode', 'mpesa_paybill_number', 'mpesa_paybill_account_name', 'mpesa_paybill_instructions',
            'mpesa_till_number', 'mpesa_buygoods_instructions', 'mpesa_send_money_recipient', 'mpesa_send_money_instructions', 'mpesa_pochi_number', 'mpesa_pochi_instructions',
            'paypal_client_id', 'paypal_client_secret', 'paypal_webhook_id',
            'stripe_publishable_key', 'stripe_secret_key', 'stripe_webhook_secret',
            'bank_name', 'bank_account_name', 'bank_account_number', 
            'bank_branch', 'bank_swift_code'
        ]
        widgets = {
            'gateway': forms.Select(attrs={'class': 'form-select'}),
            'environment': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'mpesa_consumer_key': forms.TextInput(attrs={'class': 'form-control'}),
            'mpesa_consumer_secret': forms.PasswordInput(attrs={'class': 'form-control'}, render_value=True),
            'mpesa_passkey': forms.PasswordInput(attrs={'class': 'form-control'}, render_value=True),
            'mpesa_shortcode': forms.TextInput(attrs={'class': 'form-control'}),
            'mpesa_paybill_number': forms.TextInput(attrs={'class': 'form-control'}),
            'mpesa_paybill_account_name': forms.TextInput(attrs={'class': 'form-control'}),
            'mpesa_paybill_instructions': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'mpesa_till_number': forms.TextInput(attrs={'class': 'form-control'}),
            'mpesa_buygoods_instructions': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'mpesa_send_money_recipient': forms.TextInput(attrs={'class': 'form-control'}),
            'mpesa_send_money_instructions': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'mpesa_pochi_number': forms.TextInput(attrs={'class': 'form-control'}),
            'mpesa_pochi_instructions': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'paypal_client_id': forms.TextInput(attrs={'class': 'form-control'}),
            'paypal_client_secret': forms.PasswordInput(attrs={'class': 'form-control'}, render_value=True),
            'paypal_webhook_id': forms.TextInput(attrs={'class': 'form-control'}),
            'stripe_publishable_key': forms.TextInput(attrs={'class': 'form-control'}),
            'stripe_secret_key': forms.PasswordInput(attrs={'class': 'form-control'}, render_value=True),
            'stripe_webhook_secret': forms.PasswordInput(attrs={'class': 'form-control'}, render_value=True),
            'bank_name': forms.TextInput(attrs={'class': 'form-control'}),
            'bank_account_name': forms.TextInput(attrs={'class': 'form-control'}),
            'bank_account_number': forms.TextInput(attrs={'class': 'form-control'}),
            'bank_branch': forms.TextInput(attrs={'class': 'form-control'}),
            'bank_swift_code': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Prefill default instructions for superadmin to guide school admins
        defaults = {
            'mpesa_send_money_instructions': (
                'Go to your M-Pesa\n'
                'Select Send Money\n'
                'Enter the Phone Number\n'
                'Enter the Amount\n'
                'Enter your M-Pesa PIN\n'
                'Confirm the details'
            ),
            'mpesa_pochi_instructions': (
                'Go to your M-Pesa\n'
                'Select Lipa na M-Pesa\n'
                'Choose Pochi la Biashara\n'
                'Enter the Phone Number\n'
                'Enter the Amount\n'
                'Enter your M-Pesa PIN\n'
                'Confirm'
            ),
            'mpesa_buygoods_instructions': (
                'Go to your M-Pesa\n'
                'Select Lipa na M-Pesa\n'
                'Choose Buy Goods and Services\n'
                'Enter the Till Number\n'
                'Enter the Amount\n'
                'Enter your M-Pesa PIN\n'
                'Confirm'
            ),
            'mpesa_paybill_instructions': (
                'Go to your M-Pesa\n'
                'Select Lipa na M-Pesa\n'
                'Choose PayBill\n'
                'Enter the Business Number\n'
                'Enter the Account Number\n'
                'Enter the Amount\n'
                'Enter your M-Pesa PIN\n'
                'Confirm'
            ),
        }
        for field_name, text in defaults.items():
            if field_name in self.fields:
                instance_value = getattr(self.instance, field_name, None)
                if not instance_value:
                    self.fields[field_name].initial = text
    
    def clean(self):
        cleaned_data = super().clean()
        gateway = cleaned_data.get('gateway')
        
        # Preserve existing sensitive fields if updating and left blank
        if self.instance and self.instance.pk:
            if not cleaned_data.get('mpesa_consumer_secret') and self.instance.mpesa_consumer_secret:
                cleaned_data['mpesa_consumer_secret'] = self.instance.mpesa_consumer_secret
            if not cleaned_data.get('mpesa_passkey') and self.instance.mpesa_passkey:
                cleaned_data['mpesa_passkey'] = self.instance.mpesa_passkey
            if not cleaned_data.get('mpesa_consumer_key') and self.instance.mpesa_consumer_key:
                cleaned_data['mpesa_consumer_key'] = self.instance.mpesa_consumer_key
            if not cleaned_data.get('paypal_client_secret') and self.instance.paypal_client_secret:
                cleaned_data['paypal_client_secret'] = self.instance.paypal_client_secret
            if not cleaned_data.get('stripe_secret_key') and self.instance.stripe_secret_key:
                cleaned_data['stripe_secret_key'] = self.instance.stripe_secret_key
            if not cleaned_data.get('stripe_webhook_secret') and self.instance.stripe_webhook_secret:
                cleaned_data['stripe_webhook_secret'] = self.instance.stripe_webhook_secret

        if gateway == 'mpesa_stk':
            if not cleaned_data.get('mpesa_consumer_key'):
                self.add_error('mpesa_consumer_key', 'Consumer Key is required for M-Pesa STK Push')
            if not cleaned_data.get('mpesa_consumer_secret'):
                self.add_error('mpesa_consumer_secret', 'Consumer Secret is required for M-Pesa STK Push')
            if not cleaned_data.get('mpesa_passkey'):
                self.add_error('mpesa_passkey', 'Passkey is required for M-Pesa STK Push')
            if not cleaned_data.get('mpesa_shortcode'):
                self.add_error('mpesa_shortcode', 'Shortcode is required for M-Pesa STK Push')
        elif gateway == 'mpesa_paybill':
            if not cleaned_data.get('mpesa_paybill_number'):
                self.add_error('mpesa_paybill_number', 'Paybill Number is required for M-Pesa Manual Paybill')
        elif gateway == 'paypal':
            if not cleaned_data.get('paypal_client_id'):
                self.add_error('paypal_client_id', 'Client ID is required for PayPal')
            if not cleaned_data.get('paypal_client_secret'):
                self.add_error('paypal_client_secret', 'Client Secret is required for PayPal')
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
        elif gateway == 'mpesa_buygoods':
            if not cleaned_data.get('mpesa_till_number'):
                self.add_error('mpesa_till_number', 'Till Number is required for M-Pesa Buy Goods & Services')
        elif gateway == 'mpesa_send_money':
            if not cleaned_data.get('mpesa_send_money_recipient'):
                self.add_error('mpesa_send_money_recipient', 'Recipient phone number is required for M-Pesa Send Money')
        elif gateway == 'mpesa_pochi':
            if not cleaned_data.get('mpesa_pochi_number'):
                self.add_error('mpesa_pochi_number', 'Pochi la Biashara number is required for M-Pesa Pochi')
        
        return cleaned_data


class SchoolPaymentConfigurationForm(forms.ModelForm):
    """Form for creating and editing school payment configurations"""
    
    class Meta:
        model = SchoolPaymentConfiguration
        fields = [
            'gateway', 'environment', 'is_active',
            'mpesa_consumer_key', 'mpesa_consumer_secret', 'mpesa_passkey', 'mpesa_shortcode',
            'mpesa_paybill_number', 'mpesa_paybill_account_number', 'mpesa_paybill_bank_name', 'mpesa_paybill_account_name', 'mpesa_paybill_instructions',
            'mpesa_till_number', 'mpesa_buygoods_instructions', 'mpesa_send_money_recipient', 'mpesa_send_money_instructions', 'mpesa_pochi_number', 'mpesa_pochi_instructions',
            'paypal_email',
            'bank_name', 'bank_account_name', 'bank_account_number', 'bank_branch',
            'payment_instructions'
        ]
        widgets = {
            'gateway': forms.Select(attrs={'class': 'form-select'}),
            'environment': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'mpesa_consumer_key': forms.TextInput(attrs={'class': 'form-control'}),
            'mpesa_consumer_secret': forms.PasswordInput(attrs={'class': 'form-control'}, render_value=True),
            'mpesa_passkey': forms.PasswordInput(attrs={'class': 'form-control'}, render_value=True),
            'mpesa_shortcode': forms.TextInput(attrs={'class': 'form-control'}),
            'mpesa_paybill_number': forms.TextInput(attrs={'class': 'form-control'}),
            'mpesa_paybill_account_number': forms.TextInput(attrs={'class': 'form-control'}),
            'mpesa_paybill_bank_name': forms.TextInput(attrs={'class': 'form-control'}),
            'mpesa_paybill_account_name': forms.TextInput(attrs={'class': 'form-control'}),
            'mpesa_paybill_instructions': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'mpesa_till_number': forms.TextInput(attrs={'class': 'form-control'}),
            'mpesa_buygoods_instructions': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'mpesa_send_money_recipient': forms.TextInput(attrs={'class': 'form-control'}),
            'mpesa_send_money_instructions': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'mpesa_pochi_number': forms.TextInput(attrs={'class': 'form-control'}),
            'mpesa_pochi_instructions': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'paypal_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'bank_name': forms.TextInput(attrs={'class': 'form-control'}),
            'bank_account_name': forms.TextInput(attrs={'class': 'form-control'}),
            'bank_account_number': forms.TextInput(attrs={'class': 'form-control'}),
            'bank_branch': forms.TextInput(attrs={'class': 'form-control'}),
            'payment_instructions': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs['class'] = 'form-check-input'
            elif isinstance(widget, forms.Select):
                widget.attrs['class'] = 'form-select'
            else:
                current_cls = widget.attrs.get('class', '')
                if 'form-control' not in current_cls:
                    widget.attrs['class'] = (current_cls + ' form-control').strip()
    
    def clean(self):
        cleaned_data = super().clean()
        gateway = cleaned_data.get('gateway')
        
        # Preserve existing sensitive fields if updating and left blank
        if self.instance and self.instance.pk:
            if not cleaned_data.get('mpesa_consumer_secret') and self.instance.mpesa_consumer_secret:
                cleaned_data['mpesa_consumer_secret'] = self.instance.mpesa_consumer_secret
            if not cleaned_data.get('mpesa_passkey') and self.instance.mpesa_passkey:
                cleaned_data['mpesa_passkey'] = self.instance.mpesa_passkey
            if not cleaned_data.get('mpesa_consumer_key') and self.instance.mpesa_consumer_key:
                cleaned_data['mpesa_consumer_key'] = self.instance.mpesa_consumer_key

        if gateway == 'mpesa_stk':
            if not cleaned_data.get('mpesa_consumer_key'):
                self.add_error('mpesa_consumer_key', 'Consumer Key is required for M-Pesa STK Push')
            if not cleaned_data.get('mpesa_consumer_secret'):
                self.add_error('mpesa_consumer_secret', 'Consumer Secret is required for M-Pesa STK Push')
            if not cleaned_data.get('mpesa_passkey'):
                self.add_error('mpesa_passkey', 'Passkey is required for M-Pesa STK Push')
            if not cleaned_data.get('mpesa_shortcode'):
                self.add_error('mpesa_shortcode', 'Shortcode is required for M-Pesa STK Push')
        elif gateway == 'mpesa_paybill':
            if not cleaned_data.get('mpesa_paybill_number'):
                self.add_error('mpesa_paybill_number', 'Paybill Number is required for M-Pesa Manual Paybill')
            if not cleaned_data.get('mpesa_paybill_account_number'):
                self.add_error('mpesa_paybill_account_number', 'Account Number is required for M-Pesa Manual Paybill')
            if not cleaned_data.get('mpesa_paybill_account_name'):
                self.add_error('mpesa_paybill_account_name', 'Account Name is required for M-Pesa Manual Paybill')
        elif gateway == 'paypal':
            if not cleaned_data.get('paypal_email'):
                self.add_error('paypal_email', 'PayPal Email is required for PayPal')
        elif gateway == 'bank':
            if not cleaned_data.get('bank_name'):
                self.add_error('bank_name', 'Bank Name is required for Bank Transfer')
            if not cleaned_data.get('bank_account_name'):
                self.add_error('bank_account_name', 'Account Name is required for Bank Transfer')
            if not cleaned_data.get('bank_account_number'):
                self.add_error('bank_account_number', 'Account Number is required for Bank Transfer')
        elif gateway == 'mpesa_buygoods':
            if not cleaned_data.get('mpesa_till_number'):
                self.add_error('mpesa_till_number', 'Till Number is required for M-Pesa Buy Goods & Services')
        elif gateway == 'mpesa_send_money':
            if not cleaned_data.get('mpesa_send_money_recipient'):
                self.add_error('mpesa_send_money_recipient', 'Recipient phone number is required for M-Pesa Send Money')
        elif gateway == 'mpesa_pochi':
            if not cleaned_data.get('mpesa_pochi_number'):
                self.add_error('mpesa_pochi_number', 'Pochi la Biashara number is required for M-Pesa Pochi')
        elif gateway in ['cash', 'cheque']:
            if not cleaned_data.get('payment_instructions'):
                self.add_error('payment_instructions', 'Payment Instructions are required for Cash/Cheque payments')
        
        return cleaned_data


class HeroContentForm(forms.ModelForm):
    """Form for SuperAdmin Hero Section CMS"""
    class Meta:
        from frontend.models import HeroContent
        model = HeroContent
        fields = [
            'title_prefix', 'typing_texts', 'subtitle',
            'primary_btn_text', 'primary_btn_url',
            'secondary_btn_text', 'secondary_btn_url',
            'bg_type', 'bg_image', 'bg_color', 'bg_gradient',
            'overlay_color', 'overlay_opacity', 'min_height', 'is_active'
        ]
        widgets = {
            'title_prefix': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Transform Your'}),
            'typing_texts': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Enter one phrase per line'}),
            'subtitle': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'primary_btn_text': forms.TextInput(attrs={'class': 'form-control'}),
            'primary_btn_url': forms.TextInput(attrs={'class': 'form-control'}),
            'secondary_btn_text': forms.TextInput(attrs={'class': 'form-control'}),
            'secondary_btn_url': forms.TextInput(attrs={'class': 'form-control'}),
            'bg_type': forms.Select(attrs={'class': 'form-select'}),
            'bg_image': forms.FileInput(attrs={'class': 'form-control'}),
            'bg_color': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'bg_gradient': forms.TextInput(attrs={'class': 'form-control'}),
            'overlay_color': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'overlay_opacity': forms.NumberInput(attrs={
                'type': 'range',
                'class': 'form-range',
                'step': '0.01',
                'min': '0',
                'max': '1',
                'id': 'hero_overlay_opacity',
                'style': 'border: none !important; background: transparent !important; box-shadow: none !important; outline: none !important; padding: 0 !important;',
                'oninput': "var el = document.getElementById('hero_opacity_val'); if (el) el.innerText = parseFloat(this.value).toFixed(2);"
            }),
            'min_height': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        optional_fields = ['bg_type', 'bg_image', 'bg_color', 'bg_gradient', 'overlay_color', 'overlay_opacity', 'primary_btn_url', 'secondary_btn_url', 'subtitle']
        for f in optional_fields:
            if f in self.fields:
                self.fields[f].required = False

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get('bg_type'):
            cleaned_data['bg_type'] = 'gradient'
        if not cleaned_data.get('bg_color'):
            cleaned_data['bg_color'] = '#0f172a'
        if not cleaned_data.get('overlay_color'):
            cleaned_data['overlay_color'] = '#0f172a'
        if cleaned_data.get('overlay_opacity') is None:
            cleaned_data['overlay_opacity'] = 0.85
        return cleaned_data


class ProcessStepForm(forms.ModelForm):
    """Form for How It Works / Process Step CMS"""
    class Meta:
        from frontend.models import ProcessStep
        model = ProcessStep
        fields = [
            'step_number', 'phase_tag', 'title', 'subtitle',
            'description', 'icon', 'accent_color', 'order', 'is_active'
        ]
        widgets = {
            'step_number': forms.NumberInput(attrs={'class': 'form-control'}),
            'phase_tag': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. PHASE 1'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Discovery & Strategy'}),
            'subtitle': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'icon': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. fas fa-school'}),
            'accent_color': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'order': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class FeatureItemForm(forms.ModelForm):
    """Form for Features CMS"""
    class Meta:
        from frontend.models import FeatureItem
        model = FeatureItem
        fields = ['title', 'description', 'icon', 'order', 'is_active']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'icon': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. fas fa-user-graduate'}),
            'order': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class ParallaxSectionForm(forms.ModelForm):
    """Form for Parallax Banner CMS"""
    class Meta:
        from frontend.models import ParallaxSection
        model = ParallaxSection
        fields = [
            'title', 'target_position', 'subtitle', 'content',
            'primary_btn_text', 'primary_btn_url',
            'secondary_btn_text', 'secondary_btn_url',
            'bg_image', 'bg_color', 'overlay_opacity', 'scroll_effect',
            'order', 'is_active'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'target_position': forms.Select(attrs={'class': 'form-select'}),
            'subtitle': forms.TextInput(attrs={'class': 'form-control'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'primary_btn_text': forms.TextInput(attrs={'class': 'form-control'}),
            'primary_btn_url': forms.TextInput(attrs={'class': 'form-control'}),
            'secondary_btn_text': forms.TextInput(attrs={'class': 'form-control'}),
            'secondary_btn_url': forms.TextInput(attrs={'class': 'form-control'}),
            'bg_image': forms.FileInput(attrs={'class': 'form-control'}),
            'bg_color': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'overlay_opacity': forms.NumberInput(attrs={
                'type': 'range',
                'class': 'form-range',
                'step': '0.01',
                'min': '0',
                'max': '1',
                'id': 'parallax_overlay_opacity',
                'style': 'border: none !important; background: transparent !important; box-shadow: none !important; outline: none !important; padding: 0 !important;',
                'oninput': "var el = document.getElementById('p_edit_opacity_val'); if (el) el.innerText = parseFloat(this.value).toFixed(2);"
            }),
            'scroll_effect': forms.Select(attrs={'class': 'form-select'}),
            'order': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class GlobalEmailConfigurationForm(forms.ModelForm):
    """Form for creating and editing Global Email Configuration"""
    class Meta:
        model = GlobalEmailConfiguration
        fields = '__all__'
        widgets = {
            'provider': forms.Select(attrs={'class': 'form-select', 'id': 'id_provider'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'smtp_host': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., smtp.gmail.com'}),
            'smtp_port': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '587'}),
            'smtp_username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'user@domain.com'}),
            'smtp_password': forms.PasswordInput(render_value=True, attrs={'class': 'form-control', 'placeholder': '••••••••'}),
            'smtp_use_tls': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'smtp_use_ssl': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'sendgrid_api_key': forms.PasswordInput(render_value=True, attrs={'class': 'form-control', 'placeholder': 'SG.xxxxxxxx'}),
            'sendgrid_sender_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'noreply@yourdomain.com'}),
            'sendgrid_sender_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'School Notifications'}),
            'mailgun_api_key': forms.PasswordInput(render_value=True, attrs={'class': 'form-control', 'placeholder': 'key-xxxxxxxx'}),
            'mailgun_domain': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'mg.yourdomain.com'}),
            'mailgun_sender_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'noreply@yourdomain.com'}),
            'ses_access_key': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'AKIAxxxxxxxx'}),
            'ses_secret_key': forms.PasswordInput(render_value=True, attrs={'class': 'form-control', 'placeholder': '••••••••'}),
            'ses_region': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'us-east-1'}),
            'ses_sender_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'noreply@yourdomain.com'}),
            'postmark_api_key': forms.PasswordInput(render_value=True, attrs={'class': 'form-control', 'placeholder': 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'}),
            'postmark_sender_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'noreply@yourdomain.com'}),
            'postmark_sender_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'School Notifications'}),
            'default_from_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'noreply@yourdomain.com'}),
            'default_from_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Clasyo Notifications'}),
        }


class GlobalSMSConfigurationForm(forms.ModelForm):
    """Form for creating and editing Global SMS Configuration"""
    class Meta:
        model = GlobalSMSConfiguration
        fields = '__all__'
        widgets = {
            'provider': forms.Select(attrs={'class': 'form-select', 'id': 'id_provider'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'default_sender_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. SCHOOL or 8-11 alphanumeric'}),
            'mobilesasa_api_token': forms.PasswordInput(render_value=True, attrs={'class': 'form-control', 'placeholder': 'mbs_xxxxxxxx'}),
            'mobilesasa_sender_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. MOBILESASA or Approved Sender ID'}),
            'twilio_account_sid': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ACxxxxxxxx'}),
            'twilio_auth_token': forms.PasswordInput(render_value=True, attrs={'class': 'form-control', 'placeholder': '••••••••'}),
            'twilio_phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+1234567890'}),
            'africastalking_username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'sandbox or your_username'}),
            'africastalking_api_key': forms.PasswordInput(render_value=True, attrs={'class': 'form-control', 'placeholder': '••••••••'}),
            'africastalking_sender_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional Alphanumeric Sender ID'}),
            'infobip_api_key': forms.PasswordInput(render_value=True, attrs={'class': 'form-control', 'placeholder': '••••••••'}),
            'infobip_base_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://xxxxxx.api.infobip.com'}),
            'infobip_sender': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Sender ID or Number'}),
            'clickatell_api_key': forms.PasswordInput(render_value=True, attrs={'class': 'form-control', 'placeholder': '••••••••'}),
            'nexmo_api_key': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'API Key'}),
            'nexmo_api_secret': forms.PasswordInput(render_value=True, attrs={'class': 'form-control', 'placeholder': '••••••••'}),
            'nexmo_from_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'From Name or Number'}),
        }


class GlobalDatabaseConfigurationForm(forms.ModelForm):
    """Form for creating and editing Global Database Configuration"""
    class Meta:
        model = GlobalDatabaseConfiguration
        fields = '__all__'
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Primary Read Replica or External School DB'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'db_host': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'localhost or db.example.com'}),
            'db_port': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '5432'}),
            'db_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'school_saas_db'}),
            'db_user': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'postgres'}),
            'db_password': forms.PasswordInput(render_value=True, attrs={'class': 'form-control', 'placeholder': '••••••••'}),
            'backup_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'backup_frequency': forms.Select(attrs={'class': 'form-select'}),
            'backup_retention_days': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '30'}),
            'backup_storage_path': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '/backups/databases'}),
            'max_connections': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '100'}),
            'connection_timeout': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '30'}),
        }


class GlobalWhatsAppConfigurationForm(forms.ModelForm):
    """Form for creating and editing Global WhatsApp Configuration"""
    class Meta:
        model = GlobalWhatsAppConfiguration
        fields = '__all__'
        widgets = {
            'provider': forms.Select(attrs={'class': 'form-select', 'id': 'id_provider'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'default_sender_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+254700000000'}),
            'mobilesasa_api_token': forms.PasswordInput(render_value=True, attrs={'class': 'form-control', 'placeholder': 'mbs_xxxxxxxx'}),
            'mobilesasa_account_uuid': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 98a7b6c5-d4e3-21f0-ba98-76543210fedc'}),
            'mobilesasa_sender_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+254700000000'}),
            'meta_phone_number_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 104857291048572'}),
            'meta_waba_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 294857291048572'}),
            'meta_access_token': forms.PasswordInput(render_value=True, attrs={'class': 'form-control', 'placeholder': 'EAAxxxxx Permanent System User Token'}),
            'meta_app_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Meta App ID'}),
            'meta_app_secret': forms.PasswordInput(render_value=True, attrs={'class': 'form-control', 'placeholder': 'Meta App Secret'}),
            'meta_webhook_verify_token': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Custom verify token'}),
            'twilio_account_sid': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ACxxxxxxxx'}),
            'twilio_auth_token': forms.PasswordInput(render_value=True, attrs={'class': 'form-control', 'placeholder': '••••••••'}),
            'twilio_from_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'whatsapp:+14155238886'}),
            'africastalking_username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'sandbox or your_username'}),
            'africastalking_api_key': forms.PasswordInput(render_value=True, attrs={'class': 'form-control', 'placeholder': '••••••••'}),
            'africastalking_sender_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+254700000000'}),
            'infobip_api_key': forms.PasswordInput(render_value=True, attrs={'class': 'form-control', 'placeholder': '••••••••'}),
            'infobip_base_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://xxxxxx.api.infobip.com'}),
            'infobip_sender_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Infobip WhatsApp Number'}),
        }


class SchoolWhatsAppConfigurationForm(forms.ModelForm):
    """Form for creating and editing School-specific WhatsApp Configuration"""
    class Meta:
        model = SchoolWhatsAppConfiguration
        exclude = ['use_global_settings']
        widgets = {
            'school': forms.Select(attrs={'class': 'form-select'}),
            'provider': forms.Select(attrs={'class': 'form-select', 'id': 'id_provider'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'custom_sender_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+254700000000'}),
            'daily_whatsapp_limit': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0 for unlimited'}),
            'monthly_whatsapp_limit': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0 for unlimited'}),
            'mobilesasa_api_token': forms.PasswordInput(render_value=True, attrs={'class': 'form-control', 'placeholder': 'mbs_xxxxxxxx'}),
            'mobilesasa_account_uuid': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 98a7b6c5-d4e3-21f0-ba98-76543210fedc'}),
            'mobilesasa_sender_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+254700000000'}),
            'meta_phone_number_id': forms.TextInput(attrs={'class': 'form-control'}),
            'meta_waba_id': forms.TextInput(attrs={'class': 'form-control'}),
            'meta_access_token': forms.PasswordInput(render_value=True, attrs={'class': 'form-control'}),
            'meta_app_id': forms.TextInput(attrs={'class': 'form-control'}),
            'meta_app_secret': forms.PasswordInput(render_value=True, attrs={'class': 'form-control'}),
            'meta_webhook_verify_token': forms.TextInput(attrs={'class': 'form-control'}),
            'twilio_account_sid': forms.TextInput(attrs={'class': 'form-control'}),
            'twilio_auth_token': forms.PasswordInput(render_value=True, attrs={'class': 'form-control'}),
            'twilio_from_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'whatsapp:+14155238886'}),
            'africastalking_username': forms.TextInput(attrs={'class': 'form-control'}),
            'africastalking_api_key': forms.PasswordInput(render_value=True, attrs={'class': 'form-control'}),
            'africastalking_sender_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'infobip_api_key': forms.PasswordInput(render_value=True, attrs={'class': 'form-control'}),
            'infobip_base_url': forms.URLInput(attrs={'class': 'form-control'}),
            'infobip_sender_phone': forms.TextInput(attrs={'class': 'form-control'}),
        }


class SchoolSMSConfigurationForm(forms.ModelForm):
    """Form for creating and editing School-specific SMS configuration"""
    class Meta:
        model = SchoolSMSConfiguration
        exclude = ['school', 'use_global_settings']
        widgets = {
            'provider': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'custom_sender_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. SCHOOLSMS'}),
            'default_sender_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. SCHOOLNAME'}),
            'daily_sms_limit': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0 for unlimited'}),
            'monthly_sms_limit': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0 for unlimited'}),
            'mobilesasa_api_token': forms.PasswordInput(render_value=True, attrs={'class': 'form-control', 'placeholder': 'mbs_...'}),
            'mobilesasa_sender_id': forms.TextInput(attrs={'class': 'form-control'}),
            'twilio_account_sid': forms.TextInput(attrs={'class': 'form-control'}),
            'twilio_auth_token': forms.PasswordInput(render_value=True, attrs={'class': 'form-control'}),
            'twilio_phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+1234567890'}),
            'africastalking_username': forms.TextInput(attrs={'class': 'form-control'}),
            'africastalking_api_key': forms.PasswordInput(render_value=True, attrs={'class': 'form-control'}),
            'africastalking_sender_id': forms.TextInput(attrs={'class': 'form-control'}),
            'infobip_api_key': forms.PasswordInput(render_value=True, attrs={'class': 'form-control'}),
            'infobip_base_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://api.infobip.com'}),
            'infobip_sender': forms.TextInput(attrs={'class': 'form-control'}),
            'clickatell_api_key': forms.PasswordInput(render_value=True, attrs={'class': 'form-control'}),
            'clickatell_base_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://platform.clickatell.com'}),
            'nexmo_api_key': forms.TextInput(attrs={'class': 'form-control'}),
            'nexmo_api_secret': forms.PasswordInput(render_value=True, attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs['class'] = 'form-check-input'
            elif isinstance(widget, forms.Select):
                widget.attrs['class'] = 'form-select'
            else:
                current_cls = widget.attrs.get('class', '')
                if 'form-control' not in current_cls:
                    widget.attrs['class'] = (current_cls + ' form-control').strip()


class SchoolEmailConfigurationForm(forms.ModelForm):
    """Form for creating and editing School-specific Email configuration"""
    class Meta:
        model = SchoolEmailConfiguration
        exclude = ['school', 'use_global_settings']
        widgets = {
            'provider': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'from_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'noreply@school.com'}),
            'from_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'School Name'}),
            'daily_limit': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0 for unlimited'}),
            'monthly_limit': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0 for unlimited'}),
            'smtp_host': forms.TextInput(attrs={'class': 'form-control'}),
            'smtp_port': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '587'}),
            'smtp_username': forms.TextInput(attrs={'class': 'form-control'}),
            'smtp_password': forms.PasswordInput(render_value=True, attrs={'class': 'form-control'}),
            'smtp_use_tls': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'smtp_use_ssl': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'sendgrid_api_key': forms.PasswordInput(render_value=True, attrs={'class': 'form-control'}),
            'mailgun_api_key': forms.PasswordInput(render_value=True, attrs={'class': 'form-control'}),
            'mailgun_domain': forms.TextInput(attrs={'class': 'form-control'}),
            'ses_access_key_id': forms.TextInput(attrs={'class': 'form-control'}),
            'ses_secret_access_key': forms.PasswordInput(render_value=True, attrs={'class': 'form-control'}),
            'ses_region_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'us-east-1'}),
            'postmark_server_token': forms.PasswordInput(render_value=True, attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs['class'] = 'form-check-input'
            elif isinstance(widget, forms.Select):
                widget.attrs['class'] = 'form-select'
            else:
                current_cls = widget.attrs.get('class', '')
                if 'form-control' not in current_cls:
                    widget.attrs['class'] = (current_cls + ' form-control').strip()


class GlobalGoogleAuthConfigurationForm(forms.ModelForm):
    """Form for setting up Google OAuth credentials and enabling Google Sign-In"""
    class Meta:
        model = GlobalGoogleAuthConfiguration
        fields = ['client_id', 'client_secret', 'is_active']
        widgets = {
            'client_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., 1234567890-abcdefghijklmnop.apps.googleusercontent.com',
                'autocomplete': 'off',
            }),
            'client_secret': forms.PasswordInput(render_value=True, attrs={
                'class': 'form-control',
                'placeholder': 'e.g., GOCSPX-xxxxxxxxxxxxxxxxxxxxxxxx',
                'autocomplete': 'off',
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class TestEmailDeliveryForm(forms.Form):
    """Form to test outgoing email delivery"""
    recipient_email = forms.EmailField(
        label='Recipient Email Address',
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., admin@example.com'
        })
    )


class NotificationTemplateForm(forms.ModelForm):
    """Form for creating and editing Global & School Notification Templates"""
    class Meta:
        model = NotificationTemplate
        fields = [
            'name', 'code', 'channel', 'category',
            'subject', 'heading', 'body', 'hero_image',
            'button_text', 'button_url', 'available_tags',
            'is_active',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Fee Balance Reminder'}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., fee_reminder'}),
            'channel': forms.Select(attrs={'class': 'form-select', 'id': 'id_channel'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'subject': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Fee Payment Reminder - {{ student_name }}'}),
            'heading': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., School Fee Payment Reminder'}),
            'body': forms.Textarea(attrs={'class': 'form-control font-monospace', 'rows': 7, 'placeholder': 'Write message content with dynamic {{ tags }}...'}),
            'hero_image': forms.FileInput(attrs={'class': 'form-control'}),
            'button_text': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., PAY NOW or READ MORE HERE'}),
            'button_url': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., {{ payment_url }} or https://...'}),
            'available_tags': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'comma-separated, e.g. student_name, balance, due_date'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class TestNotificationSendForm(forms.Form):
    """Form to send a live test notification for any template"""
    recipient = forms.CharField(
        label='Recipient (Email or Phone Number)',
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'admin@example.com or +254700000000'
        })
    )
    sample_context = forms.CharField(
        label='Sample Data (JSON)',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control font-monospace',
            'rows': 4,
            'placeholder': '{\n  "student_name": "John Doe",\n  "parent_name": "Jane Doe",\n  "balance": "15,000",\n  "due_date": "15th Oct 2026"\n}'
        })
    )

