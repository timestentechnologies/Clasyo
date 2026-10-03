import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import View, ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.db.models import Q
from django.http import HttpResponseForbidden, JsonResponse
from .models import User, Role, Permission, UserLoginLog
from .forms import LoginForm, UserRegistrationForm, ProfileEditForm, ChangePasswordForm, UserForm, RoleForm, PermissionForm

logger = logging.getLogger(__name__)


def csrf_failure(request, reason=""):
    """Custom CSRF failure view that redirects to home with helpful message"""
    messages.error(request, f'CSRF verification failed: {reason}. Please refresh the page and try again.')
    return redirect('frontend:home')


def clear_messages(request):
    """Safely consume and clear all pending messages from request/storage."""
    try:
        storage = messages.get_messages(request)
        for _ in storage:
            pass
        if hasattr(storage, 'used'):
            storage.used = True
    except Exception:
        pass


class LoginView(View):
    """User login view - redirects to home page with login modal"""
    template_name = 'frontend/home.html'
    form_class = LoginForm
    
    def get(self, request):
        # Redirect if already authenticated
        if request.user.is_authenticated:
            if request.user.role == 'superadmin':
                return redirect('superadmin:dashboard')
            else:
                from tenants.models import School
                school = getattr(request.user, 'school', None)
                if not school:
                    school = School.objects.filter(is_active=True).first()
                if school:
                    return redirect('core:apps_home', school_slug=school.slug)
                return redirect('frontend:home')
        
        # For unauthenticated users, redirect to home page
        from core.models import SystemSetting
        if SystemSetting.get_settings().maintenance_mode:
            return redirect('core:maintenance', school_slug='default')
            
        return redirect('frontend:home')
    
    def post(self, request):
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('ajax') == 'true' or 'application/json' in request.META.get('HTTP_ACCEPT', '')
        
        form = self.form_class(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            user = authenticate(request, username=email, password=password) or authenticate(request, email=email, password=password)
            
            if user is not None:
                if user.is_active:
                    # Check superadmin-only maintenance mode
                    from core.models import SystemSetting
                    sys_settings = SystemSetting.get_settings()
                    if sys_settings.maintenance_mode and sys_settings.superadmin_only_mode:
                        if user.role != 'superadmin' and not user.is_superuser:
                            if is_ajax:
                                return JsonResponse({'success': False, 'message': 'System is under exclusive maintenance. Only super administrators can log in.'}, status=403)
                            
                            clear_messages(request)
                            messages.error(request, 'System is under exclusive maintenance. Only super administrators can log in.')
                            school = getattr(user, 'school', None)
                            slug = school.slug if school else 'default'
                            return redirect('core:maintenance', school_slug=slug)
                    
                    # Clear any stale impersonation session data before login
                    if 'impersonated_user_id' in request.session:
                        del request.session['impersonated_user_id']
                    if 'original_user_id' in request.session:
                        del request.session['original_user_id']
                    # Ensure demo database session mode is never inherited across logins
                    if 'use_demo_database' in request.session:
                        del request.session['use_demo_database']
                    request.session.pop('real_school_slug', None)
                        
                    login(request, user)
                    
                    # Log the login
                    ip_address = request.META.get('REMOTE_ADDR')
                    user_agent = request.META.get('HTTP_USER_AGENT', '')
                    UserLoginLog.objects.create(
                        user=user,
                        ip_address=ip_address,
                        user_agent=user_agent
                    )
                    
                    # Update last login IP
                    user.last_login_ip = ip_address
                    user.save(update_fields=['last_login_ip'])
                    
                    # ALWAYS clear all accumulated messages from session to prevent old errors lingering
                    clear_messages(request)
                    
                    # Determine next URL parameter in GET or POST
                    next_url = request.GET.get('next') or request.POST.get('next')
                    
                    if user.role == 'superadmin':
                        redirect_target = reverse_lazy('superadmin:dashboard')
                    elif next_url and next_url.startswith('/'):
                        redirect_target = next_url
                    else:
                        from tenants.models import School
                        from tenants.services import register_tenant_connection
                        school = getattr(user, 'school', None)
                        if not school:
                            school = School.objects.filter(is_active=True).first()
                        
                        if school:
                            # Register tenant connection in-memory (instantaneous)
                            register_tenant_connection(school.slug)
                            redirect_target = reverse_lazy('core:apps_home', kwargs={'school_slug': school.slug})
                        else:
                            messages.warning(request, f'Welcome {user.get_full_name()}! No school associated with your account. Please contact administrator.')
                            redirect_target = reverse_lazy('frontend:home')
                    
                    target_url = str(redirect_target)
                    if is_ajax:
                        return JsonResponse({'success': True, 'redirect_url': target_url})
                    return redirect(target_url)
                else:
                    if is_ajax:
                        return JsonResponse({'success': False, 'message': 'Your account is inactive. Please contact the administrator.'}, status=403)
                    clear_messages(request)
                    messages.error(request, 'Your account is inactive. Please contact the administrator.')
                    return redirect('frontend:home')
            else:
                if is_ajax:
                    return JsonResponse({'success': False, 'message': 'Invalid email or password.'}, status=400)
                clear_messages(request)
                messages.error(request, 'Invalid email or password.')
                return redirect('frontend:home')
        else:
            first_err = 'Invalid email or password format.'
            for field, errors in form.errors.items():
                if errors:
                    first_err = errors[0]
                    break
            if is_ajax:
                return JsonResponse({'success': False, 'message': first_err}, status=400)
            clear_messages(request)
            messages.error(request, first_err)
            return redirect('frontend:home')


class LogoutView(LoginRequiredMixin, View):
    """User logout view"""
    def get(self, request):
        user = request.user
        school = getattr(user, 'school', None)
        if not school:
            from core.utils import get_current_school
            school = get_current_school(request)

        # If user was in a school with sample demo data loaded, auto-clear on logout
        # so user is never left on the sample database when logging in again
        if school and school.slug != 'demo-school':
            try:
                from students.models import Student
                from core.sample_data import clear_all_sample_data_for_school
                if Student.objects.using(school.slug).filter(is_sample_data=True).exists():
                    clear_all_sample_data_for_school(school, db_alias=school.slug)
            except Exception as e:
                logger.warning(f"Could not clear sample data on logout: {e}")

        # Update logout time in login log
        last_log = UserLoginLog.objects.filter(
            user=user,
            logout_time__isnull=True
        ).order_by('-login_time').first()
        
        if last_log:
            last_log.logout_time = timezone.now()
            last_log.session_duration = last_log.logout_time - last_log.login_time
            last_log.save()
        
        # Clear impersonation session data if any
        if 'impersonated_user_id' in request.session:
            del request.session['impersonated_user_id']
        if 'original_user_id' in request.session:
            del request.session['original_user_id']
        if 'use_demo_database' in request.session:
            del request.session['use_demo_database']
        request.session.pop('real_school_slug', None)
        
        logout(request)
        
        # Clear any existing messages so nothing lingers or pops up on the home page
        clear_messages(request)
        
        return redirect('frontend:home')


class RegisterView(View):
    """User registration view"""
    template_name = 'accounts/register.html'
    form_class = UserRegistrationForm
    
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('core:dashboard')
        form = self.form_class()
        return render(request, self.template_name, {'form': form})
    
    def post(self, request):
        form = self.form_class(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_verified = False
            raw_password = form.cleaned_data.get('password1')
            user.save()
            
            # Send notification and email
            from core.notifications import NotificationService
            try:
                # Use the user themselves as creator for self-registration
                NotificationService.notify_user_created(user, user, raw_password)
            except Exception as e:
                print(f"Error sending notification: {e}")
            
            messages.success(request, 'Registration successful! Please check your email and use the login modal to sign in.')
            return redirect('frontend:home')
        
        return render(request, self.template_name, {'form': form})


class SocialLoginCompleteView(LoginRequiredMixin, View):
    """Redirect users after social (e.g., Google) login using role-based logic"""

    def get(self, request):
        user = request.user

        # Ensure user is tagged with Google auth provider and verified
        if getattr(user, 'auth_provider', '') != 'google' or not user.is_verified:
            user.auth_provider = 'google'
            user.is_verified = True
            user.save(update_fields=['auth_provider', 'is_verified'])

        # Super admin: always go to superadmin dashboard
        if user.role == 'superadmin':
            return redirect('superadmin:dashboard')

        # For other roles, redirect to user's linked school; fallback to first active school
        from tenants.models import School
        school = getattr(user, 'school', None)
        if not school:
            school = School.objects.filter(is_active=True).first()

        if school:
            return redirect('core:apps_home', school_slug=school.slug)

        # No school associated
        messages.warning(
            request,
            f'Welcome {user.get_full_name()}! No school associated with your account. Please contact administrator.',
        )
        return redirect('frontend:home')


class PasswordResetView(View):
    """Password reset request view - handles sending reset emails and smart auth method detection"""
    
    def post(self, request):
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes
        from django.template.loader import render_to_string
        from django.core.mail import EmailMultiAlternatives
        from django.http import JsonResponse
        
        is_ajax = (
            request.headers.get('x-requested-with') == 'XMLHttpRequest' or
            request.POST.get('ajax') == 'true' or
            'application/json' in request.META.get('HTTP_ACCEPT', '')
        )
        
        email = request.POST.get('email', '').strip()
        if not email:
            err_msg = 'Please enter your email address.'
            if is_ajax:
                return JsonResponse({'success': False, 'message': err_msg}, status=400)
            messages.error(request, err_msg)
            return redirect('frontend:home')
        
        user = User.objects.filter(email__iexact=email).first()
        
        if user:
            # Check if this user used Google Sign-In
            has_google_social = user.socialaccount_set.filter(provider='google').exists()
            is_google_auth = (
                user.auth_provider == 'google' or
                has_google_social or
                (not user.has_usable_password() and has_google_social)
            )
            
            if is_google_auth:
                google_msg = (
                    "This account was created using Google Sign-In. "
                    "You do not have a password to reset. "
                    "Please sign in using the 'Continue with Google' button on the login screen."
                )
                if is_ajax:
                    return JsonResponse({
                        'success': False,
                        'is_google': True,
                        'auth_method': 'google',
                        'message': google_msg
                    })
                messages.warning(request, google_msg)
                return redirect('frontend:home')
            
            # User registered with Email & Password: Send reset link
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            
            reset_url = request.build_absolute_uri(
                f'/accounts/password-reset/confirm/{uid}/{token}/'
            )
            
            subject = 'Password Reset Request - Clasyo'
            text_body = (
                f"Hello {user.get_full_name()},\n\n"
                f"You requested to reset your password. Click the link below to set a new password:\n\n"
                f"{reset_url}\n\n"
                f"This link is valid for 24 hours. If you did not request this, please ignore this email.\n\n"
                f"Best regards,\n"
                f"Clasyo Team"
            )
            
            try:
                html_body = render_to_string('emails/password_reset_email.html', {
                    'user': user,
                    'reset_url': reset_url,
                })
                email_msg = EmailMultiAlternatives(
                    subject=subject,
                    body=text_body,
                    from_email=None,  # DynamicEmailBackend will inject active default from_email
                    to=[user.email]
                )
                email_msg.attach_alternative(html_body, "text/html")
                email_msg.send(fail_silently=False)
                
                success_msg = 'Password reset instructions have been sent to your email. Please check your inbox and spam folder.'
                if is_ajax:
                    return JsonResponse({
                        'success': True,
                        'auth_method': 'email',
                        'message': success_msg
                    })
                messages.success(request, success_msg)
            except Exception as e:
                logger.error(f"Password reset email delivery error for {user.email}: {e}")
                # For security and user feedback
                fallback_msg = 'If an account exists with that email, password reset instructions have been sent.'
                if is_ajax:
                    return JsonResponse({
                        'success': True,
                        'auth_method': 'email',
                        'message': fallback_msg
                    })
                messages.success(request, fallback_msg)
        else:
            # Don't reveal whether user exists for security
            generic_msg = 'If an account exists with that email, password reset instructions have been sent.'
            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'auth_method': 'unknown',
                    'message': generic_msg
                })
            messages.success(request, generic_msg)
        
        return redirect('frontend:home')


