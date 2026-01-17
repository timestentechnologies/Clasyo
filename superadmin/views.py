from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, CreateView, UpdateView, DetailView, DeleteView, View, TemplateView
from django.urls import reverse_lazy
from django.db.models import Count, Q, Sum
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
import csv
from django.conf import settings
from django.core.mail import send_mail
from django.utils.crypto import get_random_string
from django import forms
from .models import (
    PaymentConfiguration,
    SchoolPaymentConfiguration,
    GlobalSMSConfiguration,
    GlobalEmailConfiguration,
    GlobalDatabaseConfiguration,
    SchoolSMSConfiguration,
    SchoolEmailConfiguration,
    GlobalAIConfiguration,
    SchoolAIConfiguration,
)
from .forms import PaymentConfigurationForm, SchoolPaymentConfigurationForm
from .ai_forms import GlobalAIConfigurationForm, SchoolAIConfigurationForm
from tenants.models import School
from accounts.models import User
from subscriptions.models import SubscriptionPlan, Subscription, Payment, Invoice
from core.models import AuditLog


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
        
        # Use total rows to avoid misreporting when is_active isn't set consistently
        total_students = Student.objects.count()
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
        
        # Get recent schools with accurate student counts (union of class.school, user.school, and created_by.school)
        recent = list(School.objects.order_by('-created_on')[:5])
        try:
            for s in recent:
                context_count = Student.objects.filter(
                    Q(current_class__school=s) | Q(user__school=s) | Q(created_by__school=s)
                ).distinct().count()
                setattr(s, 'student_count', context_count)
        except Exception:
            for s in recent:
                setattr(s, 'student_count', 0)
        context['recent_schools'] = recent
        
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
        institution_type = self.request.GET.get('institution_type')
        
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
        
        if institution_type:
            queryset = queryset.filter(institution_type=institution_type)
        
        # Annotate with accurate student counts per school
        from django.db.models import Count
        queryset = queryset.annotate(
            student_count=Count('classes__students', distinct=True)
        )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['institution_type_choices'] = School.INSTITUTION_TYPE_CHOICES
        context['selected_institution_type'] = self.request.GET.get('institution_type', '')
        # Attach accurate student counts per school for current page
        try:
            from students.models import Student
            schools = list(context.get('schools') or [])
            for s in schools:
                s.student_count = Student.objects.filter(
                    Q(current_class__school=s) | Q(user__school=s) | Q(created_by__school=s)
                ).distinct().count()
            # Replace the queryset in context so template uses enriched objects
            context['schools'] = schools
        except Exception:
            pass
        return context


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
    
    def get_queryset(self):
        queryset = super().get_queryset().select_related('school', 'plan')
        status_filter = self.request.GET.get('status')
        
        if status_filter and status_filter != 'all':
            if status_filter == 'trial':
                queryset = queryset.filter(is_trial=True)
            else:
                queryset = queryset.filter(status=status_filter)
        
        return queryset


class SubscriptionEditView(SuperAdminRequiredMixin, View):
    """Edit subscription details"""
    
    def post(self, request):
        subscription_id = request.POST.get('subscription_id')
        subscription = get_object_or_404(Subscription, id=subscription_id)
        
        try:
            # Update subscription fields
            subscription.start_date = request.POST.get('start_date')
            subscription.end_date = request.POST.get('end_date')
            subscription.status = request.POST.get('status')
            subscription.is_trial = request.POST.get('is_trial') == 'on'
            
            subscription.save()
            
            messages.success(request, f'Subscription for {subscription.school.name} updated successfully!')
            
        except Exception as e:
            messages.error(request, f'Error updating subscription: {str(e)}')
        
        return redirect('superadmin:subscriptions')


class SchoolCreateView(SuperAdminRequiredMixin, CreateView):
    """Create a new school with admin"""
    model = School
    template_name = 'superadmin/school_form.html'
    fields = ['name', 'slug', 'email', 'phone', 'address', 'city', 'state', 'country', 
              'postal_code', 'website', 'institution_type', 'is_active', 'is_trial', 'trial_end_date']
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
        form.fields['institution_type'].widget.attrs.update({'class': 'form-select'})
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
                    # Link admin to this school
                    admin_user.school = school
                    admin_user.save(update_fields=['school'])
                    
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
              'postal_code', 'website', 'institution_type', 'is_active', 'is_trial', 'trial_end_date']
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
        form.fields['institution_type'].widget.attrs.update({'class': 'form-select'})
        form.fields['is_active'].widget.attrs.update({'class': 'form-check-input'})
        form.fields['is_trial'].widget.attrs.update({'class': 'form-check-input'})
        form.fields['trial_end_date'].widget.attrs.update({'class': 'form-control', 'type': 'date'})
        return form
    
    def form_valid(self, form):
        messages.success(self.request, f'School "{self.object.name}" updated successfully!')
        return super().form_valid(form)


class SchoolDeleteView(SuperAdminRequiredMixin, DeleteView):
    """Delete a school and all related data"""
    model = School
    template_name = 'superadmin/school_confirm_delete.html'
    success_url = reverse_lazy('superadmin:schools')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        school = self.get_object()
        
        # Count related objects
        from students.models import Student
        from academics.models import Class, Subject
        from library.models import Book
        from fees.models import FeeStructure
        from examinations.models import Exam
        
        context['counts'] = {
            'students': Student.objects.filter(current_class__school=school).count(),
            'parents': User.objects.filter(role='parent', children__current_class__school=school).distinct().count(),
            'teachers': User.objects.filter(role='teacher').count(),
            'classes': Class.objects.filter(school=school).count(),
            'subjects': Subject.objects.filter(school=school).count(),
            'books': Book.objects.filter(school=school).count(),
            'fees': FeeStructure.objects.filter(class_name__school=school).count(),
            'exams': Exam.objects.filter(Q(class_assigned__school=school) | Q(subject__school=school)).distinct().count(),
        }
        return context
    
    def delete(self, request, *args, **kwargs):
        school = self.get_object()
        school_name = school.name
        
        # Django will handle cascading deletes for ForeignKey with on_delete=CASCADE
        # But we'll explicitly delete to ensure cleanup
        from students.models import Student
        from academics.models import Class, Subject
        from library.models import Book, BookIssue
        from fees.models import FeeStructure, FeeCollection
        from examinations.models import Exam
        from attendance.models import StudentAttendance, StaffAttendance
        
        
        try:
            # Delete related data
            Student.objects.filter(current_class__school=school).delete()
            User.objects.filter(role='parent', children__current_class__school=school).distinct().delete()
            Class.objects.filter(school=school).delete()
            Subject.objects.filter(school=school).delete()
            Book.objects.filter(school=school).delete()
            BookIssue.objects.filter(book__school=school).delete()
            FeeStructure.objects.filter(class_name__school=school).delete()
            FeeCollection.objects.filter(fee_structure__class_name__school=school).delete()
            Exam.objects.filter(Q(class_assigned__school=school) | Q(subject__school=school)).delete()
            StudentAttendance.objects.filter(school=school).delete()
            StaffAttendance.objects.filter(school=school).delete()
            
            # Delete school admins (users with admin role) and notify them by email
            # Only admins linked to this school are affected
            admin_users = list(User.objects.filter(role='admin', school=school))
            for admin in admin_users:
                try:
                    subject = f'Your administrator account for {school_name} has been deleted'
                    message = (
                        f'Hello {admin.get_full_name()},\n\n'
                        f'This is to inform you that the school "{school_name}" has been deleted from our system. '
                        f'As a result, your administrator account associated with this school has been deleted.\n\n'
                        f'If you believe this was a mistake or need assistance, please contact support.\n\n'
                        f'Best regards,\n'
                        f'Clasyo Team'
                    )
                    send_mail(
                        subject,
                        message,
                        settings.DEFAULT_FROM_EMAIL,
                        [admin.email],
                        fail_silently=True,
                    )
                except Exception:
                    # Continue even if email fails
                    pass
            if admin_users:
                User.objects.filter(id__in=[u.id for u in admin_users]).delete()
            
            # Delete subscriptions related to the school
            Subscription.objects.filter(school=school).delete()
            
            # Finally delete the school
            response = super().delete(request, *args, **kwargs)
            messages.success(request, f'School "{school_name}" and all related data deleted successfully!')
            return response
        except Exception as e:
            messages.error(request, f'Error deleting school: {str(e)}')
            return redirect('superadmin:schools')


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
        if school:
            # Link admin user to the selected school
            user.school = school
            user.save(update_fields=['school'])
        
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


