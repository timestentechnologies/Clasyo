from django.shortcuts import render
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.db import models
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from students.models import Student
from core.utils import get_current_school

# Check if models exist
try:
    from .models import Notice, Message
    MODELS_EXIST = True
except ImportError:
    MODELS_EXIST = False
    class Notice:
        pass
    class Message:
        pass


@method_decorator(csrf_exempt, name='dispatch')
class NoticeListView(LoginRequiredMixin, ListView):
    template_name = 'communication/notices.html'
    context_object_name = 'notices'
    
    def get_queryset(self):
        if not MODELS_EXIST:
            return []
        user = self.request.user
        school = get_current_school(self.request)
        qs = Notice.objects.all()
        if school:
            qs = qs.filter(created_by__school=school)
        # Filter notices based on user role
        if user.role == 'superadmin' or user.role == 'admin':
            return qs.order_by('-created_at')
        else:
            return qs.filter(
                models.Q(target_audience='all') | 
                models.Q(target_audience=user.role)
            ).order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        return context
    
    def post(self, request, *args, **kwargs):
        try:
            if not MODELS_EXIST:
                return JsonResponse({'success': False, 'error': 'Notice model not available'})

            if getattr(request.user, 'role', None) not in ('superadmin', 'admin'):
                return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
            
            Notice.objects.create(
                title=request.POST.get('title'),
                content=request.POST.get('content'),
                target_audience=request.POST.get('target_audience', 'all'),
                priority=request.POST.get('priority', 'normal'),
                created_by=request.user
            )
            return JsonResponse({'success': True, 'message': 'Notice posted successfully!'})
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'success': False, 'error': str(e)})


class NoticeDetailView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        if not MODELS_EXIST:
            return JsonResponse({'success': False, 'error': 'Notice model not available'})
        try:
            school = get_current_school(request)
            notice_qs = Notice.objects.all()
            if school:
                notice_qs = notice_qs.filter(created_by__school=school)
            notice = notice_qs.get(pk=kwargs.get('pk'))
            return JsonResponse({
                'success': True,
                'id': notice.id,
                'title': notice.title,
                'content': notice.content,
                'target_audience': notice.target_audience,
                'priority': notice.priority,
                'created_at': notice.created_at.isoformat(),
                'updated_at': notice.updated_at.isoformat(),
            })
        except Notice.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Notice not found'}, status=404)


@method_decorator(csrf_exempt, name='dispatch')
class NoticeUpdateView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        if not MODELS_EXIST:
            return JsonResponse({'success': False, 'error': 'Notice model not available'})
        if getattr(request.user, 'role', None) not in ('superadmin', 'admin'):
            return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
        try:
            school = get_current_school(request)
            notice_qs = Notice.objects.all()
            if school:
                notice_qs = notice_qs.filter(created_by__school=school)
            notice = notice_qs.get(pk=kwargs.get('pk'))
            title = request.POST.get('title')
            content = request.POST.get('content')
            target_audience = request.POST.get('target_audience')
            priority = request.POST.get('priority')
            if title is not None:
                notice.title = title
            if content is not None:
                notice.content = content
            if target_audience is not None:
                notice.target_audience = target_audience
            if priority is not None:
                notice.priority = priority
            notice.save()
            return JsonResponse({'success': True, 'message': 'Notice updated successfully'})
        except Notice.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Notice not found'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)


@method_decorator(csrf_exempt, name='dispatch')
class NoticeDeleteView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        if not MODELS_EXIST:
            return JsonResponse({'success': False, 'error': 'Notice model not available'})
        if getattr(request.user, 'role', None) not in ('superadmin', 'admin'):
            return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
        try:
            school = get_current_school(request)
            notice_qs = Notice.objects.all()
            if school:
                notice_qs = notice_qs.filter(created_by__school=school)
            notice = notice_qs.get(pk=kwargs.get('pk'))
            notice.delete()
            return JsonResponse({'success': True, 'message': 'Notice deleted successfully'})
        except Notice.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Notice not found'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)


class MessageListView(LoginRequiredMixin, ListView):
    template_name = 'communication/messages.html'
    context_object_name = 'messages_list'
    
    def get_queryset(self):
        if not MODELS_EXIST:
            return []
        user = self.request.user
        school = get_current_school(self.request)
        qs = Message.objects.filter(models.Q(sender=user) | models.Q(recipient=user))
        if school:
            qs = qs.filter(models.Q(sender__school=school) | models.Q(recipient__school=school))
        # Show only root messages (exclude replies in main list)
        qs = qs.filter(parent_message__isnull=True)
        return qs.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        return context
    
    def post(self, request, *args, **kwargs):
        try:
            if not MODELS_EXIST:
                return JsonResponse({'success': False, 'error': 'Models not available'})
            Message.objects.create(
                sender=request.user,
                recipient_id=request.POST.get('recipient'),
                subject=request.POST.get('subject'),
                message=request.POST.get('message')
            )
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})