class PasswordResetDoneView(TemplateView):
    """Password reset done view"""
    template_name = 'accounts/password_reset_done.html'


class PasswordResetConfirmView(View):
    """Password reset confirm view - handles setting new password"""
    template_name = 'frontend/password_reset_form.html'
    
    def get(self, request, uidb64, token):
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.http import urlsafe_base64_decode
        from django.utils.encoding import force_str
        
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None
        
        if user is not None and default_token_generator.check_token(user, token):
            # Show the password reset form
            return render(request, self.template_name, {
                'uidb64': uidb64,
                'token': token,
                'validlink': True
            })
        else:
            messages.error(request, 'The password reset link is invalid or has expired.')
            return redirect('frontend:home')
    
    def post(self, request, uidb64, token):
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.http import urlsafe_base64_decode
        from django.utils.encoding import force_str
        
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        
        if password != password2:
            messages.error(request, 'Passwords do not match!')
            return render(request, self.template_name, {
                'uidb64': uidb64,
                'token': token,
                'validlink': True
            })
        
        if len(password) < 8:
            messages.error(request, 'Password must be at least 8 characters long!')
            return render(request, self.template_name, {
                'uidb64': uidb64,
                'token': token,
                'validlink': True
            })
        
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            messages.error(request, 'Invalid password reset link.')
            return redirect('frontend:home')
        
        if user is not None and default_token_generator.check_token(user, token):
            user.set_password(password)
            user.save()
            messages.success(request, 'Your password has been reset successfully! You can now log in.')
            return redirect('frontend:home')
        else:
            messages.error(request, 'The password reset link is invalid or has expired.')
            return redirect('frontend:home')