class AdminUserUpdateView(SuperAdminRequiredMixin, UpdateView):
    """Update school admin details"""
    model = User
    template_name = 'superadmin/admin_edit.html'
    context_object_name = 'admin_user'
    fields = ['email', 'first_name', 'last_name', 'phone', 'is_active', 'school']
    success_url = reverse_lazy('superadmin:admins')
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Add Bootstrap classes to form fields
        form.fields['email'].widget.attrs.update({'class': 'form-control'})
        form.fields['first_name'].widget.attrs.update({'class': 'form-control'})
        form.fields['last_name'].widget.attrs.update({'class': 'form-control'})
        form.fields['phone'].widget.attrs.update({'class': 'form-control'})
        form.fields['is_active'].widget.attrs.update({'class': 'form-check-input'})
        if 'school' in form.fields:
            form.fields['school'].widget.attrs.update({'class': 'form-select'})
        return form
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['schools'] = School.objects.filter(is_active=True)
        return context
    
    def form_valid(self, form):
        messages.success(self.request, f'Admin "{self.object.get_full_name()}" updated successfully!')
        return super().form_valid(form)


class AdminUserDeleteView(SuperAdminRequiredMixin, DeleteView):
    """Delete a school admin and also delete their school and all related data"""
    model = User
    template_name = 'superadmin/admin_confirm_delete.html'
    context_object_name = 'admin_user'
    success_url = reverse_lazy('superadmin:admins')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        admin_user = self.get_object()
        context['available_schools'] = School.objects.filter(is_active=True).order_by('name')
        context['linked_school'] = getattr(admin_user, 'school', None)
        return context

    def delete(self, request, *args, **kwargs):
        admin_user = self.get_object()
        if admin_user.role != 'admin':
            messages.error(request, 'Selected user is not a school admin.')
            return redirect('superadmin:admins')

        school = getattr(admin_user, 'school', None)
        # If admin is not linked to a school, allow superadmin to choose one to delete
        if not school:
            school_id = request.POST.get('school_id')
            if school_id:
                school = get_object_or_404(School, id=school_id)
        school_name = school.name if school else None

        # If school exists, perform full school cleanup similar to SchoolDeleteView
        if school:
            from students.models import Student
            from academics.models import Class, Subject
            from library.models import Book, BookIssue
            from fees.models import FeeStructure, FeeCollection
            from examinations.models import Exam
            from attendance.models import StudentAttendance, StaffAttendance

            try:
                # Delete related data
                Student.objects.filter(current_class__school=school).delete()
                User.objects.filter(role='parent', children__current_class__school=school).distinct().delete()
                Class.objects.filter(school=school).delete()
                Subject.objects.filter(school=school).delete()
                Book.objects.filter(school=school).delete()
                BookIssue.objects.filter(book__school=school).delete()
                FeeStructure.objects.filter(class_name__school=school).delete()
                FeeCollection.objects.filter(fee_structure__class_name__school=school).delete()
                Exam.objects.filter(Q(class_assigned__school=school) | Q(subject__school=school)).delete()
                StudentAttendance.objects.filter(school=school).delete()
                StaffAttendance.objects.filter(school=school).delete()

                # Notify and delete all admins for this school (including selected admin)
                admins = list(User.objects.filter(role='admin', school=school))
                for adm in admins:
                    try:
                        subject = f'Your administrator account for {school_name} has been deleted'
                        message = (
                            f'Hello {adm.get_full_name()},\n\n'
                            f'The school "{school_name}" has been deleted from our system. '
                            f'As a result, your administrator account associated with this school has been deleted.\n\n'
                            f'If you need assistance, please contact support.\n\n'
                            f'Best regards,\n'
                            f'Clasyo Team'
                        )
                        send_mail(
                            subject,
                            message,
                            settings.DEFAULT_FROM_EMAIL,
                            [adm.email],
                            fail_silently=True,
                        )
                    except Exception:
                        pass

                if admins:
                    User.objects.filter(id__in=[u.id for u in admins]).delete()

                # Delete school subscriptions
                Subscription.objects.filter(school=school).delete()

                # Finally delete the school itself
                school.delete()

                messages.success(request, f'School "{school_name}" and all related data deleted. Admin account removed.')
            except Exception as e:
                messages.error(request, f'Error deleting admin and school: {str(e)}')
                return redirect('superadmin:admins')
        else:
            # No school linked or selected; just delete the admin
            try:
                admin_user.delete()
                messages.success(request, 'Admin account deleted successfully. No school was linked or selected to delete.')
            except Exception as e:
                messages.error(request, f'Error deleting admin: {str(e)}')
                return redirect('superadmin:admins')

        return redirect(self.success_url)


# Content Management Views
from frontend.models import FAQ, PageContent, ContactMessage
from django.views import View
from django import forms


class PricingPlanForm(forms.ModelForm):
    """Form for pricing plans"""
    class Meta:
        model = SubscriptionPlan
        fields = '__all__'
        widgets = {
            'features': forms.Textarea(attrs={'rows': 5, 'placeholder': 'Enter each feature on a new line'}),
        }


