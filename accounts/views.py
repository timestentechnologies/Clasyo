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
    """User login view"""
    template_name = 'accounts/login.html'
    form_class = LoginForm
    
    def get(self, request):
        # Redirect if already authenticated
        if request.user.is_authenticated:
            if request.user.role == 'super_admin':
                return redirect('superadmin:dashboard')
            else:
                from tenants.models import School
                school = School.objects.filter(is_active=True).first()
                if school:
                    return redirect('core:dashboard', school_slug=school.slug)
                return redirect('frontend:home')
        
        form = self.form_class()
        return render(request, self.template_name, {'form': form})
    
    def post(self, request):
        form = self.form_class(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            user = authenticate(request, email=email, password=password)
            
            if user is not None:
                if user.is_active:
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
                    
                    messages.success(request, f'Welcome back, {user.get_full_name()}!')
                    
                    # Check if there's a next URL parameter
                    next_url = request.GET.get('next')
                    
                    # Super admin ALWAYS goes to super admin dashboard (ignore next URL)
                    if user.role == 'super_admin':
                        return redirect('superadmin:dashboard')
                    
                    # For other roles, use next URL if provided
                    if next_url:
                        return redirect(next_url)
                    
                    # Other roles need a school - get from user's school or demo school
                    from tenants.models import School
                    try:
                        # Try to get demo school or first active school
                        school = School.objects.filter(is_active=True).first()
                        if school:
                            return redirect('core:dashboard', school_slug=school.slug)
                        else:
                            messages.error(request, 'No active school found. Please contact administrator.')
                            return redirect('frontend:home')
                    except Exception as e:
                        messages.error(request, 'Error finding school. Please contact administrator.')
                        return redirect('frontend:home')
                else:
                    messages.error(request, 'Your account is inactive. Please contact the administrator.')
            else:
                messages.error(request, 'Invalid email or password.')
        
        return render(request, self.template_name, {'form': form})


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
        
        logout(request)
        messages.success(request, 'You have been logged out successfully.')
        return redirect('accounts:login')


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
            user.save()
            
            messages.success(request, 'Registration successful! Please login.')
            return redirect('accounts:login')
        
        return render(request, self.template_name, {'form': form})


class PasswordResetView(TemplateView):
    """Password reset view"""
    template_name = 'accounts/password_reset.html'


class PasswordResetDoneView(TemplateView):
    """Password reset done view"""
    template_name = 'accounts/password_reset_done.html'


class PasswordResetConfirmView(TemplateView):
    """Password reset confirm view"""
    template_name = 'accounts/password_reset_confirm.html'


class PasswordResetCompleteView(TemplateView):
    """Password reset complete view"""
    template_name = 'accounts/password_reset_complete.html'


class ProfileView(LoginRequiredMixin, DetailView):
    """User profile view"""
    model = User
    template_name = 'accounts/profile.html'
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
    
    def form_valid(self, form):
        messages.success(self.request, 'Profile updated successfully!')
        return super().form_valid(form)


class ChangePasswordView(LoginRequiredMixin, View):
    """Change password view"""
    template_name = 'accounts/change_password.html'
    form_class = ChangePasswordForm
    
    def get(self, request):
        form = self.form_class(request.user)
        return render(request, self.template_name, {'form': form})
    
    def post(self, request):
        form = self.form_class(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Password changed successfully!')
            return redirect('accounts:profile')
        
        return render(request, self.template_name, {'form': form})


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
