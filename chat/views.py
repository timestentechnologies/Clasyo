from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, FormView, View, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.http import HttpResponse, JsonResponse, Http404
from django.utils import timezone
from django.db.models import Q, Max
from django.utils.translation import gettext as _
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
import json

from .models import ChatGroup, ChatGroupMember, ChatMessage, ChatMessageRead, ChatMessageReaction, ChatGroupInvitation
from .forms import ChatGroupForm, ChatMessageForm, ChatGroupInvitationForm, ChatGroupMemberForm, ChatGroupJoinForm, ChatSearchForm

User = get_user_model()


# Chat Group Views
class ChatDashboardView(LoginRequiredMixin, TemplateView):
    """Dashboard showing all chat groups"""
    template_name = 'chat/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        school_slug = self.kwargs.get('school_slug', '')
        
        # Get user's chat groups
        user_groups = ChatGroup.objects.filter(
            members__user=user
        ).select_related('class_ref', 'event_ref').order_by('-last_activity')
        
        # Get public groups user hasn't joined
        public_groups = ChatGroup.objects.filter(
            is_public=True
        ).exclude(
            members__user=user
        ).order_by('name')
        
        # Count unread messages in each group
        for group in user_groups:
            # Get user's last read timestamp for this group
            member = ChatGroupMember.objects.filter(group=group, user=user).first()
            last_read = member.last_read if member and member.last_read else timezone.make_aware(timezone.datetime.min)
            
            # Count unread messages
            group.unread_count = ChatMessage.objects.filter(
                group=group,
                sent_at__gt=last_read
            ).exclude(
                sender=user
            ).count()
            
            # Get latest message
            latest_message = ChatMessage.objects.filter(group=group).order_by('-sent_at').first()
            group.latest_message = latest_message
        
        context.update({
            'school_slug': school_slug,
            'user_groups': user_groups,
            'public_groups': public_groups,
        })
        return context


class ChatGroupListView(LoginRequiredMixin, ListView):
    """List of Chat Groups"""
    model = ChatGroup
    template_name = 'chat/group_list.html'
    context_object_name = 'groups'
    
    def get_queryset(self):
        user = self.request.user
        # Get user's groups and public groups
        return ChatGroup.objects.filter(
            Q(members__user=user) | Q(is_public=True)
        ).distinct().order_by('-last_activity')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        return context


class ChatGroupCreateView(LoginRequiredMixin, CreateView):
    """Create a new Chat Group"""
    model = ChatGroup
    form_class = ChatGroupForm
    template_name = 'chat/group_form.html'
    
    def get_success_url(self):
        return reverse('chat:group_detail', kwargs={
            'school_slug': self.kwargs.get('school_slug', ''),
            'pk': self.object.id
        })
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        context['title'] = _('Create Chat Group')
        return context
    
    def form_valid(self, form):
        # Set creator
        form.instance.created_by = self.request.user
        
        # Associate with school
        school_slug = self.kwargs.get('school_slug')
        from tenants.models import School
        try:
            school = School.objects.get(slug=school_slug)
            form.instance.school = school
        except School.DoesNotExist:
            pass
        
        # Save the group
        response = super().form_valid(form)
        
        # Add creator as admin member
        ChatGroupMember.objects.create(
            group=self.object,
            user=self.request.user,
            role='admin'
        )
        
        # Auto-add members if specified
        if form.cleaned_data['auto_add_members']:
            self._auto_add_members()
            
        messages.success(self.request, _('Chat group created successfully'))
        return response
    
    def _auto_add_members(self):
        """Auto-add members based on group type"""
        group_type = self.object.group_type
        
        if group_type == 'class' and self.object.class_ref:
            # Add all students in the class
            from students.models import Student
            students = Student.objects.filter(current_class=self.object.class_ref, is_active=True)
            
            # If section is specified, filter by section
            if self.object.section_ref:
                students = students.filter(section=self.object.section_ref)
                
            # Add students' user accounts to the group
            for student in students:
                if hasattr(student, 'user') and student.user:
                    ChatGroupMember.objects.get_or_create(
                        group=self.object,
                        user=student.user,
                        defaults={'role': 'member'}
                    )
            
            # Add class teacher if available
            if self.object.section_ref and self.object.section_ref.class_teacher:
                ChatGroupMember.objects.get_or_create(
                    group=self.object,
                    user=self.object.section_ref.class_teacher,
                    defaults={'role': 'moderator'}
                )
        
        elif group_type == 'event' and self.object.event_ref:
            # Add event participants
            for participant in self.object.event_ref.participants.all():
                ChatGroupMember.objects.get_or_create(
                    group=self.object,
                    user=participant,
                    defaults={'role': 'member'}
                )
                
            # Add event creator as moderator
            if self.object.event_ref.created_by:
                ChatGroupMember.objects.get_or_create(
                    group=self.object,
                    user=self.object.event_ref.created_by,
                    defaults={'role': 'moderator'}
                )


