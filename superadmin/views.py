from django.shortcuts import render
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Count, Sum
from tenants.models import School
from subscriptions.models import Subscription, Payment


class SuperAdminRequiredMixin(UserPassesTestMixin):
    """Mixin to require super admin access"""
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.role == 'super_admin'


class DashboardView(SuperAdminRequiredMixin, TemplateView):
    """Super Admin Dashboard"""
    template_name = 'superadmin/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get statistics
        context['stats'] = {
            'total_schools': School.objects.count(),
            'active_schools': School.objects.filter(is_active=True).count(),
            'trial_schools': School.objects.filter(is_trial=True, is_active=True).count(),
            'total_revenue': Payment.objects.filter(status='completed').aggregate(
                total=Sum('amount')
            )['total'] or 0,
        }
        
        # Get recent schools
        context['recent_schools'] = School.objects.all().order_by('-created_on')[:10]
        
        return context


class SchoolListView(SuperAdminRequiredMixin, ListView):
    """List all schools"""
    model = School
    template_name = 'superadmin/school_list.html'
    context_object_name = 'schools'
    paginate_by = 20
    ordering = ['-created_on']


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