class FAQForm(forms.ModelForm):
    """Form for FAQs"""
    class Meta:
        model = FAQ
        fields = '__all__'
        widgets = {
            'question': forms.TextInput(attrs={'class': 'form-control'}),
            'answer': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'category': forms.TextInput(attrs={'class': 'form-control'}),
            'order': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class PageContentForm(forms.ModelForm):
    """Form for page content"""
    class Meta:
        model = PageContent
        fields = '__all__'
        widgets = {
            'content': forms.Textarea(attrs={'rows': 6}),
            'extra_data': forms.Textarea(attrs={'rows': 4, 'placeholder': '{"key": "value"}'}),
        }


class PricingManagementView(SuperAdminRequiredMixin, View):
    """Manage pricing plans"""
    template_name = 'superadmin/pricing_management.html'
    
    def get(self, request):
        plans = SubscriptionPlan.objects.all().order_by('display_order', 'price')
        form = PricingPlanForm()
        edit_id = request.GET.get('edit')
        edit_plan = None
        
        if edit_id:
            edit_plan = get_object_or_404(SubscriptionPlan, id=edit_id)
            form = PricingPlanForm(instance=edit_plan)
        
        return render(request, self.template_name, {
            'pricing_plans': plans,
            'form': form,
            'edit_plan': edit_plan
        })
    
    def post(self, request):
        plan_id = request.POST.get('plan_id')
        action = request.POST.get('action')
        
        if action == 'delete' and plan_id:
            plan = get_object_or_404(SubscriptionPlan, id=plan_id)
            plan_name = plan.name
            
            # Check if there are any subscriptions associated with this plan
            subscription_count = plan.subscriptions.count()
            if subscription_count > 0:
                messages.error(request, f'Cannot delete pricing plan "{plan_name}" because it is associated with {subscription_count} subscription(s). Please deactivate the plan instead.')
                return redirect('superadmin:pricing_management')
            
            try:
                plan.delete()
                messages.success(request, f'Pricing plan "{plan_name}" deleted successfully!')
            except Exception as e:
                messages.error(request, f'Error deleting pricing plan: {str(e)}')
            return redirect('superadmin:pricing_management')
        
        # Handle form submission for create/update
        if plan_id:
            plan = get_object_or_404(SubscriptionPlan, id=plan_id)
            success_msg = 'Pricing plan updated successfully!'
        else:
            plan = None
            success_msg = 'Pricing plan created successfully!'
        
        try:
            # Extract form data
            name = request.POST.get('name')
            slug = request.POST.get('slug')
            plan_type = request.POST.get('plan_type')
            description = request.POST.get('description', '')
            price = request.POST.get('price')
            billing_cycle = request.POST.get('billing_cycle')
            trial_days = request.POST.get('trial_days', '0')
            max_students = request.POST.get('max_students', '100')
            max_teachers = request.POST.get('max_teachers', '20')
            max_staff = request.POST.get('max_staff', '10')
            max_branches = 1
            storage_limit_gb = 5
            is_active = request.POST.get('is_active') == 'on'
            is_popular = request.POST.get('is_popular') == 'on'
            display_order = request.POST.get('display_order', '0')
            # New pricing components
            setup_fee = request.POST.get('setup_fee', '0')
            data_migration_fee = request.POST.get('data_migration_fee', '0')
            license_fee = request.POST.get('license_fee', '0')
            training_fee = request.POST.get('training_fee', '0')
            
            # Validate required fields
            if not name or not slug or not plan_type or not price or not billing_cycle:
                messages.error(request, 'Please fill in all required fields (Name, Slug, Plan Type, Price, and Billing Cycle).')
                return redirect('superadmin:pricing_management')
            
            # Convert to appropriate types
            try:
                if price:
                    price = float(price)
                if trial_days:
                    trial_days = int(trial_days)
                if max_students:
                    max_students = int(max_students)
                if max_teachers:
                    max_teachers = int(max_teachers)
                if max_staff:
                    max_staff = int(max_staff)
                if display_order:
                    display_order = int(display_order)
                if setup_fee:
                    setup_fee = float(setup_fee)
                if data_migration_fee:
                    data_migration_fee = float(data_migration_fee)
                if license_fee:
                    license_fee = float(license_fee)
                if training_fee:
                    training_fee = float(training_fee)
            except ValueError:
                messages.error(request, 'Please ensure all numeric fields contain valid numbers.')
                return redirect('superadmin:pricing_management')
            
            # Create or update plan
            if plan:
                # Check if slug is being changed and if the new slug already exists
                if plan.slug != slug and SubscriptionPlan.objects.filter(slug=slug).exists():
                    messages.error(request, f'A plan with slug "{slug}" already exists!')
                    return redirect('superadmin:pricing_management')
                
                plan.name = name
                plan.slug = slug
                plan.plan_type = plan_type
                plan.description = description
                plan.price = price
                plan.billing_cycle = billing_cycle
                plan.trial_days = trial_days
                plan.setup_fee = setup_fee
                plan.data_migration_fee = data_migration_fee
                plan.license_fee = license_fee
                plan.training_fee = training_fee
                plan.max_students = max_students
                plan.max_teachers = max_teachers
                plan.max_staff = max_staff
                plan.max_branches = max_branches
                plan.storage_limit_gb = storage_limit_gb
                plan.is_active = is_active
                plan.is_popular = is_popular
                plan.display_order = display_order
                plan.save()
            else:
                # Check if slug already exists
                if SubscriptionPlan.objects.filter(slug=slug).exists():
                    messages.error(request, f'A plan with slug "{slug}" already exists!')
                    return redirect('superadmin:pricing_management')
                
                plan = SubscriptionPlan.objects.create(
                    name=name,
                    slug=slug,
                    plan_type=plan_type,
                    description=description,
                    price=price,
                    billing_cycle=billing_cycle,
                    trial_days=trial_days,
                    setup_fee=setup_fee,
                    data_migration_fee=data_migration_fee,
                    license_fee=license_fee,
                    training_fee=training_fee,
                    max_students=max_students,
                    max_teachers=max_teachers,
                    max_staff=max_staff,
                    max_branches=max_branches,
                    storage_limit_gb=storage_limit_gb,
                    is_active=is_active,
                    is_popular=is_popular,
                    display_order=display_order
                )
            
            messages.success(request, success_msg)
            return redirect('superadmin:pricing_management')
            
        except Exception as e:
            messages.error(request, f'Error saving pricing plan: {str(e)}')
            return redirect('superadmin:pricing_management')


class FAQManagementView(SuperAdminRequiredMixin, View):
    """Manage FAQs"""
    template_name = 'superadmin/faq_management.html'
    
    def get(self, request):
        category_filter = request.GET.get('category', '')
        faqs = FAQ.objects.all()
        
        if category_filter:
            faqs = faqs.filter(category=category_filter)
        
        faqs = faqs.order_by('category', 'order')
        form = FAQForm()
        edit_id = request.GET.get('edit')
        edit_faq = None
        
        if edit_id:
            edit_faq = get_object_or_404(FAQ, id=edit_id)
            form = FAQForm(instance=edit_faq)
        
        categories = FAQ.objects.values_list('category', flat=True).distinct()
        
        return render(request, self.template_name, {
            'faqs': faqs,
            'form': form,
            'edit_faq': edit_faq,
            'categories': categories,
            'category_filter': category_filter
        })
    
    def post(self, request):
        faq_id = request.POST.get('faq_id')
        action = request.POST.get('action')
        
        if action == 'delete' and faq_id:
            faq = get_object_or_404(FAQ, id=faq_id)
            faq.delete()
            messages.success(request, 'FAQ deleted successfully!')
            return redirect('superadmin:faq_management')
        
        if faq_id:
            faq = get_object_or_404(FAQ, id=faq_id)
            form = FAQForm(request.POST, instance=faq)
            success_msg = 'FAQ updated successfully!'
        else:
            form = FAQForm(request.POST)
            success_msg = 'FAQ created successfully!'
        
        if form.is_valid():
            form.save()
            messages.success(request, success_msg)
            return redirect('superadmin:faq_management')
        else:
            faqs = FAQ.objects.all().order_by('category', 'order')
            categories = FAQ.objects.values_list('category', flat=True).distinct()
            return render(request, self.template_name, {
                'faqs': faqs,
                'form': form,
                'categories': categories
            })


class PageContentManagementView(SuperAdminRequiredMixin, View):
    """Manage page content"""
    template_name = 'superadmin/page_content_management.html'
    
    def get(self, request):
        page_contents = PageContent.objects.all()
        form = PageContentForm()
        edit_id = request.GET.get('edit')
        edit_content = None
        
        if edit_id:
            edit_content = get_object_or_404(PageContent, id=edit_id)
            form = PageContentForm(instance=edit_content)
        
        return render(request, self.template_name, {
            'page_contents': page_contents,
            'form': form,
            'edit_content': edit_content
        })
    
    def post(self, request):
        content_id = request.POST.get('content_id')
        action = request.POST.get('action')
        
        if action == 'delete' and content_id:
            content = get_object_or_404(PageContent, id=content_id)
            content.delete()
            messages.success(request, 'Page content deleted successfully!')
            return redirect('superadmin:page_content_management')
        
        if content_id:
            content = get_object_or_404(PageContent, id=content_id)
            form = PageContentForm(request.POST, instance=content)
            success_msg = 'Page content updated successfully!'
        else:
            form = PageContentForm(request.POST)
            success_msg = 'Page content created successfully!'
        
        if form.is_valid():
            form.save()
            messages.success(request, success_msg)
            return redirect('superadmin:page_content_management')
        else:
            page_contents = PageContent.objects.all()
            return render(request, self.template_name, {
                'page_contents': page_contents,
                'form': form
            })


class ContactMessagesView(SuperAdminRequiredMixin, ListView):
    """View contact form submissions"""
    template_name = 'superadmin/contact_messages.html'
    context_object_name = 'messages_list'
    paginate_by = 30
    
    def get_queryset(self):
        queryset = ContactMessage.objects.all().order_by('-created_at')
        status = self.request.GET.get('status')
        if status == 'unread':
            queryset = queryset.filter(is_read=False)
        elif status == 'replied':
            queryset = queryset.filter(replied=True)
        return queryset
    
    def post(self, request):
        message_id = request.POST.get('message_id')
        action = request.POST.get('action')
        
        if message_id:
            contact_message = get_object_or_404(ContactMessage, id=message_id)
            
            if action == 'mark_read':
                contact_message.is_read = True
                contact_message.save()
                messages.success(request, 'Message marked as read!')
            elif action == 'mark_replied':
                contact_message.replied = True
                contact_message.save()
                messages.success(request, 'Message marked as replied!')
            elif action == 'delete':
                contact_message.delete()
                messages.success(request, 'Message deleted successfully!')
        
        return redirect('superadmin:contact_messages')


# ===== IMPERSONATION VIEWS =====

class ImpersonateUserView(SuperAdminRequiredMixin, View):
    """Allow superadmin to impersonate any user"""
    
    def get(self, request, user_id):
        # Get the user to impersonate
        user_to_impersonate = get_object_or_404(User, id=user_id)
        
        # Don't allow impersonating another superadmin
        if user_to_impersonate.role == 'superadmin':
            messages.error(request, 'Cannot impersonate another superadmin!')
            return redirect(request.META.get('HTTP_REFERER', 'superadmin:dashboard'))
        
        # Store original user in session (use same keys as existing system)
        if 'original_user_id' not in request.session:
            request.session['original_user_id'] = request.user.id
        
        # Store impersonated user in session
        request.session['impersonated_user_id'] = user_to_impersonate.id
        
        messages.success(
            request, 
            f'You are now logged in as {user_to_impersonate.get_full_name()} ({user_to_impersonate.get_role_display()})'
        )
        
        # Redirect based on user role and find their school
        school = None
        
        if user_to_impersonate.role == 'admin':
            # For school admin, use their linked school if available
            try:
                school = getattr(user_to_impersonate, 'school', None)
            except Exception:
                school = None
            if not school:
                school = School.objects.filter(is_active=True).first()
        elif user_to_impersonate.role == 'teacher':
            # Get teacher's school through their classes or HR record
            try:
                from academics.models import Class
                teacher_class = Class.objects.filter(class_teacher=user_to_impersonate).first()
                if teacher_class:
                    school = teacher_class.school
            except:
                pass
        elif user_to_impersonate.role == 'student':
            # Get student's school through current_class
            try:
                from students.models import Student
                student = Student.objects.select_related('current_class__school').filter(user=user_to_impersonate).first()
                if student and student.current_class:
                    school = student.current_class.school
            except:
                pass
        elif user_to_impersonate.role == 'parent':
            # Get parent's school from their children
            try:
                from students.models import Student
                child = Student.objects.select_related('current_class__school').filter(parent_user=user_to_impersonate).first()
                if child and child.current_class:
                    school = child.current_class.school
            except:
                pass
        
        # If no school found, get first active school
        if not school:
            school = School.objects.filter(is_active=True).first()
        
        if school:
            return redirect('core:dashboard', school_slug=school.slug)
        
        return redirect('frontend:home')


class StopImpersonationView(LoginRequiredMixin, View):
    """Stop impersonating and return to original superadmin account"""
    
    def get(self, request):
        # Check if impersonating
        if 'original_user_id' not in request.session:
            messages.warning(request, 'You are not currently impersonating anyone.')
            return redirect('frontend:home')
        
        # Get original user
        original_user_id = request.session.get('original_user_id')
        try:
            original_user = User.objects.get(id=original_user_id)
        except User.DoesNotExist:
            messages.error(request, 'Original user not found.')
            return redirect('accounts:login')
        
        # Clear impersonation session
        del request.session['impersonated_user_id']
        del request.session['original_user_id']
        
        messages.success(request, f'You have stopped impersonating and returned to your {original_user.get_role_display()} account.')
        
        # Redirect based on original user role
        if original_user.role == 'superadmin':
            return redirect('superadmin:dashboard')
        else:
            schools = School.objects.filter(is_active=True).first()
            if schools:
                return redirect('core:dashboard', school_slug=schools.slug)
            return redirect('frontend:home')


class SuperAdminProfileView(SuperAdminRequiredMixin, TemplateView):
    """Superadmin profile view"""
    template_name = 'superadmin/profile.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user'] = self.request.user
        return context