class ChatGroupDetailView(LoginRequiredMixin, DetailView):
    """View chat group and messages"""
    model = ChatGroup
    template_name = 'chat/group_detail.html'
    context_object_name = 'group'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        group = self.object
        user = self.request.user
        school_slug = self.kwargs.get('school_slug', '')
        
        # Check if user is a member
        try:
            member = ChatGroupMember.objects.get(group=group, user=user)
            is_member = True
        except ChatGroupMember.DoesNotExist:
            member = None
            is_member = False
        
        # Get messages with pagination
        messages_qs = ChatMessage.objects.filter(group=group).select_related('sender').order_by('-sent_at')
        
        # Pagination
        page_number = self.request.GET.get('page', 1)
        paginator = Paginator(messages_qs, 50)  # 50 messages per page
        chat_messages = paginator.get_page(page_number)
        
        # Update last read timestamp for this user
        if member:
            member.last_read = timezone.now()
            member.save(update_fields=['last_read'])
        
        # Get members
        members = ChatGroupMember.objects.filter(group=group).select_related('user')
        
        # Message form
        message_form = ChatMessageForm() if is_member else None
        
        # Check if user can manage the group
        can_manage = is_member and member and member.role in ['admin', 'moderator']
        
        context.update({
            'school_slug': school_slug,
            'chat_messages': chat_messages,
            'members': members,
            'is_member': is_member,
            'can_manage': can_manage,
            'message_form': message_form,
        })
        
        return context


class ChatGroupUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """Update chat group settings"""
    model = ChatGroup
    form_class = ChatGroupForm
    template_name = 'chat/group_form.html'
    
    def test_func(self):
        # Only admins and moderators can edit the group
        group = self.get_object()
        try:
            member = ChatGroupMember.objects.get(group=group, user=self.request.user)
            return member.role in ['admin', 'moderator']
        except ChatGroupMember.DoesNotExist:
            return False
    
    def get_success_url(self):
        return reverse('chat:group_detail', kwargs={
            'school_slug': self.kwargs.get('school_slug', ''),
            'pk': self.object.id
        })
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        context['title'] = _('Update Chat Group')
        return context
    
    def form_valid(self, form):
        messages.success(self.request, _('Chat group updated successfully'))
        return super().form_valid(form)


class ChatGroupDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """Delete a chat group"""
    model = ChatGroup
    template_name = 'chat/confirm_delete.html'
    
    def test_func(self):
        # Only admins can delete the group
        group = self.get_object()
        try:
            member = ChatGroupMember.objects.get(group=group, user=self.request.user)
            return member.role == 'admin'
        except ChatGroupMember.DoesNotExist:
            return False
    
    def get_success_url(self):
        return reverse('chat:dashboard', kwargs={'school_slug': self.kwargs.get('school_slug', '')})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        context['title'] = _('Delete Chat Group')
        context['message'] = _('Are you sure you want to delete this chat group? All messages will be permanently deleted.')
        return context


class ChatMessageCreateView(LoginRequiredMixin, CreateView):
    """Create a new chat message"""
    model = ChatMessage
    form_class = ChatMessageForm
    http_method_names = ['post']
    
    def form_valid(self, form):
        group_id = self.kwargs.get('group_id')
        group = get_object_or_404(ChatGroup, id=group_id)
        
        # Check if user is a member
        try:
            ChatGroupMember.objects.get(group=group, user=self.request.user)
        except ChatGroupMember.DoesNotExist:
            messages.error(self.request, _('You are not a member of this group'))
            return redirect('chat:group_detail', school_slug=self.kwargs.get('school_slug', ''), pk=group.id)
        
        # Set message attributes
        form.instance.group = group
        form.instance.sender = self.request.user
        
        # Handle file uploads
        if form.instance.file and not form.instance.file_name:
            form.instance.file_name = form.instance.file.name
            form.instance.file_size = form.instance.file.size
        
        response = super().form_valid(form)
        
        # If it's an AJAX request, return JSON response
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message_id': self.object.id,
                'sent_at': self.object.sent_at.isoformat(),
            })
            
        return response
    
    def form_invalid(self, form):
        # If it's an AJAX request, return error as JSON
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'errors': form.errors
            }, status=400)
            
        messages.error(self.request, _('Error sending message'))
        return redirect('chat:group_detail', school_slug=self.kwargs.get('school_slug', ''), pk=self.kwargs.get('group_id'))
    
    def get_success_url(self):
        return reverse('chat:group_detail', kwargs={
            'school_slug': self.kwargs.get('school_slug', ''),
            'pk': self.kwargs.get('group_id')
        })


