from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import View, ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.urls import reverse_lazy
from django.utils import timezone
from django.db.models import Q
from .models import User, Role, Permission, UserLoginLog
from .forms import LoginForm, UserRegistrationForm, ProfileEditForm, ChangePasswordForm, UserForm, RoleForm, PermissionForm


class LoginView(View):
    """User login view - redirects to home page with login modal"""
    template_name = 'frontend/home.html'
    form_class = LoginForm
    
    def get(self, request):
        # Redirect if already authenticated
        if request.user.is_authenticated:
            messages.info(request, f'You are already logged in as {request.user.email}. Logout first to login with a different account.')
            
            if request.user.role == 'superadmin':  # Fixed: was 'super_admin'
                return redirect('superadmin:dashboard')
            else:
                from tenants.models import School
                school = School.objects.filter(is_active=True).first()
                if school:
                    return redirect('core:apps_home', school_slug=school.slug)
                
                # If no school exists, show helpful message
                messages.warning(request, 'No active school found. Please contact administrator or logout.')
                return redirect('frontend:home')
        
        # For unauthenticated users, show home page with login modal
        messages.info(request, 'Please use the login modal to sign in.')
        return redirect('frontend:home')
    
    def post(self, request):
        form = self.form_class(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            user = authenticate(request, email=email, password=password)
            
            if user is not None:
                if user.is_active:
                    # Clear any stale impersonation session data before login
                    if 'impersonated_user_id' in request.session:
                        del request.session['impersonated_user_id']
                    if 'original_user_id' in request.session:
                        del request.session['original_user_id']
                    
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
                    
                    # Check if there's a next URL parameter in GET or POST
                    next_url = request.GET.get('next') or request.POST.get('next')
                    
                    # Super admin ALWAYS goes to super admin dashboard (ignore next URL)
                    if user.role == 'superadmin':
                        messages.success(request, f'Welcome back, {user.get_full_name()}!')
                        return redirect('superadmin:dashboard')
                    
                    # For other roles, use next URL if provided
                    if next_url and next_url.startswith('/'):
                        messages.success(request, f'Welcome back, {user.get_full_name()}!')
                        return redirect(next_url)
                    
                    # Other roles need a school - get from user's school or first active school
                    from tenants.models import School
                    
                    # Get the school associated with the user or first active school
                    school = School.objects.filter(is_active=True).first()
                    
                    if school:
                        # Redirect to apps home page
                        messages.success(request, f'Welcome back, {user.get_full_name()}!')
                        return redirect('core:apps_home', school_slug=school.slug)
                    else:
                        # No school found - stay on home page with message
                        messages.warning(request, f'Welcome {user.get_full_name()}! No school associated with your account. Please contact administrator.')
                        return redirect('frontend:home')
                else:
                    messages.error(request, 'Your account is inactive. Please contact the administrator.')
                    return redirect('frontend:home')
            else:
                messages.error(request, 'Invalid email or password.')
                return redirect('frontend:home')
        else:
            # Form validation failed
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
            return redirect('frontend:home')


class LogoutView(LoginRequiredMixin, View):
    """User logout view"""
    def get(self, request):
        # Update logout time in login log
        last_log = UserLoginLog.objects.filter(
            user=request.user,
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
        
        logout(request)
        messages.success(request, 'You have been logged out successfully.')
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
            raw_password = form.cleaned_data.get('password')
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

        # Super admin: always go to superadmin dashboard
        if user.role == 'superadmin':
            messages.success(request, f'Welcome back, {user.get_full_name()}!')
            return redirect('superadmin:dashboard')

        # For other roles, redirect to first active school apps home (same as LoginView)
        from tenants.models import School
        school = School.objects.filter(is_active=True).first()

        if school:
            messages.success(request, f'Welcome back, {user.get_full_name()}!')
            return redirect('core:apps_home', school_slug=school.slug)

        # No school associated
        messages.warning(
            request,
            f'Welcome {user.get_full_name()}! No school associated with your account. Please contact administrator.',
        )
        return redirect('frontend:home')


class PasswordResetView(View):
    """Password reset request view - handles sending reset emails"""
    
    def post(self, request):
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes
        from django.template.loader import render_to_string
        from django.core.mail import send_mail
        from django.conf import settings
        
        email = request.POST.get('email')
        
        try:
            user = User.objects.get(email=email)
            
            # Generate password reset token
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            
            # Build reset URL
            reset_url = request.build_absolute_uri(
                f'/accounts/password-reset/confirm/{uid}/{token}/'
            )
            
            # Send email (you'll need to configure email settings)
            subject = 'Password Reset Request - Clasyo'
            message = f'''
Hello {user.get_full_name()},

You have requested to reset your password. Click the link below to reset it:

{reset_url}

If you didn't request this, please ignore this email.

Best regards,
Clasyo Team
            '''
            
            try:
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                    fail_silently=False,
                )
                messages.success(request, 'Password reset instructions have been sent to your email.')
            except Exception as e:
                # If email fails, still show success message for security
                messages.success(request, 'If an account exists with that email, password reset instructions have been sent.')
                
        except User.DoesNotExist:
            # Don't reveal if user exists or not for security
            messages.success(request, 'If an account exists with that email, password reset instructions have been sent.')
        
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
        form = self.form_class(request.user)
        context = {
            'form': form,
            'school_slug': self.get_school_slug(request)
        }
        return render(request, self.template_name, context)
    
    def post(self, request):
        form = self.form_class(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Password changed successfully!')
            
            # Redirect back to referer or dashboard
            referer = request.META.get('HTTP_REFERER', '')
            if referer and '/school/' in referer:
                return redirect(referer)
            
            school_slug = self.get_school_slug(request)
            if school_slug:
                return redirect('core:dashboard', school_slug=school_slug)
            
            return redirect('frontend:home')
        
        context = {
            'form': form,
            'school_slug': self.get_school_slug(request)
        }
        return render(request, self.template_name, context)


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
        messages.success(self.request, 'User created successfully!')
        return super().form_valid(form)


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
