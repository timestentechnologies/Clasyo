from django import forms
from django.utils.translation import gettext_lazy as _
from .models import ChatGroup, ChatGroupMember, ChatMessage, ChatGroupInvitation
from django.contrib.auth import get_user_model
from academics.models import Class, Section
from core.models import CalendarEvent

User = get_user_model()


class ChatGroupForm(forms.ModelForm):
    """Form for creating and updating chat groups"""
    class Meta:
        model = ChatGroup
        fields = ['name', 'description', 'group_type', 'class_ref', 'section_ref', 
                 'event_ref', 'is_public', 'allow_join', 'auto_add_members', 'avatar']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make reference fields optional
        self.fields['class_ref'].required = False
        self.fields['section_ref'].required = False
        self.fields['event_ref'].required = False
        
        # Dynamic field visibility based on group_type
        self.fields['group_type'].widget.attrs.update({'class': 'group-type-selector'})
        
    def clean(self):
        cleaned_data = super().clean()
        group_type = cleaned_data.get('group_type')
        
        # Validate required fields based on group_type
        if group_type == 'class' and not cleaned_data.get('class_ref'):
            self.add_error('class_ref', _('Class is required for class group type'))
        
        if group_type == 'event' and not cleaned_data.get('event_ref'):
            self.add_error('event_ref', _('Event is required for event group type'))
        
        return cleaned_data


class ChatMessageForm(forms.ModelForm):
    """Form for sending chat messages"""
    class Meta:
        model = ChatMessage
        fields = ['content', 'message_type', 'image', 'file']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 2, 'placeholder': _('Type a message...')}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['message_type'].widget = forms.HiddenInput()
        self.fields['image'].widget = forms.FileInput(attrs={'accept': 'image/*', 'class': 'image-upload'})
        self.fields['file'].widget = forms.FileInput(attrs={'class': 'file-upload'})
        
        # Make fields optional
        self.fields['content'].required = False
        self.fields['image'].required = False
        self.fields['file'].required = False
    
    def clean(self):
        cleaned_data = super().clean()
        content = cleaned_data.get('content')
        image = cleaned_data.get('image')
        file = cleaned_data.get('file')
        
        # At least one of content, image or file must be provided
        if not content and not image and not file:
            raise forms.ValidationError(_('Message cannot be empty'))
        
        # Update message_type based on attachments
        if image:
            cleaned_data['message_type'] = 'image'
        elif file:
            cleaned_data['message_type'] = 'file'
        else:
            cleaned_data['message_type'] = 'text'
        
        return cleaned_data


class ChatGroupInvitationForm(forms.ModelForm):
    """Form for inviting users to a chat group"""
    users = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(is_active=True),
        label=_('Select Users'),
        widget=forms.SelectMultiple(attrs={'class': 'select2'})
    )
    
    class Meta:
        model = ChatGroupInvitation
        fields = ['group']
        widgets = {
            'group': forms.HiddenInput()
        }


class ChatGroupMemberForm(forms.ModelForm):
    """Form for managing chat group members"""
    class Meta:
        model = ChatGroupMember
        fields = ['user', 'role']
        widgets = {
            'user': forms.Select(attrs={'class': 'select2'}),
        }


class ChatGroupJoinForm(forms.Form):
    """Form for joining a chat group"""
    group_uuid = forms.UUIDField(widget=forms.HiddenInput())


class ChatSearchForm(forms.Form):
    """Form for searching chat messages"""
    query = forms.CharField(
        label=_('Search'),
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': _('Search in chat...')})
    )
    date_from = forms.DateField(
        label=_('From'),
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    date_to = forms.DateField(
        label=_('To'),
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    sender = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True),
        label=_('From User'),
        required=False,
        widget=forms.Select(attrs={'class': 'select2'})
    )
    message_type = forms.ChoiceField(
        choices=[(None, 'All')] + list(ChatMessage.MESSAGE_TYPES),
        label=_('Message Type'),
        required=False
    )
