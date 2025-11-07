from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Count, Sum, Q
from django.contrib import messages
from django.urls import reverse_lazy
from django.core.mail import send_mail
from django.conf import settings
from django.utils.crypto import get_random_string
from tenants.models import School
from subscriptions.models import Subscription, Payment, SubscriptionPlan
from accounts.models import User


class SuperAdminRequiredMixin(UserPassesTestMixin):
    """Mixin to require super admin access"""
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.role == 'superadmin'  # Fixed: was 'super_admin'
    
    def handle_no_permission(self):
        messages.error(self.request, 'You do not have permission to access this page.')
        return redirect('frontend:home')


class DashboardView(SuperAdminRequiredMixin, TemplateView):
    """Super Admin Dashboard"""
    template_name = 'superadmin/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get comprehensive statistics
        from students.models import Student
        
        total_students = Student.objects.filter(is_active=True).count()
        total_teachers = User.objects.filter(role='teacher', is_active=True).count()
        total_admins = User.objects.filter(role='admin', is_active=True).count()
        
        context['stats'] = {
            'total_schools': School.objects.count(),
            'active_schools': School.objects.filter(is_active=True).count(),
            'inactive_schools': School.objects.filter(is_active=False).count(),
            'trial_schools': School.objects.filter(is_trial=True, is_active=True).count(),
            'total_students': total_students,
            'total_teachers': total_teachers,
            'total_admins': total_admins,
            'total_revenue': Payment.objects.filter(status='completed').aggregate(
                total=Sum('amount')
            )['total'] or 0,
            'pending_payments': Payment.objects.filter(status='pending').count(),
        }
        
        # Get recent schools
        context['recent_schools'] = School.objects.all().order_by('-created_on')[:5]
        
        # Get recent subscriptions
        context['recent_subscriptions'] = Subscription.objects.select_related(
            'school', 'plan'
        ).order_by('-created_at')[:5]
        
        # Get subscription plans
        context['plans'] = SubscriptionPlan.objects.filter(is_active=True)
        
        return context


class SchoolListView(SuperAdminRequiredMixin, ListView):
    """List all schools"""
    model = School
    template_name = 'superadmin/school_list.html'
    context_object_name = 'schools'
    paginate_by = 20
    ordering = ['-created_on']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.GET.get('search')
        status = self.request.GET.get('status')
        
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | 
                Q(slug__icontains=search) |
                Q(email__icontains=search)
            )
        
        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)
        elif status == 'trial':
            queryset = queryset.filter(is_trial=True)
        
        return queryset


class SchoolDetailView(SuperAdminRequiredMixin, DetailView):
    """View school details"""
    model = School
    template_name = 'superadmin/school_detail.html'
    context_object_name = 'school'


class SubscriptionListView(SuperAdminRequiredMixin, ListView):
    """List all subscriptions"""
    model = Subscription
    template_name = 'superadmin/subscription_list.html'
    context_object_name = 'subscriptions'
    paginate_by = 20
    ordering = ['-created_at']