# Payment Configuration Views

class PaymentConfigurationListView(SuperAdminRequiredMixin, ListView):
    """List all payment configurations"""
    model = PaymentConfiguration
    template_name = 'superadmin/payment_config_list.html'
    context_object_name = 'configs'
    paginate_by = 10
    
    def get_queryset(self):
        return PaymentConfiguration.objects.all().order_by('gateway', 'environment')


class PaymentConfigurationCreateView(SuperAdminRequiredMixin, CreateView):
    """Create a new payment configuration"""
    model = PaymentConfiguration
    form_class = PaymentConfigurationForm
    template_name = 'superadmin/payment_config_form.html'
    success_url = reverse_lazy('superadmin:payment_config_list')
    
    def form_valid(self, form):
        messages.success(self.request, f'{form.instance.get_gateway_display()} configuration created successfully.')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)


class PaymentConfigurationUpdateView(SuperAdminRequiredMixin, UpdateView):
    """Update a payment configuration"""
    model = PaymentConfiguration
    form_class = PaymentConfigurationForm
    template_name = 'superadmin/payment_config_form.html'
    success_url = reverse_lazy('superadmin:payment_config_list')
    
    def form_valid(self, form):
        messages.success(self.request, f'{form.instance.get_gateway_display()} configuration updated successfully.')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)


class PaymentConfigurationDetailView(SuperAdminRequiredMixin, DetailView):
    """View payment configuration details"""
    model = PaymentConfiguration
    template_name = 'superadmin/payment_config_detail.html'
    context_object_name = 'config'


class PaymentConfigurationDeleteView(SuperAdminRequiredMixin, DeleteView):
    """Delete a payment configuration"""
    model = PaymentConfiguration
    template_name = 'superadmin/payment_config_confirm_delete.html'
    success_url = reverse_lazy('superadmin:payment_config_list')
    
    def delete(self, request, *args, **kwargs):
        config = self.get_object()
        messages.success(request, f'{config.get_gateway_display()} configuration deleted successfully.')
        return super().delete(request, *args, **kwargs)


# Payment Approval Views

class PaymentApprovalListView(SuperAdminRequiredMixin, ListView):
    """List payments pending approval"""
    model = Payment
    template_name = 'superadmin/payment_approval_list.html'
    context_object_name = 'payments'
    paginate_by = 20
    
    def get_queryset(self):
        return Payment.objects.filter(
            status__in=['pending_verification', 'pending', 'verified']
        ).select_related('subscription__school', 'verified_by', 'approved_by').order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['pending_count'] = Payment.objects.filter(
            status__in=['pending_verification', 'pending']
        ).count()
        context['verified_count'] = Payment.objects.filter(status='verified').count()
        return context


class PaymentDetailView(SuperAdminRequiredMixin, DetailView):
    """View payment details for approval"""
    model = Payment
    template_name = 'superadmin/payment_detail.html'
    context_object_name = 'payment'
    
    def get_queryset(self):
        return Payment.objects.select_related(
            'subscription__school', 'subscription__plan', 
            'verified_by', 'approved_by'
        )


class PaymentVerifyView(SuperAdminRequiredMixin, View):
    """Verify a payment"""
    
    def post(self, request, payment_id):
        payment = get_object_or_404(Payment, payment_id=payment_id)
        
        if payment.status not in ['pending_verification', 'pending']:
            messages.error(request, 'This payment cannot be verified.')
            return redirect('superadmin:payment_approval_list')
        
        payment.verify_payment(request.user)
        messages.success(request, f'Payment {payment.payment_id} has been verified.')
        return redirect('superadmin:payment_approval_list')


class PaymentApproveView(SuperAdminRequiredMixin, View):
    """Approve a payment"""
    
    def post(self, request, payment_id):
        payment = get_object_or_404(Payment, payment_id=payment_id)
        
        if payment.status not in ['verified']:
            messages.error(request, 'This payment must be verified before approval.')
            return redirect('superadmin:payment_approval_list')
        
        payment.approve_payment(request.user)
        messages.success(request, f'Payment {payment.payment_id} has been approved and subscription activated.')
        return redirect('superadmin:payment_approval_list')


class PaymentRejectView(SuperAdminRequiredMixin, View):
    """Reject a payment"""
    
    def post(self, request, payment_id):
        payment = get_object_or_404(Payment, payment_id=payment_id)
        rejection_reason = request.POST.get('rejection_reason', '')
        
        if not rejection_reason.strip():
            messages.error(request, 'Please provide a reason for rejection.')
            return redirect('superadmin:payment_detail', pk=payment_id)
        
        payment.reject_payment(request.user, rejection_reason)
        messages.success(request, f'Payment {payment.payment_id} has been rejected.')
        return redirect('superadmin:payment_approval_list')


class PaymentHistoryListView(SuperAdminRequiredMixin, ListView):
    """List all payment history"""
    model = Payment
    template_name = 'superadmin/payment_history_list.html'
    context_object_name = 'payments'
    paginate_by = 25
    
    def get_queryset(self):
        return Payment.objects.select_related(
            'subscription__school', 'subscription__plan',
            'verified_by', 'approved_by'
        ).order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = Payment.STATUS_CHOICES
        context['payment_method_choices'] = Payment.PAYMENT_METHOD_CHOICES
        return context