class PasswordResetCompleteView(TemplateView):
    """Password reset complete view"""
    template_name = 'accounts/password_reset_complete.html'


class ProfileView(LoginRequiredMixin, DetailView):
    """User profile view"""
    model = User
    template_name = 'core/profile.html'
    context_object_name = 'profile_user'
    
    def get_object(self):
        return self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Try to pass school_slug for consistent navigation
        school_slug = getattr(self.request, 'school_slug', '')
        if not school_slug:
            referer = self.request.META.get('HTTP_REFERER', '')
            if '/school/' in referer:
                parts = referer.split('/school/')
                if len(parts) > 1:
                    slug_part = parts[1].split('/')[0]
                    if slug_part:
                        school_slug = slug_part
        if not school_slug:
            try:
                from tenants.models import School
                school = School.objects.filter(is_active=True).first()
                if school:
                    school_slug = school.slug
            except Exception:
                pass
        context['school_slug'] = school_slug
        return context

    def post(self, request, *args, **kwargs):
        user = request.user
        school_slug = getattr(request, 'school_slug', '')
        if not school_slug and request.META.get('HTTP_REFERER'):
            referer = request.META.get('HTTP_REFERER', '')
            if '/school/' in referer:
                parts = referer.split('/school/')
                if len(parts) > 1:
                    slug_part = parts[1].split('/')[0]
                    if slug_part:
                        school_slug = slug_part
        
        # 1. Update personal details
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        phone = request.POST.get('phone', '').strip()
        nav_layout = request.POST.get('navigation_layout', '')
        
        if first_name:
            user.first_name = first_name
        if last_name:
            user.last_name = last_name
        user.phone = phone
        if nav_layout in ['', 'sidebar', 'horizontal']:
            user.navigation_layout = nav_layout
            
        if 'avatar' in request.FILES:
            user.avatar = request.FILES['avatar']
            
        # 2. Check password change if any password field is entered
        old_password = request.POST.get('old_password', '').strip()
        new_password1 = request.POST.get('new_password1', '').strip()
        new_password2 = request.POST.get('new_password2', '').strip()
        
        password_changed = False
        if old_password or new_password1 or new_password2:
            if not old_password:
                messages.error(request, 'Please enter your current password to set a new password.')
                if school_slug:
                    return redirect('core:profile', school_slug=school_slug)
                return redirect('accounts:profile')
            if not user.check_password(old_password):
                messages.error(request, 'Current password is incorrect.')
                if school_slug:
                    return redirect('core:profile', school_slug=school_slug)
                return redirect('accounts:profile')
            if not new_password1:
                messages.error(request, 'Please enter a new password.')
                if school_slug:
                    return redirect('core:profile', school_slug=school_slug)
                return redirect('accounts:profile')
            if new_password1 != new_password2:
                messages.error(request, 'New passwords do not match.')
                if school_slug:
                    return redirect('core:profile', school_slug=school_slug)
                return redirect('accounts:profile')
            if len(new_password1) < 8:
                messages.error(request, 'New password must be at least 8 characters long.')
                if school_slug:
                    return redirect('core:profile', school_slug=school_slug)
                return redirect('accounts:profile')
            
            user.set_password(new_password1)
            password_changed = True
            
        try:
            user.save()
            if password_changed:
                update_session_auth_hash(request, user)
                messages.success(request, 'Profile and password updated successfully!')
            else:
                messages.success(request, 'Profile updated successfully!')
        except Exception as e:
            messages.error(request, f'Error updating profile: {str(e)}')
            
        if school_slug:
            return redirect('core:profile', school_slug=school_slug)
        return redirect('accounts:profile')


