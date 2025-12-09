from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Club, ClubMembership, ClubActivity, ClubAchievement, ClubResource

class ClubForm(forms.ModelForm):
    """Form for creating and editing clubs"""
    
    class Meta:
        model = Club
        fields = [
            'name', 'description', 'club_type', 'teacher_advisor', 
            'student_president', 'student_secretary', 'meeting_day', 
            'meeting_time', 'meeting_venue', 'max_members', 
            'membership_fee', 'requires_application', 'application_deadline'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'meeting_time': forms.TimeInput(attrs={'type': 'time'}),
            'application_deadline': forms.DateInput(attrs={'type': 'date'}),
            'membership_fee': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.school = kwargs.pop('school', None)
        super().__init__(*args, **kwargs)
        
        if self.school:
            # Filter users by school for advisor and student leadership
            self.fields['teacher_advisor'].queryset = self.fields['teacher_advisor'].queryset.filter(
                role='teacher'
            )
            self.fields['student_president'].queryset = self.fields['student_president'].queryset.filter(
                role='student'
            )
            self.fields['student_secretary'].queryset = self.fields['student_secretary'].queryset.filter(
                role='student'
            )
    
    def clean_application_deadline(self):
        deadline = self.cleaned_data.get('application_deadline')
        if deadline and deadline < timezone.now().date():
            raise ValidationError("Application deadline cannot be in the past.")
        return deadline
    
    def clean_max_members(self):
        max_members = self.cleaned_data.get('max_members')
        if max_members and max_members < 1:
            raise ValidationError("Maximum members must be at least 1.")
        return max_members
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.school:
            instance.school = self.school
        if commit:
            instance.save()
        return instance

class ClubMembershipForm(forms.ModelForm):
    """Form for students to apply for club membership"""
    
    class Meta:
        model = ClubMembership
        fields = ['application_reason', 'parent_consent']
        widgets = {
            'application_reason': forms.Textarea(attrs={'rows': 4, 'placeholder': 
                'Tell us why you want to join this club and what you hope to contribute...'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['application_reason'].required = True
        self.fields['parent_consent'].label = 'I have obtained parent/guardian consent to join this club'

class ClubActivityForm(forms.ModelForm):
    """Form for creating and editing club activities"""
    
    class Meta:
        model = ClubActivity
        fields = [
            'title', 'description', 'activity_type', 'date', 
            'duration', 'venue', 'max_participants', 'is_mandatory', 'points_awarded'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'points_awarded': forms.NumberInput(attrs={'min': '0'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['date'].required = True
        self.fields['duration'].required = True
        self.fields['venue'].required = True
    
    def clean_date(self):
        activity_date = self.cleaned_data.get('date')
        if activity_date and activity_date < timezone.now():
            raise ValidationError("Activity date cannot be in the past.")
        return activity_date
    
    def clean_max_participants(self):
        max_participants = self.cleaned_data.get('max_participants')
        if max_participants and max_participants < 1:
            raise ValidationError("Maximum participants must be at least 1.")
        return max_participants

class ClubAchievementForm(forms.ModelForm):
    """Form for recording club achievements"""
    
    class Meta:
        model = ClubAchievement
        fields = [
            'title', 'description', 'achievement_type', 'date_achieved', 
            'level', 'participants', 'certificate', 'photos'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'date_achieved': forms.DateInput(attrs={'type': 'date'}),
            'participants': forms.CheckboxSelectMultiple(),
        }
    
    def __init__(self, *args, **kwargs):
        club = kwargs.pop('club', None)
        super().__init__(*args, **kwargs)
        
        if club:
            # Filter participants to club members
            self.fields['participants'].queryset = self.fields['participants'].queryset.filter(
                club_memberships__club=club,
                club_memberships__status='active'
            ).distinct()
    
    def clean_date_achieved(self):
        date_achieved = self.cleaned_data.get('date_achieved')
        if date_achieved and date_achieved > timezone.now().date():
            raise ValidationError("Achievement date cannot be in the future.")
        return date_achieved

class ClubResourceForm(forms.ModelForm):
    """Form for uploading club resources"""
    
    class Meta:
        model = ClubResource
        fields = ['title', 'description', 'resource_type', 'file', 'url', 'is_public']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        file = cleaned_data.get('file')
        url = cleaned_data.get('url')
        
        if not file and not url:
            raise ValidationError("Please provide either a file or a URL.")
        
        if file and url:
            raise ValidationError("Please provide either a file or a URL, not both.")
        
        return cleaned_data

class ClubSearchForm(forms.Form):
    """Form for searching clubs"""
    search = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Search clubs...'})
    )
    club_type = forms.ChoiceField(
        choices=[('', 'All Types')] + Club.CLUB_TYPES,
        required=False
    )

class ActivitySearchForm(forms.Form):
    """Form for searching club activities"""
    search = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Search activities...'})
    )
    activity_type = forms.ChoiceField(
        choices=[('', 'All Types')] + ClubActivity.ACTIVITY_TYPES,
        required=False
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'})
    )

class AttendanceForm(forms.Form):
    """Form for marking club activity attendance"""
    
    def __init__(self, *args, **kwargs):
        activity = kwargs.pop('activity')
        super().__init__(*args, **kwargs)
        
        # Add attendance fields for each club member
        members = activity.club.memberships.filter(status='active').select_related('student')
        
        for membership in members:
            field_name = f'attendance_{membership.student.id}'
            self.fields[field_name] = forms.ChoiceField(
                choices=ClubAttendance.ATTENDANCE_STATUS,
                initial='present',
                widget=forms.RadioSelect,
                label=membership.student.get_full_name()
            )

class ClubMembershipBulkActionForm(forms.Form):
    """Form for bulk actions on club memberships"""
    
    ACTION_CHOICES = [
        ('', 'Select Action'),
        ('approve', 'Approve Selected'),
        ('reject', 'Reject Selected'),
        ('inactive', 'Mark Inactive'),
    ]
    
    action = forms.ChoiceField(choices=ACTION_CHOICES, required=False)
    selected_memberships = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple,
        required=False
    )
    
    def __init__(self, *args, **kwargs):
        memberships = kwargs.pop('memberships', [])
        super().__init__(*args, **kwargs)
        
        self.fields['selected_memberships'].choices = [
            (m.id, f'{m.student.get_full_name()} ({m.get_status_display()})') 
            for m in memberships
        ]
