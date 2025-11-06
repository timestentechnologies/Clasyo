from django.shortcuts import render
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.db import models
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from students.models import Student

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
        # Filter notices based on user role
        if user.role == 'super_admin' or user.role == 'school_admin':
            return Notice.objects.all().order_by('-created_at')
        else:
            return Notice.objects.filter(
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


class MessageListView(LoginRequiredMixin, ListView):
    template_name = 'communication/messages.html'
    context_object_name = 'messages_list'
    
    def get_queryset(self):
        if not MODELS_EXIST:
            return []
        user = self.request.user
        # Return messages sent to or from the user
        return Message.objects.filter(
            models.Q(sender=user) | models.Q(receiver=user)
        ).order_by('-created_at')
    
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
                receiver_id=request.POST.get('recipient'),
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
            message = Message.objects.get(pk=kwargs['pk'])
            return JsonResponse({
                'sender': message.sender.get_full_name(),
                'subject': message.subject,
                'message': message.message,
                'created_at': message.created_at.strftime('%B %d, %Y %I:%M %p')
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
                receiver=receiver,
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
            message = Message.objects.get(pk=kwargs['pk'])
            message.delete()
            return JsonResponse({'success': True})
        except Message.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Message not found'})