class ProfileEditView(LoginRequiredMixin, UpdateView):
    """Edit user profile"""
    model = User
    form_class = ProfileEditForm
    template_name = 'accounts/profile_edit.html'
    success_url = reverse_lazy('accounts:profile')
    
    def get_object(self):
        return self.request.user

    def get_success_url(self):
        school_slug = getattr(self.request, 'school_slug', '')

        if not school_slug and self.request.META.get('HTTP_REFERER'):
            referer = self.request.META.get('HTTP_REFERER', '')
            if '/school/' in referer:
                parts = referer.split('/school/')
                if len(parts) > 1:
                    slug_part = parts[1].split('/')[0]
                    if slug_part:
                        school_slug = slug_part

        if school_slug:
            return reverse_lazy('core:profile', kwargs={'school_slug': school_slug})

        return super().get_success_url()
    
    def form_valid(self, form):
        messages.success(self.request, 'Profile updated successfully!')
        return super().form_valid(form)


class ChangePasswordView(LoginRequiredMixin, View):
    """Change password view"""
    template_name = 'accounts/change_password.html'
    form_class = ChangePasswordForm
    
    def get_school_slug(self, request):
        """Get school slug from request or referer"""
        # Try to get from request attribute (set by middleware)
        school_slug = getattr(request, 'school_slug', '')
        
        # If not found, try to extract from referer URL
        if not school_slug and request.META.get('HTTP_REFERER'):
            referer = request.META.get('HTTP_REFERER', '')
            if '/school/' in referer:
                parts = referer.split('/school/')
                if len(parts) > 1:
                    slug_part = parts[1].split('/')[0]
                    if slug_part:
                        school_slug = slug_part
        
        return school_slug
    
    def get(self, request):
        # Redirect to profile page where the inline change-password form now lives
        school_slug = self.get_school_slug(request)
        if school_slug:
            return redirect('core:profile', school_slug=school_slug)
        return redirect('accounts:profile')
    
    def post(self, request):
        form = self.form_class(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Password changed successfully!')
            
            # Redirect back to profile page
            school_slug = self.get_school_slug(request)
            if school_slug:
                return redirect('core:profile', school_slug=school_slug)
            return redirect('accounts:profile')
        
        # Invalid form: surface errors via messages and redirect back to profile
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f"{field}: {error}")
        school_slug = self.get_school_slug(request)
        if school_slug:
            return redirect('core:profile', school_slug=school_slug)
        return redirect('accounts:profile')


class UserListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """List all users"""
    model = User
    template_name = 'accounts/user_list.html'
    context_object_name = 'users'
    paginate_by = 20
    
    def test_func(self):
        return self.request.user.is_school_admin or self.request.user.is_superadmin
    
    def get_queryset(self):
        queryset = User.objects.all()
        
        # Search
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(email__icontains=search) |
                Q(employee_id__icontains=search)
            )
        
        # Filter by role
        role = self.request.GET.get('role')
        if role:
            queryset = queryset.filter(role=role)
        
        return queryset


class UserDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    """User detail view"""
    model = User
    template_name = 'accounts/user_detail.html'
    context_object_name = 'user_obj'
    
    def test_func(self):
        return self.request.user.is_school_admin or self.request.user.is_superadmin


class UserCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    """Create new user"""
    model = User
    form_class = UserForm
    template_name = 'accounts/user_form.html'
    success_url = reverse_lazy('accounts:user_list')
    
    def test_func(self):
        return self.request.user.is_school_admin or self.request.user.is_superadmin
    
    def form_valid(self, form):
        password = form.cleaned_data.get('password1')
        self.object = form.save(commit=False)
        if not password:
            password = get_random_string(12)
            self.object.set_password(password)
        self.object.save()
        try:
            from core.notifications import NotificationService
            NotificationService.notify_user_created(self.object, self.request.user, password)
        except Exception as e:
            print(f"Error sending notification: {e}")
        messages.success(self.request, 'User created successfully!')
        return redirect(self.success_url)


class UserUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """Update user"""
    model = User
    form_class = UserForm
    template_name = 'accounts/user_form.html'
    success_url = reverse_lazy('accounts:user_list')
    
    def test_func(self):
        return self.request.user.is_school_admin or self.request.user.is_superadmin
    
    def form_valid(self, form):
        messages.success(self.request, 'User updated successfully!')
        return super().form_valid(form)


class UserDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """Delete user"""
    model = User
    template_name = 'accounts/user_confirm_delete.html'
    success_url = reverse_lazy('accounts:user_list')
    
    def test_func(self):
        return self.request.user.is_school_admin or self.request.user.is_superadmin
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'User deleted successfully!')
        return super().delete(request, *args, **kwargs)


