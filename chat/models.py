from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from tenants.models import School
from django.utils import timezone
import uuid


class ChatGroup(models.Model):
    """Chat Group Model"""
    GROUP_TYPES = [
        ('direct', 'Direct Message'),
        ('class', 'Class Group'),
        ('department', 'Department Group'),
        ('general', 'General Group'),
        ('event', 'Event Group'),
        ('parent', 'Parent Group'),
        ('custom', 'Custom Group'),
    ]
    
    name = models.CharField(_('Group Name'), max_length=255)
    description = models.TextField(_('Description'), blank=True)
    group_type = models.CharField(_('Group Type'), max_length=20, choices=GROUP_TYPES, default='general')
    group_uuid = models.UUIDField(_('Group UUID'), default=uuid.uuid4, unique=True)
    
    # If class-specific
    class_ref = models.ForeignKey('academics.Class', on_delete=models.CASCADE, 
                                null=True, blank=True, related_name='chat_groups')
    section_ref = models.ForeignKey('academics.Section', on_delete=models.CASCADE, 
                                  null=True, blank=True, related_name='chat_groups')
    
    # If event-specific
    event_ref = models.ForeignKey('core.CalendarEvent', on_delete=models.CASCADE, 
                                null=True, blank=True, related_name='chat_groups')
    
    # Group settings
    is_public = models.BooleanField(_('Is Public'), default=False)
    allow_join = models.BooleanField(_('Allow Join'), default=True)
    auto_add_members = models.BooleanField(_('Auto Add Members'), default=False)
    
    # School association (for multi-tenant)
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='chat_groups', null=True, blank=True)
    
    # Created by and timestamps
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, 
                                 null=True, related_name='created_chat_groups')
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    # Group avatar
    avatar = models.ImageField(_('Avatar'), upload_to='chat/avatars/', blank=True, null=True)
    
    # Activity
    last_activity = models.DateTimeField(_('Last Activity'), default=timezone.now)
    
    class Meta:
        verbose_name = _('Chat Group')
        verbose_name_plural = _('Chat Groups')
        ordering = ['-last_activity']
    
    def __str__(self):
        return self.name


class ChatGroupMember(models.Model):
    """Chat Group Member Model"""
    MEMBER_ROLES = [
        ('admin', 'Admin'),
        ('moderator', 'Moderator'),
        ('member', 'Member'),
        ('guest', 'Guest'),
    ]
    
    group = models.ForeignKey(ChatGroup, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='chat_memberships')
    
    role = models.CharField(_('Role'), max_length=20, choices=MEMBER_ROLES, default='member')
    joined_at = models.DateTimeField(_('Joined At'), auto_now_add=True)
    invited_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, 
                                  null=True, blank=True, related_name='invited_members')
    
    # Notification settings
    mute_notifications = models.BooleanField(_('Mute Notifications'), default=False)
    
    # Last read message timestamp
    last_read = models.DateTimeField(_('Last Read'), null=True, blank=True)
    
    class Meta:
        verbose_name = _('Chat Group Member')
        verbose_name_plural = _('Chat Group Members')
        unique_together = ['group', 'user']
        ordering = ['group', 'joined_at']
    
    def __str__(self):
        return f"{self.user} in {self.group}"


class ChatMessage(models.Model):
    """Chat Message Model"""
    MESSAGE_TYPES = [
        ('text', 'Text'),
        ('image', 'Image'),
        ('file', 'File'),
        ('audio', 'Audio'),
        ('video', 'Video'),
        ('system', 'System Message'),
    ]
    
    group = models.ForeignKey(ChatGroup, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='chat_sent_messages')
    
    # Message content
    message_type = models.CharField(_('Message Type'), max_length=10, choices=MESSAGE_TYPES, default='text')
    content = models.TextField(_('Content'))
    
    # Media attachments
    image = models.ImageField(_('Image'), upload_to='chat/images/', blank=True, null=True)
    file = models.FileField(_('File'), upload_to='chat/files/', blank=True, null=True)
    file_name = models.CharField(_('File Name'), max_length=255, blank=True)
    file_size = models.PositiveIntegerField(_('File Size (bytes)'), default=0)
    
    # Reply reference
    reply_to = models.ForeignKey('self', on_delete=models.SET_NULL, 
                               null=True, blank=True, related_name='replies')
    
    # Message metadata
    sent_at = models.DateTimeField(_('Sent At'), default=timezone.now)
    edited_at = models.DateTimeField(_('Edited At'), null=True, blank=True)
    is_edited = models.BooleanField(_('Is Edited'), default=False)
    
    # Message status
    is_deleted = models.BooleanField(_('Is Deleted'), default=False)
    
    class Meta:
        verbose_name = _('Chat Message')
        verbose_name_plural = _('Chat Messages')
        ordering = ['sent_at']
    
    def __str__(self):
        if len(self.content) > 50:
            return f"{self.content[:50]}..."
        return self.content
    
    def save(self, *args, **kwargs):
        # Update group's last activity when a new message is sent
        self.group.last_activity = timezone.now()
        self.group.save(update_fields=['last_activity'])
        
        # Set edited status if it's an update
        if self.pk:
            self.is_edited = True
            self.edited_at = timezone.now()
        
        super().save(*args, **kwargs)


class ChatMessageRead(models.Model):
    """Chat Message Read Status"""
    message = models.ForeignKey(ChatMessage, on_delete=models.CASCADE, related_name='read_receipts')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='read_messages')
    read_at = models.DateTimeField(_('Read At'), default=timezone.now)
    
    class Meta:
        verbose_name = _('Chat Message Read Receipt')
        verbose_name_plural = _('Chat Message Read Receipts')
        unique_together = ['message', 'user']
    
    def __str__(self):
        return f"{self.user} read message {self.message.id} at {self.read_at}"


class ChatMessageReaction(models.Model):
    """Chat Message Reaction Model"""
    message = models.ForeignKey(ChatMessage, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='message_reactions')
    
    reaction = models.CharField(_('Reaction'), max_length=50)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('Chat Message Reaction')
        verbose_name_plural = _('Chat Message Reactions')
        unique_together = ['message', 'user', 'reaction']
    
    def __str__(self):
        return f"{self.user} reacted with {self.reaction} to message {self.message.id}"


class ChatGroupInvitation(models.Model):
    """Chat Group Invitation Model"""
    group = models.ForeignKey(ChatGroup, on_delete=models.CASCADE, related_name='invitations')
    inviter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_invitations')
    invitee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_invitations')
    
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    expires_at = models.DateTimeField(_('Expires At'), null=True, blank=True)
    is_accepted = models.BooleanField(_('Is Accepted'), default=False)
    accepted_at = models.DateTimeField(_('Accepted At'), null=True, blank=True)
    
    class Meta:
        verbose_name = _('Chat Group Invitation')
        verbose_name_plural = _('Chat Group Invitations')
        unique_together = ['group', 'invitee']
    
    def __str__(self):
        return f"Invitation to {self.invitee} for {self.group.name}"
    
    def accept(self):
        """Accept the invitation"""
        self.is_accepted = True
        self.accepted_at = timezone.now()
        self.save(update_fields=['is_accepted', 'accepted_at'])
        
        # Create membership
        ChatGroupMember.objects.create(
            group=self.group,
            user=self.invitee,
            role='member',
            invited_by=self.inviter
        )