class InvoiceListView(SuperAdminRequiredMixin, ListView):
    """List all subscription invoices"""
    model = Invoice
    template_name = 'superadmin/invoice_list.html'
    context_object_name = 'invoices'
    paginate_by = 25

    def get_queryset(self):
        # Ensure trial/free invoices exist so they are visible to superadmins
        self._ensure_trial_and_free_invoices()
        queryset = Invoice.objects.select_related(
            'school', 'subscription', 'payment'
        ).order_by('-created_at')

        status = self.request.GET.get('status')
        invoice_type = self.request.GET.get('type')
        school_search = self.request.GET.get('school')

        if status:
            queryset = queryset.filter(status=status)

        if invoice_type:
            queryset = queryset.filter(invoice_type=invoice_type)

        if school_search:
            queryset = queryset.filter(school__name__icontains=school_search)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = Invoice.STATUS_CHOICES
        context['invoice_type_choices'] = Invoice.INVOICE_TYPES
        return context

    def _ensure_trial_and_free_invoices(self):
        """Create missing invoices for schools on trial or free plans.
        This avoids coupling invoice creation to the school admin Billing view.
        """
        try:
            from django.utils import timezone
            # Consider all schools (including inactive) to surface historical trial/free invoices
            schools = School.objects.all()
            for school in schools:
                # Determine latest subscription and effective plan
                sub = school.subscriptions.all().order_by('-created_at').first()
                plan = sub.plan if sub and sub.plan else getattr(school, 'subscription_plan', None)

                # Trial invoice (amount 0, paid)
                is_trial = bool(getattr(school, 'is_trial', False) or (sub and sub.is_trial))
                if is_trial:
                    trial_exists = Invoice.objects.filter(
                        school=school,
                        invoice_type='trial_end'
                    ).exists()
                    if not trial_exists:
                        plan_name = getattr(plan, 'name', 'Trial')
                        start = getattr(school, 'subscription_start_date', None) or (sub.start_date if sub else None)
                        end = getattr(school, 'trial_end_date', None) or (sub.end_date if sub else None)
                        Invoice.objects.create(
                            school=school,
                            subscription=sub,
                            invoice_type='trial_end',
                            plan_name=plan_name,
                            plan_description=f"{plan_name} - Free Trial Period",
                            amount=0,
                            tax_amount=0,
                            total_amount=0,
                            due_date=timezone.now().date(),
                            billing_start_date=start,
                            billing_end_date=end,
                            status='paid'
                        )

                # Free plan invoice (amount 0, paid)
                if plan and getattr(plan, 'price', 0) == 0:
                    free_exists = Invoice.objects.filter(
                        school=school,
                        invoice_type='new',
                        total_amount=0
                    ).exists()
                    if not free_exists:
                        start = None
                        end = None
                        if sub:
                            start = sub.start_date
                            end = sub.end_date
                        elif hasattr(school, 'created_on') and school.created_on:
                            start = school.created_on.date()
                        Invoice.objects.create(
                            school=school,
                            subscription=sub if sub else None,
                            invoice_type='new',
                            plan_name=getattr(plan, 'name', 'Free Plan'),
                            plan_description=f"{getattr(plan, 'name', 'Free Plan')} - Free Plan",
                            amount=0,
                            tax_amount=0,
                            total_amount=0,
                            due_date=timezone.now().date(),
                            billing_start_date=start,
                            billing_end_date=end,
                            status='paid'
                        )
        except Exception as e:
            # Fail-safe: do not block page rendering if backfill fails
            print(f"Invoice backfill error: {e}")


# School Admin Payment Configuration Views
class SchoolAdminRequiredMixin(UserPassesTestMixin):
    """Mixin to require school admin access"""
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.role == 'admin'
    
    def handle_no_permission(self):
        messages.error(self.request, 'You do not have permission to access this page.')
        return redirect('frontend:home')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get school from context or URL
        if hasattr(self, 'school'):
            context['school'] = self.school
        else:
            # Try to get school from URL kwargs
            school_slug = self.kwargs.get('school_slug')
            if school_slug:
                context['school'] = get_object_or_404(School, slug=school_slug)
        return context


class SchoolPaymentConfigurationListView(SchoolAdminRequiredMixin, ListView):
    """List payment configurations for a school"""
    model = SchoolPaymentConfiguration
    template_name = 'superadmin/school_payment_config_list.html'
    context_object_name = 'configs'
    paginate_by = 10
    
    def get_queryset(self):
        school_slug = self.kwargs.get('school_slug')
        self.school = get_object_or_404(School, slug=school_slug)
        return SchoolPaymentConfiguration.objects.filter(school=self.school).order_by('gateway')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school'] = self.school
        return context


class SchoolPaymentConfigurationCreateView(SchoolAdminRequiredMixin, CreateView):
    """Create a new payment configuration for a school"""
    model = SchoolPaymentConfiguration
    form_class = SchoolPaymentConfigurationForm
    template_name = 'superadmin/school_payment_config_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        school_slug = self.kwargs.get('school_slug')
        context['school'] = get_object_or_404(School, slug=school_slug)
        return context
    
    def form_valid(self, form):
        school_slug = self.kwargs.get('school_slug')
        school = get_object_or_404(School, slug=school_slug)
        form.instance.school = school
        
        # Check if configuration already exists for this gateway
        if SchoolPaymentConfiguration.objects.filter(school=school, gateway=form.instance.gateway).exists():
            messages.error(self.request, f'A configuration for {form.instance.get_gateway_display()} already exists.')
            return self.form_invalid(form)
        
        messages.success(self.request, f'Payment configuration for {form.instance.get_gateway_display()} created successfully.')
        return super().form_valid(form)
    
    def get_success_url(self):
        school_slug = self.kwargs.get('school_slug')
        return reverse_lazy('superadmin:school_payment_config_list', kwargs={'school_slug': school_slug})


class SchoolPaymentConfigurationUpdateView(SchoolAdminRequiredMixin, UpdateView):
    """Update a payment configuration for a school"""
    model = SchoolPaymentConfiguration
    form_class = SchoolPaymentConfigurationForm
    template_name = 'superadmin/school_payment_config_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school'] = self.object.school
        return context
    
    def get(self, request, *args, **kwargs):
        # Handle toggle status request
        if request.GET.get('toggle_status') == 'true':
            obj = self.get_object()
            obj.is_active = not obj.is_active
            obj.save()
            status_text = 'activated' if obj.is_active else 'deactivated'
            messages.success(request, f'Payment configuration for {obj.get_gateway_display()} {status_text} successfully.')
            return redirect('superadmin:school_payment_config_detail', school_slug=obj.school.slug, pk=obj.pk)
        
        return super().get(request, *args, **kwargs)
    
    def form_valid(self, form):
        messages.success(self.request, f'Payment configuration for {form.instance.get_gateway_display()} updated successfully.')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('superadmin:school_payment_config_list', kwargs={'school_slug': self.object.school.slug})


class SchoolPaymentConfigurationDetailView(SchoolAdminRequiredMixin, DetailView):
    """View payment configuration details for a school"""
    model = SchoolPaymentConfiguration
    template_name = 'superadmin/school_payment_config_detail.html'
    context_object_name = 'config'


class SchoolPaymentConfigurationDeleteView(SchoolAdminRequiredMixin, DeleteView):
    """Delete a payment configuration for a school"""
    model = SchoolPaymentConfiguration
    template_name = 'superadmin/school_payment_config_confirm_delete.html'
    context_object_name = 'config'
    
    def delete(self, request, *args, **kwargs):
        config = self.get_object()
        messages.success(request, f'Payment configuration for {config.get_gateway_display()} deleted successfully.')
        return super().delete(request, *args, **kwargs)
    
    def get_success_url(self):
        return reverse_lazy('superadmin:school_payment_config_list', kwargs={'school_slug': self.object.school.slug})


# ============== GLOBAL SETTINGS VIEWS ==============

class GlobalSettingsView(SuperAdminRequiredMixin, TemplateView):
    """Global settings dashboard"""
    template_name = 'superadmin/global_settings.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        from .models import GlobalSMSConfiguration, GlobalEmailConfiguration, GlobalDatabaseConfiguration
        from django.conf import settings
        
        context['sms_configs'] = GlobalSMSConfiguration.objects.all()
        context['email_configs'] = GlobalEmailConfiguration.objects.all()
        context['db_configs'] = GlobalDatabaseConfiguration.objects.all()
        
        # Add current database configuration from settings
        current_db = {
            'name': 'Current Database',
            'is_active': True,
            'db_host': getattr(settings, 'DB_HOST', None) or settings.DATABASES['default'].get('HOST', 'localhost'),
            'db_port': getattr(settings, 'DB_PORT', None) or settings.DATABASES['default'].get('PORT', '5432'),
            'db_name': settings.DATABASES['default'].get('NAME', 'N/A'),
            'db_user': getattr(settings, 'DB_USER', None) or settings.DATABASES['default'].get('USER', 'N/A'),
            'db_password': '***' if settings.DATABASES['default'].get('PASSWORD') else None,
            'engine': settings.DATABASES['default']['ENGINE'].split('.')[-1],
            'is_current': True
        }
        
        # Add current email configuration from settings
        current_email = {
            'name': 'Current Email Configuration',
            'is_active': True,
            'smtp_host': getattr(settings, 'EMAIL_HOST', 'Not configured'),
            'smtp_port': getattr(settings, 'EMAIL_PORT', 587),
            'smtp_use_tls': getattr(settings, 'EMAIL_USE_TLS', True),
            'smtp_use_ssl': getattr(settings, 'EMAIL_USE_SSL', False),
            'default_from_email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'Not configured'),
            'default_from_name': getattr(settings, 'DEFAULT_FROM_NAME', 'Clasyo'),
            'backend': getattr(settings, 'EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend').split('.')[-1],
            'is_current': True
        }
        
        # Create simple objects that can be used in templates
        from collections import namedtuple
        
        CurrentDB = namedtuple('CurrentDB', current_db.keys())
        CurrentEmail = namedtuple('CurrentEmail', current_email.keys())
        
        context['current_db'] = CurrentDB(**current_db)
        context['current_email'] = CurrentEmail(**current_email)
        
        return context


