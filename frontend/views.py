from django.shortcuts import render
from django.views.generic import TemplateView
from subscriptions.models import SubscriptionPlan


class HomeView(TemplateView):
    """Homepage view"""
    template_name = 'frontend/home.html'


class AboutView(TemplateView):
    """About page view"""
    template_name = 'frontend/about.html'


class ContactView(TemplateView):
    """Contact page view"""
    template_name = 'frontend/contact.html'


class PricingView(TemplateView):
    """Pricing page view"""
    template_name = 'frontend/pricing.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['plans'] = SubscriptionPlan.objects.filter(is_active=True).order_by('price')
        return context