class ToggleUserStatusView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Toggle user active status"""
    
    def test_func(self):
        return self.request.user.is_school_admin or self.request.user.is_superadmin
    
    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        user.is_active = not user.is_active
        user.save()
        
        status = 'activated' if user.is_active else 'deactivated'
        messages.success(request, f'User {status} successfully!')
        
        return redirect('accounts:user_list')


class RoleListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """List all roles"""
    model = Role
    template_name = 'accounts/role_list.html'
    context_object_name = 'roles'
    
    def test_func(self):
        return self.request.user.is_school_admin or self.request.user.is_superadmin


class RoleCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    """Create new role"""
    model = Role
    form_class = RoleForm
    template_name = 'accounts/role_form.html'
    success_url = reverse_lazy('accounts:role_list')
    
    def test_func(self):
        return self.request.user.is_school_admin or self.request.user.is_superadmin
    
    def form_valid(self, form):
        messages.success(self.request, 'Role created successfully!')
        return super().form_valid(form)


class RoleUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """Update role"""
    model = Role
    form_class = RoleForm
    template_name = 'accounts/role_form.html'
    success_url = reverse_lazy('accounts:role_list')
    
    def test_func(self):
        return self.request.user.is_school_admin or self.request.user.is_superadmin
    
    def form_valid(self, form):
        messages.success(self.request, 'Role updated successfully!')
        return super().form_valid(form)


class RoleDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """Delete role"""
    model = Role
    template_name = 'accounts/role_confirm_delete.html'
    success_url = reverse_lazy('accounts:role_list')
    
    def test_func(self):
        return self.request.user.is_school_admin or self.request.user.is_superadmin


class PermissionListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """List all permissions"""
    model = Permission
    template_name = 'accounts/permission_list.html'
    context_object_name = 'permissions'
    
    def test_func(self):
        return self.request.user.is_school_admin or self.request.user.is_superadmin


class PermissionCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    """Create new permission"""
    model = Permission
    form_class = PermissionForm
    template_name = 'accounts/permission_form.html'
    success_url = reverse_lazy('accounts:permission_list')
    
    def test_func(self):
        return self.request.user.is_school_admin or self.request.user.is_superadmin


class PermissionUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """Update permission"""
    model = Permission
    form_class = PermissionForm
    template_name = 'accounts/permission_form.html'
    success_url = reverse_lazy('accounts:permission_list')
    
    def test_func(self):
        return self.request.user.is_school_admin or self.request.user.is_superadmin


class PermissionDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """Delete permission"""
    model = Permission
    template_name = 'accounts/permission_confirm_delete.html'
    success_url = reverse_lazy('accounts:permission_list')
    
    def test_func(self):
        return self.request.user.is_school_admin or self.request.user.is_superadmin


class LoginLogListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """List login logs"""
    model = UserLoginLog
    template_name = 'accounts/login_logs.html'
    context_object_name = 'logs'
    paginate_by = 50
    
    def test_func(self):
        return self.request.user.is_school_admin or self.request.user.is_superadmin
    
    def get_queryset(self):
        queryset = UserLoginLog.objects.select_related('user')
        
        # Filter by user if specified
        user_id = self.request.GET.get('user')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        return queryset


class ToggleNavigationLayoutView(LoginRequiredMixin, View):
    """Allow user to toggle or set their navigation layout preference."""

    def get(self, request, *args, **kwargs):
        return self._handle_layout_change(request)

    def post(self, request, *args, **kwargs):
        return self._handle_layout_change(request)

    def _handle_layout_change(self, request):
        user = request.user
        target_layout = request.GET.get('layout') or request.POST.get('layout')

        if target_layout in ['sidebar', 'horizontal', 'default']:
            if target_layout == 'default':
                user.navigation_layout = ''
            else:
                user.navigation_layout = target_layout
        else:
            # Toggle between sidebar and horizontal
            current = user.get_navigation_layout()
            user.navigation_layout = 'horizontal' if current == 'sidebar' else 'sidebar'

        user.save(update_fields=['navigation_layout'])

        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('ajax') == 'true':
            return JsonResponse({
                'success': True,
                'navigation_layout': user.get_navigation_layout(),
                'user_preference': user.navigation_layout,
            })

        redirect_url = request.META.get('HTTP_REFERER') or '/'
        return redirect(redirect_url)