class MessageDetailView(LoginRequiredMixin, DetailView):
    def get(self, request, *args, **kwargs):
        if not MODELS_EXIST:
            return JsonResponse({'success': False, 'error': 'Models not available'})
        try:
            school = get_current_school(request)
            message_qs = Message.objects.all()
            if school:
                message_qs = message_qs.filter(models.Q(sender__school=school) | models.Q(recipient__school=school))
            message = message_qs.get(pk=kwargs['pk'])
            # Build thread: original + replies (ascending by time)
            replies = []
            for r in message.replies.all().order_by('created_at'):
                replies.append({
                    'id': r.id,
                    'sender': r.sender.get_full_name() or r.sender.email,
                    'sender_id': r.sender_id,
                    'message': r.message,
                    'created_at': r.created_at.isoformat(),
                    'created_at_display': r.created_at.strftime('%b %d, %Y %I:%M %p')
                })
            return JsonResponse({
                'success': True,
                'id': message.id,
                'sender': message.sender.get_full_name() or message.sender.email,
                'sender_id': message.sender_id,
                'recipient': message.recipient.get_full_name() or message.recipient.email,
                'subject': message.subject,
                'message': message.message,
                'created_at': message.created_at.isoformat(),
                'created_at_display': message.created_at.strftime('%b %d, %Y %I:%M %p'),
                'replies': replies,
            })
        except Message.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Message not found'})


@method_decorator(csrf_exempt, name='dispatch')
class MessageSendView(LoginRequiredMixin, View):
    """Send a message"""
    def post(self, request, *args, **kwargs):
        try:
            if not MODELS_EXIST:
                return JsonResponse({'success': False, 'error': 'Models not available'})
            
            from accounts.models import User
            
            recipient_type = request.POST.get('recipient_type')
            
            if recipient_type == 'custom':
                # Find user by email
                receiver_email = request.POST.get('receiver_email')
                try:
                    receiver = User.objects.get(email=receiver_email)
                except User.DoesNotExist:
                    return JsonResponse({'success': False, 'error': 'User not found with that email'})
            else:
                # Get user by ID
                receiver_id = request.POST.get('receiver_id')
                if not receiver_id:
                    return JsonResponse({'success': False, 'error': 'Please select a recipient'})
                try:
                    receiver = User.objects.get(pk=receiver_id)
                except User.DoesNotExist:
                    return JsonResponse({'success': False, 'error': 'Recipient not found'})
            
            Message.objects.create(
                sender=request.user,
                recipient=receiver,
                subject=request.POST.get('subject'),
                message=request.POST.get('message')
            )
            return JsonResponse({'success': True, 'message': 'Message sent successfully!'})
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'success': False, 'error': str(e)})


@method_decorator(csrf_exempt, name='dispatch')
class RecipientListView(LoginRequiredMixin, View):
    """Get list of recipients by type"""
    def get(self, request, recipient_type, *args, **kwargs):
        try:
            from accounts.models import User
            school = get_current_school(request)
            
            if recipient_type == 'student':
                users = User.objects.filter(role='student')
            elif recipient_type == 'teacher':
                users = User.objects.filter(role='teacher')
            elif recipient_type == 'parent':
                users = User.objects.filter(role='parent')
            elif recipient_type == 'staff':
                users = User.objects.filter(role='staff')
            else:
                return JsonResponse({'success': False, 'error': 'Invalid recipient type'})
            
            if school:
                users = users.filter(school=school)
            
            recipients = [{
                'id': u.id,
                'name': u.get_full_name() or u.email,
                'email': u.email
            } for u in users[:100]]  # Limit to 100
            
            return JsonResponse({'success': True, 'recipients': recipients})
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'success': False, 'error': str(e)})


class MessageDeleteView(LoginRequiredMixin, DeleteView):
    def post(self, request, *args, **kwargs):
        if not MODELS_EXIST:
            return JsonResponse({'success': False, 'error': 'Models not available'})
        try:
            school = get_current_school(request)
            message_qs = Message.objects.all()
            if school:
                message_qs = message_qs.filter(models.Q(sender__school=school) | models.Q(recipient__school=school))
            message = message_qs.get(pk=kwargs['pk'])
            message.delete()
            return JsonResponse({'success': True})
        except Message.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Message not found'})


class MessageReplyView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        if not MODELS_EXIST:
            return JsonResponse({'success': False, 'error': 'Models not available'})
            
        message_id = kwargs.get('pk')
        try:
            original_message = Message.objects.get(id=message_id)
            
            # Create a new message as a reply
            reply = Message.objects.create(
                sender=request.user,
                recipient=original_message.sender if request.user == original_message.recipient else original_message.recipient,
                subject=f"Re: {original_message.subject}",
                message=request.POST.get('message'),
                parent_message=original_message
            )
            
            return JsonResponse({
                'success': True,
                'message': 'Reply sent successfully',
                'reply': {
                    'id': reply.id,
                    'sender': str(reply.sender),
                    'message': reply.message,
                    'created_at': reply.created_at.isoformat(),
                }
            })
            
        except Message.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Original message not found'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)


class MessageReadView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        if not MODELS_EXIST:
            return JsonResponse({'success': False, 'error': 'Models not available'})
            
        message_id = kwargs.get('pk')
        try:
            message = Message.objects.get(id=message_id, recipient=request.user)
            if not message.is_read:
                message.is_read = True
                message.save(update_fields=['is_read'])
            return JsonResponse({'success': True})
        except Message.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Message not found'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
