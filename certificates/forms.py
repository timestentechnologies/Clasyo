from django import forms
from django.utils.translation import gettext_lazy as _
from .models import CertificateType, Certificate, IDCard, IDCardTemplate
from students.models import Student
from academics.models import Class
from core.models import AcademicYear
from django.utils import timezone


class CertificateTypeForm(forms.ModelForm):
    """Form for Certificate Types"""
    class Meta:
        model = CertificateType
        fields = ['name', 'code', 'category', 'description', 'template_html', 'background_image',
                 'include_qr_code', 'enable_verification', 'default_width_mm', 'default_height_mm']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'template_html': forms.Textarea(attrs={'rows': 10, 'class': 'html-editor'}),
        }


class CertificateForm(forms.ModelForm):
    """Form for Certificates"""
    def __init__(self, *args, **kwargs):
        self.school = kwargs.pop('school', None)
        super().__init__(*args, **kwargs)
        
        # Filter certificate types by school
        if self.school:
            self.fields['certificate_type'].queryset = CertificateType.objects.filter(
                school=self.school, 
                is_active=True
            )
            self.fields['certificate_type'].widget.attrs.update({'class': 'select2'})
    
    student = forms.ModelChoiceField(
        queryset=Student.objects.filter(is_active=True),
        label=_('Student'),
        widget=forms.Select(attrs={'class': 'select2'})
    )
    
    class_name = forms.ModelChoiceField(
        queryset=Class.objects.filter(is_active=True),
        label=_('Class'),
        required=False,
        widget=forms.Select(attrs={'class': 'select2'})
    )
    
    academic_year = forms.ModelChoiceField(
        queryset=AcademicYear.objects.all(),
        label=_('Academic Year'),
        required=False,
        widget=forms.Select(attrs={'class': 'select2'})
    )
    
    issue_date = forms.DateField(
        label=_('Issue Date'),
        initial=timezone.now().date(),
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    
    expiry_date = forms.DateField(
        label=_('Expiry Date'),
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    
    class Meta:
        model = Certificate
        fields = ['certificate_type', 'student', 'title', 'issue_date', 'expiry_date',
                 'academic_year', 'class_name', 'description', 'remarks']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'remarks': forms.Textarea(attrs={'rows': 2}),
        }


class CertificateVerifyForm(forms.Form):
    """Form for Certificate Verification"""
    verification_code = forms.CharField(
        label=_('Verification Code'),
        max_length=50,
        widget=forms.TextInput(attrs={'placeholder': _('Enter verification code')})
    )


class IDCardTemplateForm(forms.ModelForm):
    """Form for ID Card Templates"""
    class Meta:
        model = IDCardTemplate
        fields = ['name', 'description', 'front_background', 'back_background',
                 'width_mm', 'height_mm', 'school_logo_position', 'photo_position',
                 'signature_position', 'primary_color', 'secondary_color', 'is_default']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'primary_color': forms.TextInput(attrs={'type': 'color'}),
            'secondary_color': forms.TextInput(attrs={'type': 'color'}),
        }


class IDCardForm(forms.ModelForm):
    """Form for Student ID Cards"""
    student = forms.ModelChoiceField(
        queryset=Student.objects.filter(is_active=True),
        label=_('Student'),
        widget=forms.Select(attrs={'class': 'select2'})
    )
    
    card_template = forms.ModelChoiceField(
        queryset=IDCardTemplate.objects.filter(is_active=True),
        label=_('Card Template'),
        widget=forms.Select(attrs={'class': 'select2'})
    )
    
    issue_date = forms.DateField(
        label=_('Issue Date'),
        initial=timezone.now().date(),
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    
    valid_from = forms.DateField(
        label=_('Valid From'),
        initial=timezone.now().date(),
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    
    valid_until = forms.DateField(
        label=_('Valid Until'),
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    
    class Meta:
        model = IDCard
        fields = ['student', 'card_template', 'issue_date', 'valid_from', 'valid_until']


class BulkIDCardForm(forms.Form):
    """Form for Bulk ID Card Generation"""
    students = forms.ModelMultipleChoiceField(
        queryset=Student.objects.filter(is_active=True),
        label=_('Students'),
        widget=forms.SelectMultiple(attrs={'class': 'select2'})
    )
    
    class_name = forms.ModelChoiceField(
        queryset=Class.objects.filter(is_active=True),
        label=_('Class'),
        required=False,
        widget=forms.Select(attrs={'class': 'select2'}),
        help_text=_('If selected, all students from this class will be included')
    )
    
    card_template = forms.ModelChoiceField(
        queryset=IDCardTemplate.objects.filter(is_active=True),
        label=_('Card Template'),
        widget=forms.Select(attrs={'class': 'select2'})
    )
    
    academic_year = forms.ModelChoiceField(
        queryset=AcademicYear.objects.all(),
        label=_('Academic Year'),
        widget=forms.Select(attrs={'class': 'select2'})
    )
    
    issue_date = forms.DateField(
        label=_('Issue Date'),
        initial=timezone.now().date(),
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    
    valid_from = forms.DateField(
        label=_('Valid From'),
        initial=timezone.now().date(),
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    
    valid_until = forms.DateField(
        label=_('Valid Until'),
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    
    def clean(self):
        cleaned_data = super().clean()
        students = cleaned_data.get('students')
        class_name = cleaned_data.get('class_name')
        
        # If neither students nor class is selected, raise an error
        if not students and not class_name:
            raise forms.ValidationError(_('Please select either specific students or a class'))
            
        return cleaned_data