class ChatMessageDeleteView(LoginRequiredMixin, DeleteView):
    """Delete a chat message"""
    model = ChatMessage
    template_name = 'chat/confirm_delete.html'
    
    def get_success_url(self):
        return reverse('chat:group_detail', kwargs={
            'school_slug': self.kwargs.get('school_slug', ''),
            'pk': self.object.group.id
        })
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        context['title'] = _('Delete Message')
        context['message'] = _('Are you sure you want to delete this message?')
        return context
    
    def dispatch(self, request, *args, **kwargs):
        # Check if user has permission to delete this message
        message = self.get_object()
        user = request.user
        
        # Users can delete their own messages
        if message.sender == user:
            return super().dispatch(request, *args, **kwargs)
        
        # Admins and moderators can delete any message in their group
        try:
            member = ChatGroupMember.objects.get(group=message.group, user=user)
            if member.role in ['admin', 'moderator']:
                return super().dispatch(request, *args, **kwargs)
        except ChatGroupMember.DoesNotExist:
            pass
        
        # No permission
        messages.error(request, _('You do not have permission to delete this message'))
        return redirect('chat:group_detail', school_slug=self.kwargs.get('school_slug', ''), pk=message.group.id)


# Chat Group Member Management Views
class ChatGroupMemberListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """List members of a chat group"""
    model = ChatGroupMember
    template_name = 'chat/group_members.html'
    context_object_name = 'members'
    
    def test_func(self):
        # Only members can view the member list
        group_id = self.kwargs.get('group_id')
        group = get_object_or_404(ChatGroup, id=group_id)
        return ChatGroupMember.objects.filter(group=group, user=self.request.user).exists()
    
    def get_queryset(self):
        group_id = self.kwargs.get('group_id')
        return ChatGroupMember.objects.filter(group_id=group_id).select_related('user')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        group_id = self.kwargs.get('group_id')
        group = get_object_or_404(ChatGroup, id=group_id)
        user = self.request.user
        
        context.update({
            'school_slug': self.kwargs.get('school_slug', ''),
            'group': group,
            'user_is_admin': ChatGroupMember.objects.filter(group=group, user=user, role='admin').exists(),
            'user_is_moderator': ChatGroupMember.objects.filter(group=group, user=user, role__in=['admin', 'moderator']).exists(),
        })
        return context


class ChatGroupJoinView(LoginRequiredMixin, View):
    """Join a public chat group"""
    
    def post(self, request, *args, **kwargs):
        group_id = self.kwargs.get('group_id')
        group = get_object_or_404(ChatGroup, id=group_id)
        
        # Check if user is already a member
        if ChatGroupMember.objects.filter(group=group, user=request.user).exists():
            messages.warning(request, _('You are already a member of this group'))
            return redirect('chat:group_detail', school_slug=self.kwargs.get('school_slug', ''), pk=group.id)
        
        # Check if group allows joining
        if not group.allow_join or not group.is_public:
            messages.error(request, _('This group does not allow public joining'))
            return redirect('chat:dashboard', school_slug=self.kwargs.get('school_slug', ''))
        
        # Create membership
        ChatGroupMember.objects.create(
            group=group,
            user=request.user,
            role='member'
        )
        
        # Add system message to the group
        ChatMessage.objects.create(
            group=group,
            sender=request.user,
            content=f"{request.user.get_full_name()} joined the group",
            message_type='system'
        )
        
        messages.success(request, _('You have successfully joined the group'))
        return redirect('chat:group_detail', school_slug=self.kwargs.get('school_slug', ''), pk=group.id)