class SchoolCreateView(SuperAdminRequiredMixin, CreateView):
    """Create a new school with admin"""
    model = School
    template_name = 'superadmin/school_form.html'
    fields = ['name', 'slug', 'email', 'phone', 'address', 'city', 'state', 'country', 
              'postal_code', 'website', 'is_active', 'is_trial', 'trial_end_date']
    success_url = reverse_lazy('superadmin:schools')
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Add Bootstrap classes to form fields
        form.fields['name'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Enter school name'})
        form.fields['slug'].widget.attrs.update({'class': 'form-control', 'placeholder': 'e.g., demo-school'})
        form.fields['email'].widget.attrs.update({'class': 'form-control', 'placeholder': 'school@example.com'})
        form.fields['phone'].widget.attrs.update({'class': 'form-control', 'placeholder': '+254 xxx xxx xxx'})
        form.fields['address'].widget.attrs.update({'class': 'form-control', 'rows': 3})
        form.fields['city'].widget.attrs.update({'class': 'form-control'})
        form.fields['state'].widget.attrs.update({'class': 'form-control'})
        form.fields['country'].widget.attrs.update({'class': 'form-control'})
        form.fields['postal_code'].widget.attrs.update({'class': 'form-control'})
        form.fields['website'].widget.attrs.update({'class': 'form-control', 'placeholder': 'https://school.com'})
        form.fields['is_active'].widget.attrs.update({'class': 'form-check-input'})
        form.fields['is_trial'].widget.attrs.update({'class': 'form-check-input'})
        form.fields['trial_end_date'].widget.attrs.update({'class': 'form-control', 'type': 'date'})
        return form
    
    def form_valid(self, form):
        response = super().form_valid(form)
        school = self.object
        
        # Check if admin creation requested
        if self.request.POST.get('create_admin') == 'yes':
            admin_email = self.request.POST.get('admin_email')
            admin_first_name = self.request.POST.get('admin_first_name')
            admin_last_name = self.request.POST.get('admin_last_name')
            
            if admin_email and admin_first_name and admin_last_name:
                # Generate random password
                password = get_random_string(12)
                
                # Create admin user
                try:
                    admin_user = User.objects.create_user(
                        email=admin_email,
                        first_name=admin_first_name,
                        last_name=admin_last_name,
                        role='admin',
                        is_active=True,
                        password=password
                    )
                    
                    # Send email with credentials
                    self.send_admin_credentials_email(
                        admin_user, password, school
                    )
                    
                    messages.success(
                        self.request, 
                        f'School "{school.name}" created successfully! '
                        f'Admin account created for {admin_email} and login credentials sent via email.'
                    )
                except Exception as e:
                    messages.warning(
                        self.request, 
                        f'School created but admin account creation failed: {str(e)}'
                    )
            else:
                messages.success(self.request, f'School "{school.name}" created successfully!')
        else:
            messages.success(self.request, f'School "{school.name}" created successfully!')
        
        return response
    
    def send_admin_credentials_email(self, user, password, school):
        """Send login credentials to new school admin"""
        subject = f'Welcome to {school.name} - School Management System'
        message = f"""Hello {user.get_full_name()},

Your school administrator account has been created for {school.name}.

Login Details:
- URL: {settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else 'your-domain.com'}/accounts/login/
- Email: {user.email}
- Password: {password}
- School Slug: {school.slug}

Please login and change your password immediately.

Your dashboard URL: https://{settings.ALLOWED_HOSTS[0]}/school/{school.slug}/

Best regards,
School Management System Team
"""
        
        try:
            send_mail(
                subject,
                message,
                settings.EMAIL_HOST_USER,
                [user.email],
                fail_silently=False,
            )
        except Exception as e:
            messages.warning(self.request, f'Email sending failed: {str(e)}')


class SchoolUpdateView(SuperAdminRequiredMixin, UpdateView):
    """Update school details"""
    model = School
    template_name = 'superadmin/school_form.html'
    fields = ['name', 'email', 'phone', 'address', 'city', 'state', 'country', 
              'postal_code', 'website', 'is_active', 'is_trial', 'trial_end_date']
    success_url = reverse_lazy('superadmin:schools')
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Add Bootstrap classes to form fields
        form.fields['name'].widget.attrs.update({'class': 'form-control'})
        form.fields['email'].widget.attrs.update({'class': 'form-control'})
        form.fields['phone'].widget.attrs.update({'class': 'form-control'})
        form.fields['address'].widget.attrs.update({'class': 'form-control', 'rows': 3})
        form.fields['city'].widget.attrs.update({'class': 'form-control'})
        form.fields['state'].widget.attrs.update({'class': 'form-control'})
        form.fields['country'].widget.attrs.update({'class': 'form-control'})
        form.fields['postal_code'].widget.attrs.update({'class': 'form-control'})
        form.fields['website'].widget.attrs.update({'class': 'form-control'})
        form.fields['is_active'].widget.attrs.update({'class': 'form-check-input'})
        form.fields['is_trial'].widget.attrs.update({'class': 'form-check-input'})
        form.fields['trial_end_date'].widget.attrs.update({'class': 'form-control', 'type': 'date'})
        return form
    
    def form_valid(self, form):
        messages.success(self.request, f'School "{self.object.name}" updated successfully!')
        return super().form_valid(form)


class SchoolDeleteView(SuperAdminRequiredMixin, DeleteView):
    """Delete a school"""
    model = School
    template_name = 'superadmin/school_confirm_delete.html'
    success_url = reverse_lazy('superadmin:schools')
    
    def delete(self, request, *args, **kwargs):
        school_name = self.get_object().name
        response = super().delete(request, *args, **kwargs)
        messages.success(request, f'School "{school_name}" deleted successfully!')
        return response


class AdminUserListView(SuperAdminRequiredMixin, ListView):
    """List all school admins"""
    template_name = 'superadmin/admin_list.html'
    context_object_name = 'admins'
    paginate_by = 20
    
    def get_queryset(self):
        return User.objects.filter(role='admin').order_by('-created_at')


class AdminUserCreateView(SuperAdminRequiredMixin, CreateView):
    """Create a new school admin"""
    model = User
    template_name = 'superadmin/admin_form.html'
    fields = ['email', 'first_name', 'last_name', 'phone']
    success_url = reverse_lazy('superadmin:admins')
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Add Bootstrap classes to form fields
        form.fields['email'].widget.attrs.update({'class': 'form-control', 'placeholder': 'admin@example.com'})
        form.fields['first_name'].widget.attrs.update({'class': 'form-control', 'placeholder': 'First Name'})
        form.fields['last_name'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Last Name'})
        form.fields['phone'].widget.attrs.update({'class': 'form-control', 'placeholder': '+254 xxx xxx xxx'})
        return form
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['schools'] = School.objects.filter(is_active=True)
        return context
    
    def form_valid(self, form):
        # Generate random password
        password = get_random_string(12)
        
        # Create user
        user = form.save(commit=False)
        user.role = 'admin'
        user.is_active = True
        user.set_password(password)
        user.save()
        
        # Get selected school
        school_id = self.request.POST.get('school')
        school = get_object_or_404(School, id=school_id) if school_id else None
        
        # Send email
        if school:
            self.send_admin_credentials_email(user, password, school)
            messages.success(
                self.request, 
                f'Admin account created for {user.email} and credentials sent via email!'
            )
        else:
            messages.success(self.request, f'Admin account created for {user.email}!')
        
        return redirect(self.success_url)
    
    def send_admin_credentials_email(self, user, password, school):
        """Send login credentials to new admin"""
        subject = f'School Admin Account Created - {school.name}'
        message = f"""Hello {user.get_full_name()},

Your school administrator account has been created for {school.name}.

Login Details:
- URL: https://{settings.ALLOWED_HOSTS[0]}/accounts/login/
- Email: {user.email}
- Password: {password}
- School: {school.name}
- School Slug: {school.slug}

Dashboard: https://{settings.ALLOWED_HOSTS[0]}/school/{school.slug}/

Please login and change your password immediately.

Best regards,
School Management System Team
"""
        
        try:
            send_mail(
                subject,
                message,
                settings.EMAIL_HOST_USER,
                [user.email],
                fail_silently=False,
            )
        except Exception as e:
            messages.warning(self.request, f'Email sending failed: {str(e)}')
