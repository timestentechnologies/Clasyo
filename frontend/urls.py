from django.urls import path
from . import views

app_name = 'frontend'

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('about/', views.AboutView.as_view(), name='about'),
    path('pricing/', views.PricingView.as_view(), name='pricing'),
    path('contact/', views.ContactView.as_view(), name='contact'),
    path('faq/', views.FAQView.as_view(), name='faq'),
    path('privacy/', views.PrivacyPolicyView.as_view(), name='privacy'),
    path('terms/', views.TermsOfServiceView.as_view(), name='terms'),
    path('license/', views.LicenseView.as_view(), name='license'),
    path('documentation/', views.DocumentationView.as_view(), name='documentation'),
    path('documentation/pdf/', views.generate_pdf_documentation, name='documentation_pdf'),
    path('register/', views.SchoolRegistrationView.as_view(), name='register'),
]
