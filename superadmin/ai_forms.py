from django import forms
from .models import GlobalAIConfiguration, SchoolAIConfiguration


class GlobalAIConfigurationForm(forms.ModelForm):
    """Form for global AI configuration management"""

    class Meta:
        model = GlobalAIConfiguration
        exclude = ['created_at', 'updated_at']
        widgets = {
            'openai_api_key': forms.PasswordInput(render_value=True, attrs={'class': 'form-control'}),
            'azure_openai_api_key': forms.PasswordInput(render_value=True, attrs={'class': 'form-control'}),
            'anthropic_api_key': forms.PasswordInput(render_value=True, attrs={'class': 'form-control'}),
            'local_model_path': forms.TextInput(attrs={'class': 'form-control'}),
        }


class SchoolAIConfigurationForm(forms.ModelForm):
    """Form for school AI configuration management"""

    class Meta:
        model = SchoolAIConfiguration
        exclude = ['school', 'created_at', 'updated_at']
        widgets = {
            'openai_api_key': forms.PasswordInput(render_value=True, attrs={'class': 'form-control'}),
            'azure_openai_api_key': forms.PasswordInput(render_value=True, attrs={'class': 'form-control'}),
            'anthropic_api_key': forms.PasswordInput(render_value=True, attrs={'class': 'form-control'}),
            'local_model_path': forms.TextInput(attrs={'class': 'form-control'}),
        }
