from django.urls import path
from django.views.decorators.cache import cache_page
from django.views.generic import RedirectView
from django.conf import settings
from . import views

app_name = 'frontend'

def dev_cache(timeout):
    if settings.DEBUG:
        return lambda view_func: view_func
    return cache_page(timeout)

urlpatterns = [
    path('', dev_cache(60 * 10)(views.HomeView.as_view()), name='home'),  # 10 minutes
    path('features/', dev_cache(60 * 30)(views.FeaturesView.as_view()), name='features'),  # 30 minutes
    path('about/', RedirectView.as_view(url='/', permanent=True), name='about'),
    path('pricing/', dev_cache(60 * 30)(views.PricingView.as_view()), name='pricing'),  # 30 minutes
    path('contact/', views.ContactView.as_view(), name='contact'),  # has form; avoid full-page cache
    path('faq/', dev_cache(60 * 30)(views.FAQView.as_view()), name='faq'),  # 30 minutes
    path('privacy/', dev_cache(60 * 60 * 24)(views.PrivacyPolicyView.as_view()), name='privacy'),  # 1 day
    path('terms/', dev_cache(60 * 60 * 24)(views.TermsOfServiceView.as_view()), name='terms'),  # 1 day
    path('license/', dev_cache(60 * 60 * 24)(views.LicenseView.as_view()), name='license'),  # 1 day
    path('documentation/', dev_cache(60 * 60)(views.DocumentationView.as_view()), name='documentation'),  # 1 hour
    path('documentation/pdf/', views.generate_pdf_documentation, name='documentation_pdf'),
    path('register/', views.SchoolRegistrationView.as_view(), name='register'),
    # Community Forum
    path('forum/', views.CommunityForumView.as_view(), name='forum'),
    path('forum/thread/<int:message_id>/', views.CommunityThreadView.as_view(), name='forum_thread'),
    # Public AI Chat API
    path('api/ai/chat/', views.PublicAiChatApiView.as_view(), name='public_ai_chat'),
]