class GlobalSMSConfigurationListView(SuperAdminRequiredMixin, ListView):
    """List all global SMS configurations"""
    model = GlobalSMSConfiguration
    template_name = 'superadmin/sms_config_list.html'
    context_object_name = 'configs'
    
    def get_queryset(self):
        return GlobalSMSConfiguration.objects.all().order_by('provider')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from django.conf import settings
        
        # Add current SMS configuration from settings
        current_sms = {
            'name': 'Current SMS Configuration',
            'is_active': True,
            'provider': 'system',
            'api_key': getattr(settings, 'SMS_API_KEY', None),
            'default_sender_id': getattr(settings, 'SMS_SENDER_ID', None),
            'is_current': True
        }
        
        # Create simple object that can be used in template
        from collections import namedtuple
        CurrentSMS = namedtuple('CurrentSMS', current_sms.keys())
        
        context['current_sms'] = CurrentSMS(**current_sms)
        return context


class GlobalSMSConfigurationCreateView(SuperAdminRequiredMixin, CreateView):
    """Create a new global SMS configuration"""
    model = GlobalSMSConfiguration
    template_name = 'superadmin/sms_config_form.html'
    fields = '__all__'
    success_url = reverse_lazy('superadmin:sms_config_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'SMS configuration created successfully.')
        return super().form_valid(form)


class GlobalSMSConfigurationUpdateView(SuperAdminRequiredMixin, UpdateView):
    """Update a global SMS configuration"""
    model = GlobalSMSConfiguration
    template_name = 'superadmin/sms_config_form.html'
    fields = '__all__'
    success_url = reverse_lazy('superadmin:sms_config_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'SMS configuration updated successfully.')
        return super().form_valid(form)


class GlobalSMSConfigurationDeleteView(SuperAdminRequiredMixin, DeleteView):
    """Delete a global SMS configuration"""
    model = GlobalSMSConfiguration
    template_name = 'superadmin/sms_config_confirm_delete.html'
    context_object_name = 'config'
    success_url = reverse_lazy('superadmin:sms_config_list')
    
    def delete(self, request, *args, **kwargs):
        config = self.get_object()
        messages.success(request, f'SMS configuration for {config.get_provider_display()} deleted successfully.')
        return super().delete(request, *args, **kwargs)


class GlobalEmailConfigurationListView(SuperAdminRequiredMixin, ListView):
    """List all global email configurations"""
    model = GlobalEmailConfiguration
    template_name = 'superadmin/email_config_list.html'
    context_object_name = 'configs'
    
    def get_queryset(self):
        return GlobalEmailConfiguration.objects.all().order_by('provider')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from django.conf import settings
        
        # Add current email configuration from settings
        current_email = {
            'name': 'Current Email Configuration',
            'is_active': True,
            'provider': 'system',
            'smtp_host': getattr(settings, 'EMAIL_HOST', 'Not configured'),
            'smtp_port': getattr(settings, 'EMAIL_PORT', 587),
            'smtp_use_tls': getattr(settings, 'EMAIL_USE_TLS', True),
            'smtp_use_ssl': getattr(settings, 'EMAIL_USE_SSL', False),
            'default_from_email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'Not configured'),
            'default_from_name': getattr(settings, 'DEFAULT_FROM_NAME', 'Clasyo'),
            'backend': getattr(settings, 'EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend').split('.')[-1],
            'is_current': True
        }
        
        # Create simple object that can be used in template
        from collections import namedtuple
        CurrentEmail = namedtuple('CurrentEmail', current_email.keys())
        
        context['current_email'] = CurrentEmail(**current_email)
        return context


class GlobalEmailConfigurationCreateView(SuperAdminRequiredMixin, CreateView):
    """Create a new global email configuration"""
    model = GlobalEmailConfiguration
    template_name = 'superadmin/email_config_form.html'
    fields = '__all__'
    success_url = reverse_lazy('superadmin:email_config_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Email configuration created successfully.')
        return super().form_valid(form)


class GlobalEmailConfigurationUpdateView(SuperAdminRequiredMixin, UpdateView):
    """Update a global email configuration"""
    model = GlobalEmailConfiguration
    template_name = 'superadmin/email_config_form.html'
    fields = '__all__'
    success_url = reverse_lazy('superadmin:email_config_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Email configuration updated successfully.')
        return super().form_valid(form)


class GlobalEmailConfigurationDeleteView(SuperAdminRequiredMixin, DeleteView):
    """Delete a global email configuration"""
    model = GlobalEmailConfiguration
    template_name = 'superadmin/email_config_confirm_delete.html'
    context_object_name = 'config'
    success_url = reverse_lazy('superadmin:email_config_list')
    
    def delete(self, request, *args, **kwargs):
        config = self.get_object()
        messages.success(request, f'Email configuration for {config.get_provider_display()} deleted successfully.')
        return super().delete(request, *args, **kwargs)


class AuditLogListView(SuperAdminRequiredMixin, ListView):
    model = AuditLog
    template_name = 'superadmin/audit_logs.html'
    context_object_name = 'logs'
    paginate_by = 50

    def get_queryset(self):
        qs = AuditLog.objects.select_related('user', 'school').all().order_by('-timestamp')
        request = self.request
        school_slug = request.GET.get('school')
        user_id = request.GET.get('user')
        method = request.GET.get('method')
        status = request.GET.get('status')
        q = request.GET.get('q')
        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')
        if school_slug:
            qs = qs.filter(school__slug=school_slug)
        if user_id:
            qs = qs.filter(user_id=user_id)
        if method:
            qs = qs.filter(method__iexact=method)
        if status:
            try:
                qs = qs.filter(status_code=int(status))
            except ValueError:
                pass
        if q:
            qs = qs.filter(path__icontains=q)
        if date_from:
            from django.utils.dateparse import parse_datetime, parse_date
            dt = parse_datetime(date_from) or parse_date(date_from)
            if dt:
                qs = qs.filter(timestamp__gte=dt)
        if date_to:
            from django.utils.dateparse import parse_datetime, parse_date
            dt = parse_datetime(date_to) or parse_date(date_to)
            if dt:
                qs = qs.filter(timestamp__lte=dt)
        return qs

    def get(self, request, *args, **kwargs):
        if request.GET.get('export') == 'csv':
            qs = self.get_queryset()[:50000]
            resp = HttpResponse(content_type='text/csv')
            resp['Content-Disposition'] = 'attachment; filename="audit_logs.csv"'
            writer = csv.writer(resp)
            writer.writerow(['timestamp', 'user', 'school', 'method', 'path', 'status', 'ip', 'user_agent'])
            for log in qs:
                writer.writerow([
                    log.timestamp.isoformat(),
                    getattr(log.user, 'email', '') if log.user_id else '',
                    getattr(log.school, 'name', '') if log.school_id else '',
                    log.method,
                    log.path,
                    log.status_code,
                    log.ip_address or '',
                    (log.user_agent or '')[:200],
                ])
            return resp
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['schools'] = School.objects.all().order_by('name')
        ctx['users'] = User.objects.filter(is_active=True).order_by('email')[:500]
        return ctx


class SchoolAuditLogListView(LoginRequiredMixin, ListView):
    model = AuditLog
    template_name = 'superadmin/audit_logs.html'
    context_object_name = 'logs'
    paginate_by = 50

    def dispatch(self, request, *args, **kwargs):
        # Allow superadmin or school admin only
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        if request.user.role not in ['superadmin', 'admin']:
            messages.error(request, 'You do not have permission to access audit logs.')
            return redirect('frontend:home')
        return super().dispatch(request, *args, **kwargs)

    def get_school(self):
        return get_object_or_404(School, slug=self.kwargs.get('school_slug'))

    def get_queryset(self):
        school = self.get_school()
        qs = AuditLog.objects.select_related('user', 'school').filter(school=school).order_by('-timestamp')
        request = self.request
        user_id = request.GET.get('user')
        method = request.GET.get('method')
        status = request.GET.get('status')
        q = request.GET.get('q')
        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')
        if user_id:
            qs = qs.filter(user_id=user_id)
        if method:
            qs = qs.filter(method__iexact=method)
        if status:
            try:
                qs = qs.filter(status_code=int(status))
            except ValueError:
                pass
        if q:
            qs = qs.filter(path__icontains=q)
        if date_from:
            from django.utils.dateparse import parse_datetime, parse_date
            dt = parse_datetime(date_from) or parse_date(date_from)
            if dt:
                qs = qs.filter(timestamp__gte=dt)
        if date_to:
            from django.utils.dateparse import parse_datetime, parse_date
            dt = parse_datetime(date_to) or parse_date(date_to)
            if dt:
                qs = qs.filter(timestamp__lte=dt)
        return qs

    def get(self, request, *args, **kwargs):
        if request.GET.get('export') == 'csv':
            qs = self.get_queryset()[:50000]
            resp = HttpResponse(content_type='text/csv')
            resp['Content-Disposition'] = 'attachment; filename="school_audit_logs.csv"'
            writer = csv.writer(resp)
            writer.writerow(['timestamp', 'user', 'method', 'path', 'status', 'ip', 'user_agent'])
            for log in qs:
                writer.writerow([
                    log.timestamp.isoformat(),
                    getattr(log.user, 'email', '') if log.user_id else '',
                    log.method,
                    log.path,
                    log.status_code,
                    log.ip_address or '',
                    (log.user_agent or '')[:200],
                ])
            return resp
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['school'] = self.get_school()
        ctx['users'] = User.objects.filter(is_active=True, school=ctx['school']).order_by('email')[:500]
        return ctx

class GlobalDatabaseConfigurationListView(SuperAdminRequiredMixin, ListView):
    """List all global database configurations"""
    model = GlobalDatabaseConfiguration
    template_name = 'superadmin/db_config_list.html'
    context_object_name = 'configs'
    
    def get_queryset(self):
        return GlobalDatabaseConfiguration.objects.all().order_by('name')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from django.conf import settings
        
        # Add current database configuration from settings
        current_db = {
            'name': 'Current Database',
            'is_active': True,
            'db_host': getattr(settings, 'DB_HOST', None) or settings.DATABASES['default'].get('HOST', 'localhost'),
            'db_port': getattr(settings, 'DB_PORT', None) or settings.DATABASES['default'].get('PORT', '5432'),
            'db_name': settings.DATABASES['default'].get('NAME', 'N/A'),
            'db_user': getattr(settings, 'DB_USER', None) or settings.DATABASES['default'].get('USER', 'N/A'),
            'db_password': '***' if settings.DATABASES['default'].get('PASSWORD') else None,
            'engine': settings.DATABASES['default']['ENGINE'].split('.')[-1],
            'is_current': True
        }
        
        # Create simple object that can be used in template
        from collections import namedtuple
        CurrentDB = namedtuple('CurrentDB', current_db.keys())
        
        context['current_db'] = CurrentDB(**current_db)
        return context


class GlobalDatabaseConfigurationCreateView(SuperAdminRequiredMixin, CreateView):
    """Create a new global database configuration"""
    model = GlobalDatabaseConfiguration
    template_name = 'superadmin/db_config_form.html'
    fields = '__all__'
    success_url = reverse_lazy('superadmin:db_config_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Database configuration created successfully.')
        return super().form_valid(form)


class GlobalDatabaseConfigurationUpdateView(SuperAdminRequiredMixin, UpdateView):
    """Update a global database configuration"""
    model = GlobalDatabaseConfiguration
    template_name = 'superadmin/db_config_form.html'
    fields = '__all__'
    success_url = reverse_lazy('superadmin:db_config_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Database configuration updated successfully.')
        return super().form_valid(form)


class GlobalDatabaseConfigurationDeleteView(SuperAdminRequiredMixin, DeleteView):
    """Delete a global database configuration"""
    model = GlobalDatabaseConfiguration
    template_name = 'superadmin/db_config_confirm_delete.html'
    context_object_name = 'config'
    success_url = reverse_lazy('superadmin:db_config_list')
    
    def delete(self, request, *args, **kwargs):
        config = self.get_object()
        messages.success(request, f'Database configuration "{config.name}" deleted successfully.')
        return super().delete(request, *args, **kwargs)


class GlobalAIConfigurationListView(SuperAdminRequiredMixin, ListView):
    """List all global AI configurations"""
    model = GlobalAIConfiguration
    template_name = 'superadmin/ai_config_global_list.html'
    context_object_name = 'configs'

    def get_queryset(self):
        return GlobalAIConfiguration.objects.all().order_by('provider')


class GlobalAIConfigurationCreateView(SuperAdminRequiredMixin, CreateView):
    """Create a new global AI configuration"""
    model = GlobalAIConfiguration
    form_class = GlobalAIConfigurationForm
    template_name = 'superadmin/ai_config_global_form.html'
    success_url = reverse_lazy('superadmin:ai_config_global_list')

    def form_valid(self, form):
        messages.success(self.request, 'Global AI configuration created successfully.')
        return super().form_valid(form)


class GlobalAIConfigurationUpdateView(SuperAdminRequiredMixin, UpdateView):
    """Update a global AI configuration"""
    model = GlobalAIConfiguration
    form_class = GlobalAIConfigurationForm
    template_name = 'superadmin/ai_config_global_form.html'
    success_url = reverse_lazy('superadmin:ai_config_global_list')

    def form_valid(self, form):
        messages.success(self.request, 'Global AI configuration updated successfully.')
        return super().form_valid(form)


class GlobalAIConfigurationDeleteView(SuperAdminRequiredMixin, DeleteView):
    """Delete a global AI configuration"""
    model = GlobalAIConfiguration
    template_name = 'superadmin/ai_config_global_confirm_delete.html'
    context_object_name = 'config'
    success_url = reverse_lazy('superadmin:ai_config_global_list')

    def delete(self, request, *args, **kwargs):
        config = self.get_object()
        messages.success(request, f'Global AI configuration "{config}" deleted successfully.')
        return super().delete(request, *args, **kwargs)


class SchoolAIConfigurationListView(SuperAdminRequiredMixin, ListView):
    """List AI configurations for all schools"""
    model = SchoolAIConfiguration
    template_name = 'superadmin/ai_config_school_list.html'
    context_object_name = 'configs'

    def get_queryset(self):
        return SchoolAIConfiguration.objects.select_related('school').order_by('school__name')


class SchoolAIConfigurationCreateView(SuperAdminRequiredMixin, CreateView):
    """Create a new AI configuration for a school"""
    model = SchoolAIConfiguration
    form_class = SchoolAIConfigurationForm
    template_name = 'superadmin/ai_config_school_form.html'
    success_url = reverse_lazy('superadmin:ai_config_school_list')

    def form_valid(self, form):
        messages.success(self.request, 'School AI configuration created successfully.')
        return super().form_valid(form)


class SchoolAIConfigurationUpdateView(SuperAdminRequiredMixin, UpdateView):
    """Update an AI configuration for a school"""
    model = SchoolAIConfiguration
    form_class = SchoolAIConfigurationForm
    template_name = 'superadmin/ai_config_school_form.html'
    success_url = reverse_lazy('superadmin:ai_config_school_list')

    def form_valid(self, form):
        messages.success(self.request, 'School AI configuration updated successfully.')
        return super().form_valid(form)


class SchoolAIConfigurationDeleteView(SuperAdminRequiredMixin, DeleteView):
    """Delete an AI configuration for a school"""
    model = SchoolAIConfiguration
    template_name = 'superadmin/ai_config_school_confirm_delete.html'
    context_object_name = 'config'
    success_url = reverse_lazy('superadmin:ai_config_school_list')

    def delete(self, request, *args, **kwargs):
        config = self.get_object()
        messages.success(request, f'AI configuration for school "{config.school}" deleted successfully.')
        return super().delete(request, *args, **kwargs)


class SchoolAdminAIConfigurationView(SchoolAdminRequiredMixin, UpdateView):
    """Allow a school admin to manage AI configuration for their own school"""

    model = SchoolAIConfiguration
    form_class = SchoolAIConfigurationForm
    template_name = 'superadmin/school_admin_ai_config_form.html'

    def get_object(self, queryset=None):
        """Fetch or create the SchoolAIConfiguration for the current school"""
        school_slug = self.kwargs.get('school_slug')
        school = get_object_or_404(School, slug=school_slug)
        config, _created = SchoolAIConfiguration.objects.get_or_create(
            school=school,
            defaults={
                'use_global_settings': True,
                'is_active': True,
                'provider': 'openai',
            },
        )
        return config

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug')
        # Add global AI configurations to show available providers
        context['global_configs'] = GlobalAIConfiguration.objects.all().order_by('provider')
        return context

    def get_form_kwargs(self):
        """Pass the school instance to the form"""
        kwargs = super().get_form_kwargs()
        school_slug = self.kwargs.get('school_slug')
        school = get_object_or_404(School, slug=school_slug)
        kwargs['instance'] = self.get_object()  # Already fetches/creates the config
        return kwargs

    def get_success_url(self):
        return reverse_lazy('superadmin:school_admin_ai_config', kwargs={'school_slug': self.kwargs.get('school_slug')})

    def form_valid(self, form):
        print("SchoolAdminAIConfigurationView.form_valid called")
        messages.success(self.request, 'AI configuration for your school has been updated successfully.')
        return super().form_valid(form)

    def form_invalid(self, form):
        print("SchoolAdminAIConfigurationView.form_invalid called")
        print(form.errors)
        return super().form_invalid(form)


class SchoolSMSConfigurationListView(LoginRequiredMixin, ListView):
    """List SMS configurations for a school"""
    model = SchoolSMSConfiguration
    template_name = 'superadmin/school_sms_config_list.html'
    context_object_name = 'configs'
    
    def get_queryset(self):
        school = get_object_or_404(School, slug=self.kwargs.get('school_slug'))
        
        # Check permissions
        if not (self.request.user.role == 'superadmin' or 
                (self.request.user.role == 'admin' and school.is_active)):
            messages.error(self.request, 'You do not have permission to access this school\'s settings.')
            return redirect('frontend:home')
        
        return SchoolSMSConfiguration.objects.filter(school=school).order_by('provider')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school'] = get_object_or_404(School, slug=self.kwargs.get('school_slug'))
        return context


class SchoolSMSConfigurationCreateView(LoginRequiredMixin, CreateView):
    """Create a new SMS configuration for a school"""
    model = SchoolSMSConfiguration
    template_name = 'superadmin/school_sms_config_form.html'
    fields = '__all__'
    
    def get_success_url(self):
        return reverse_lazy('superadmin:school_sms_config_list', kwargs={'school_slug': self.object.school.slug})
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        
        # Filter school based on user role
        if self.request.user.role == 'admin':
            form.fields['school'].queryset = School.objects.filter(is_active=True)
            form.fields['school'].initial = get_object_or_404(School, slug=self.kwargs.get('school_slug'))
            form.fields['school'].widget = forms.HiddenInput()
        elif self.request.user.role == 'superadmin':
            form.fields['school'].queryset = School.objects.all()
        
        return form
    
    def form_valid(self, form):
        messages.success(self.request, 'SMS configuration created successfully.')
        return super().form_valid(form)


class SchoolSMSConfigurationUpdateView(LoginRequiredMixin, UpdateView):
    """Update a SMS configuration for a school"""
    model = SchoolSMSConfiguration
    template_name = 'superadmin/school_sms_config_form.html'
    fields = '__all__'
    
    def get_success_url(self):
        return reverse_lazy('superadmin:school_sms_config_list', kwargs={'school_slug': self.object.school.slug})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school'] = self.object.school
        return context
    
    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        
        # Check permissions
        if not (self.request.user.role == 'superadmin' or 
                (self.request.user.role == 'admin' and obj.school.is_active)):
            messages.error(self.request, 'You do not have permission to access this school\'s settings.')
            return redirect('frontend:home')
        
        return obj
    
    def form_valid(self, form):
        messages.success(self.request, 'SMS configuration updated successfully.')
        return super().form_valid(form)


class SchoolSMSConfigurationDeleteView(LoginRequiredMixin, DeleteView):
    """Delete a SMS configuration for a school"""
    model = SchoolSMSConfiguration
    template_name = 'superadmin/school_sms_config_confirm_delete.html'
    context_object_name = 'config'
    
    def get_success_url(self):
        return reverse_lazy('superadmin:school_sms_config_list', kwargs={'school_slug': self.object.school.slug})
    
    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        
        # Check permissions
        if not (self.request.user.role == 'superadmin' or 
                (self.request.user.role == 'admin' and obj.school.is_active)):
            messages.error(self.request, 'You do not have permission to access this school\'s settings.')
            return redirect('frontend:home')
        
        return obj
    
    def delete(self, request, *args, **kwargs):
        config = self.get_object()
        messages.success(request, f'SMS configuration for {config.get_provider_display()} deleted successfully.')
        return super().delete(request, *args, **kwargs)


class SchoolEmailConfigurationListView(LoginRequiredMixin, ListView):
    """List email configurations for a school"""
    model = SchoolEmailConfiguration
    template_name = 'superadmin/school_email_config_list.html'
    context_object_name = 'configs'
    
    def get_queryset(self):
        school = get_object_or_404(School, slug=self.kwargs.get('school_slug'))
        
        # Check permissions
        if not (self.request.user.role == 'superadmin' or 
                (self.request.user.role == 'admin' and school.is_active)):
            messages.error(self.request, 'You do not have permission to access this school\'s settings.')
            return redirect('frontend:home')
        
        return SchoolEmailConfiguration.objects.filter(school=school).order_by('provider')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school'] = get_object_or_404(School, slug=self.kwargs.get('school_slug'))
        return context


class SchoolEmailConfigurationCreateView(LoginRequiredMixin, CreateView):
    """Create a new email configuration for a school"""
    model = SchoolEmailConfiguration
    template_name = 'superadmin/school_email_config_form.html'
    fields = '__all__'
    
    def get_success_url(self):
        return reverse_lazy('superadmin:school_email_config_list', kwargs={'school_slug': self.object.school.slug})
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        
        # Filter school based on user role
        if self.request.user.role == 'admin':
            form.fields['school'].queryset = School.objects.filter(is_active=True)
            form.fields['school'].initial = get_object_or_404(School, slug=self.kwargs.get('school_slug'))
            form.fields['school'].widget = forms.HiddenInput()
        elif self.request.user.role == 'superadmin':
            form.fields['school'].queryset = School.objects.all()
        
        return form
    
    def form_valid(self, form):
        messages.success(self.request, 'Email configuration created successfully.')
        return super().form_valid(form)


class SchoolEmailConfigurationUpdateView(LoginRequiredMixin, UpdateView):
    """Update an email configuration for a school"""
    model = SchoolEmailConfiguration
    template_name = 'superadmin/school_email_config_form.html'
    fields = '__all__'
    
    def get_success_url(self):
        return reverse_lazy('superadmin:school_email_config_list', kwargs={'school_slug': self.object.school.slug})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school'] = self.object.school
        return context
    
    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        
        # Check permissions
        if not (self.request.user.role == 'superadmin' or 
                (self.request.user.role == 'admin' and obj.school.is_active)):
            messages.error(self.request, 'You do not have permission to access this school\'s settings.')
            return redirect('frontend:home')
        
        return obj
    
    def form_valid(self, form):
        messages.success(self.request, 'Email configuration updated successfully.')
        return super().form_valid(form)


class SchoolEmailConfigurationDeleteView(LoginRequiredMixin, DeleteView):
    """Delete an email configuration for a school"""
    model = SchoolEmailConfiguration
    template_name = 'superadmin/school_email_config_confirm_delete.html'
    context_object_name = 'config'
    
    def get_success_url(self):
        return reverse_lazy('superadmin:school_email_config_list', kwargs={'school_slug': self.object.school.slug})
    
    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        
        # Check permissions
        if not (self.request.user.role == 'superadmin' or 
                (self.request.user.role == 'admin' and obj.school.is_active)):
            messages.error(self.request, 'You do not have permission to access this school\'s settings.')
            return redirect('frontend:home')
        
        return obj
    
    def delete(self, request, *args, **kwargs):
        config = self.get_object()
        messages.success(request, f'Email configuration for {config.get_provider_display()} deleted successfully.')
        return super().delete(request, *args, **kwargs)