class ChatGroupLeaveView(LoginRequiredMixin, View):
    """Leave a chat group"""
    
    def post(self, request, *args, **kwargs):
        group_id = self.kwargs.get('group_id')
        group = get_object_or_404(ChatGroup, id=group_id)
        
        # Check if user is a member
        try:
            member = ChatGroupMember.objects.get(group=group, user=request.user)
        except ChatGroupMember.DoesNotExist:
            messages.warning(request, _('You are not a member of this group'))
            return redirect('chat:dashboard', school_slug=self.kwargs.get('school_slug', ''))
        
        # Check if user is the only admin
        if member.role == 'admin':
            admin_count = ChatGroupMember.objects.filter(group=group, role='admin').count()
            if admin_count == 1:
                messages.error(request, _('You cannot leave the group as you are the only admin. Please assign another admin first.'))
                return redirect('chat:group_detail', school_slug=self.kwargs.get('school_slug', ''), pk=group.id)
        
        # Delete membership
        member.delete()
        
        # Add system message to the group
        ChatMessage.objects.create(
            group=group,
            sender=request.user,  # This is technically not accurate as they've left, but needed for the model
            content=f"{request.user.get_full_name()} left the group",
            message_type='system'
        )
        
        messages.success(request, _('You have successfully left the group'))
        return redirect('chat:dashboard', school_slug=self.kwargs.get('school_slug', ''))


class ChatGroupInviteView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    """Invite users to a chat group"""
    form_class = ChatGroupInvitationForm
    template_name = 'chat/group_invite.html'
    
    def test_func(self):
        # Only group members can invite others
        group_id = self.kwargs.get('group_id')
        group = get_object_or_404(ChatGroup, id=group_id)
        return ChatGroupMember.objects.filter(group=group, user=self.request.user).exists()
    
    def get_initial(self):
        return {'group': self.kwargs.get('group_id')}
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        group_id = self.kwargs.get('group_id')
        group = get_object_or_404(ChatGroup, id=group_id)
        
        # Exclude users who are already members
        existing_members = ChatGroupMember.objects.filter(group=group).values_list('user_id', flat=True)
        form.fields['users'].queryset = User.objects.filter(is_active=True).exclude(id__in=existing_members)
        
        return form
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        group_id = self.kwargs.get('group_id')
        group = get_object_or_404(ChatGroup, id=group_id)
        
        context.update({
            'school_slug': self.kwargs.get('school_slug', ''),
            'group': group,
            'title': _('Invite Users to Chat Group')
        })
        return context
    
    def form_valid(self, form):
        group_id = self.kwargs.get('group_id')
        group = get_object_or_404(ChatGroup, id=group_id)
        users = form.cleaned_data['users']
        inviter = self.request.user
        
        # Create invitations
        invitation_count = 0
        for user in users:
            # Skip if already a member
            if ChatGroupMember.objects.filter(group=group, user=user).exists():
                continue
                
            # Create or update invitation
            invitation, created = ChatGroupInvitation.objects.update_or_create(
                group=group,
                invitee=user,
                defaults={
                    'inviter': inviter,
                    'is_accepted': False,
                    'expires_at': timezone.now() + timezone.timedelta(days=7)
                }
            )
            invitation_count += 1
            
        messages.success(self.request, _(f'{invitation_count} invitations sent successfully'))
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('chat:group_detail', kwargs={
            'school_slug': self.kwargs.get('school_slug', ''),
            'pk': self.kwargs.get('group_id')
        })


class ChatGroupAcceptInvitationView(LoginRequiredMixin, View):
    """Accept an invitation to join a chat group"""
    
    def get(self, request, *args, **kwargs):
        invitation_id = self.kwargs.get('invitation_id')
        invitation = get_object_or_404(ChatGroupInvitation, id=invitation_id, invitee=request.user)
        
        # Check if invitation is expired
        if invitation.expires_at and invitation.expires_at < timezone.now():
            messages.error(request, _('This invitation has expired'))
            return redirect('chat:dashboard', school_slug=self.kwargs.get('school_slug', ''))
        
        # Check if already a member
        if ChatGroupMember.objects.filter(group=invitation.group, user=request.user).exists():
            messages.info(request, _('You are already a member of this group'))
            invitation.delete()  # Clean up the invitation
            return redirect('chat:group_detail', school_slug=self.kwargs.get('school_slug', ''), pk=invitation.group.id)
        
        # Accept the invitation
        invitation.accept()
        
        # Add system message to the group
        ChatMessage.objects.create(
            group=invitation.group,
            sender=request.user,
            content=f"{request.user.get_full_name()} joined the group",
            message_type='system'
        )
        
        messages.success(request, _('You have successfully joined the group'))
        return redirect('chat:group_detail', school_slug=self.kwargs.get('school_slug', ''), pk=invitation.group.id)
