from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from django.contrib.sitemaps.views import sitemap
from frontend.sitemaps import StaticViewSitemap
from inventory.views import CanteenPOSView

def health_check(request):
    return JsonResponse({'status': 'ok', 'service': 'schoolsaas'}, status=200)

sitemaps = {
    'static': StaticViewSitemap,  # Pass class to avoid instantiating during urlconf import
}

from django.views.generic import RedirectView

urlpatterns = [
    # Favicon route
    path('favicon.ico', RedirectView.as_view(url='/static/images/favicon.ico', permanent=True)),
    
    # Health checks (for Cron-job.org, UptimeRobot, Render Health Check)
    path('health/', health_check, name='health_check'),
    path('healthz/', health_check, name='healthz_check'),
    path('ping/', health_check, name='ping_check'),
    
    # Admin
    path('admin/', admin.site.urls),
    
    # Sitemap
    path('sitemap.xml', sitemap, 
        {
            'sitemaps': sitemaps, 
            'template_name': 'sitemap.xml',
            'content_type': 'application/xml'
        }, 
        name='django.contrib.sitemaps.views.sitemap'),
    
    # Super Admin
    path('superadmin/', include('superadmin.urls', namespace='superadmin')),
    
    # Authentication
    path('accounts/', include('accounts.urls', namespace='accounts')),
    # Social authentication (django-allauth)
    path('auth/', include('allauth.urls')),
    # Compatibility routes for Google OAuth if accessed via /accounts/
    path('accounts/google/login/', RedirectView.as_view(url='/auth/google/login/', permanent=False)),
    path('accounts/google/login/callback/', RedirectView.as_view(url='/auth/google/login/callback/', query_string=True, permanent=False)),
    
    # Public site
    path('', include('frontend.urls', namespace='frontend')),
    
    # Subscriptions
    path('subscriptions/', include('subscriptions.urls', namespace='subscriptions')),
    
    # Tenants & Workspace Provisioning
    path('tenants/', include('tenants.urls', namespace='tenants')),
    
    # School modules (tenant-specific)
    path('school/<slug:school_slug>/', include([
        path('', include('core.urls', namespace='core')),
        path('students/', include('students.urls', namespace='students')),
        path('academics/', include('academics.urls', namespace='academics')),
        path('fees/', include('fees.urls', namespace='fees')),
        path('examinations/', include('examinations.urls', namespace='examinations')),
        path('homework/', include('homework.urls', namespace='homework')),
        path('hr/', include('human_resource.urls', namespace='hr')),
        path('leave/', include('leave_management.urls', namespace='leave')),
        path('communication/', include('communication.urls', namespace='communication')),
        path('library/', include('library.urls', namespace='library')),
        path('inventory/', include('inventory.urls', namespace='inventory')),
        path('transport/', include('transport.urls', namespace='transport')),
        path('dormitory/', include('dormitory.urls', namespace='dormitory')),
        path('attendance/', include('attendance.urls', namespace='attendance')),
        path('lesson-plan/', include('lesson_plan.urls', namespace='lesson_plan')),
        path('certificates/', include('certificates.urls', namespace='certificates')),
        path('reports/', include('reports.urls', namespace='reports')),
        path('finance/', include('finance.urls', namespace='finance')),
        path('online-exam/', include('online_exam.urls', namespace='online_exam')),
        path('chat/', include('chat.urls', namespace='chat')),
        path('clubs/', include('clubs.urls', namespace='clubs')),
        path('canteen/pos/', CanteenPOSView.as_view(), name='canteen_pos'),
    ])),
]

# Always serve media files via Django (handles cPanel/Passenger where Apache rewrite may not apply)
# Static files in production are handled by WhiteNoise; media files are always served by Django
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
