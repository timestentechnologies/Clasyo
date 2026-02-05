from django.urls import path
from django.views.decorators.cache import cache_page
from . import views

app_name = 'frontend'

urlpatterns = [
    path('', cache_page(60 * 10)(views.HomeView.as_view()), name='home'),  # 10 minutes
    path('about/', cache_page(60 * 60)(views.AboutView.as_view()), name='about'),  # 1 hour
    path('pricing/', cache_page(60 * 30)(views.PricingView.as_view()), name='pricing'),  # 30 minutes
    path('contact/', views.ContactView.as_view(), name='contact'),  # has form; avoid full-page cache
    path('faq/', cache_page(60 * 30)(views.FAQView.as_view()), name='faq'),  # 30 minutes
    path('privacy/', cache_page(60 * 60 * 24)(views.PrivacyPolicyView.as_view()), name='privacy'),  # 1 day
    path('terms/', cache_page(60 * 60 * 24)(views.TermsOfServiceView.as_view()), name='terms'),  # 1 day
    path('license/', cache_page(60 * 60 * 24)(views.LicenseView.as_view()), name='license'),  # 1 day
    path('documentation/', cache_page(60 * 60)(views.DocumentationView.as_view()), name='documentation'),  # 1 hour
    path('documentation/pdf/', views.generate_pdf_documentation, name='documentation_pdf'),
    path('register/', views.SchoolRegistrationView.as_view(), name='register'),
    # Community Forum
    path('forum/', views.CommunityForumView.as_view(), name='forum'),
    path('forum/thread/<int:message_id>/', views.CommunityThreadView.as_view(), name='forum_thread'),
    # Public AI Chat API
    path('api/ai/chat/', views.PublicAiChatApiView.as_view(), name='public_ai_chat'),
]
