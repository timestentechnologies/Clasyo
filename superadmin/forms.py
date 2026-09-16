from django import forms
from .models import (
    PaymentConfiguration, SchoolPaymentConfiguration,
    GlobalAIConfiguration, SchoolAIConfiguration,
    GlobalEmailConfiguration, GlobalSMSConfiguration,
    GlobalDatabaseConfiguration, GlobalWhatsAppConfiguration,
    SchoolWhatsAppConfiguration,
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
            'mpesa_consumer_secret': forms.PasswordInput(attrs={'class': 'form-control'}),
            'mpesa_passkey': forms.PasswordInput(attrs={'class': 'form-control'}),
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
            # Account name and instructions are optional globally but recommended
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
        elif gateway == 'mpesa_buygoods':
            if not cleaned_data.get('mpesa_till_number'):
                raise forms.ValidationError('Till Number is required for M-Pesa Buy Goods & Services')
        elif gateway == 'mpesa_send_money':
            if not cleaned_data.get('mpesa_send_money_recipient'):
                raise forms.ValidationError('Recipient phone number is required for M-Pesa Send Money')
        elif gateway == 'mpesa_pochi':
            if not cleaned_data.get('mpesa_pochi_number'):
                raise forms.ValidationError('Pochi la Biashara number is required for M-Pesa Pochi')
        
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
            'gateway': forms.Select(attrs={'class': 'form-control'}),
            'environment': forms.Select(attrs={'class': 'form-control'}),
            'mpesa_consumer_key': forms.TextInput(attrs={'class': 'form-control'}),
            'mpesa_consumer_secret': forms.PasswordInput(attrs={'class': 'form-control'}),
            'mpesa_passkey': forms.PasswordInput(attrs={'class': 'form-control'}),
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
            if not cleaned_data.get('mpesa_paybill_account_name'):
                raise forms.ValidationError('Account Name is required for M-Pesa Manual Paybill')
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
        elif gateway == 'mpesa_buygoods':
            if not cleaned_data.get('mpesa_till_number'):
                raise forms.ValidationError('Till Number is required for M-Pesa Buy Goods & Services')
        elif gateway == 'mpesa_send_money':
            if not cleaned_data.get('mpesa_send_money_recipient'):
                raise forms.ValidationError('Recipient phone number is required for M-Pesa Send Money')
        elif gateway == 'mpesa_pochi':
            if not cleaned_data.get('mpesa_pochi_number'):
                raise forms.ValidationError('Pochi la Biashara number is required for M-Pesa Pochi')
        elif gateway in ['cash', 'cheque']:
            if not cleaned_data.get('payment_instructions'):
                raise forms.ValidationError('Payment Instructions are required for Cash/Cheque payments')
        
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
            'overlay_opacity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.05', 'min': '0', 'max': '1'}),
            'min_height': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class FloatingParallaxElementForm(forms.ModelForm):
    """Form for Floating Parallax Icons CMS"""
    class Meta:
        from frontend.models import FloatingParallaxElement
        model = FloatingParallaxElement
        fields = [
            'title', 'icon', 'section_target', 'preset_position',
            'position_top', 'position_left', 'position_bottom', 'position_right',
            'font_size', 'opacity', 'animation_type', 'animation_duration',
            'animation_delay', 'order', 'is_active'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Graduation Cap Icon'}),
            'icon': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. fas fa-graduation-cap'}),
            'section_target': forms.Select(attrs={'class': 'form-select'}),
            'preset_position': forms.Select(attrs={'class': 'form-select'}),
            'position_top': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 10% or 50px or auto'}),
            'position_left': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 10% or 40px or auto'}),
            'position_bottom': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 15% or auto'}),
            'position_right': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 15% or auto'}),
            'font_size': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 3rem or 45px'}),
            'opacity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.05', 'min': '0.01', 'max': '1'}),
            'animation_type': forms.Select(attrs={'class': 'form-select'}),
            'animation_duration': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 18s'}),
            'animation_delay': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 0s'}),
            'order': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


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
            'overlay_opacity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.05', 'min': '0', 'max': '1'}),
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
        fields = '__all__'
        widgets = {
            'school': forms.Select(attrs={'class': 'form-select'}),
            'provider': forms.Select(attrs={'class': 'form-select', 'id': 'id_provider'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'use_global_settings': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
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



