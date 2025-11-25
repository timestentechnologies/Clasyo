from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.sitemaps.views import sitemap
from frontend.sitemaps import StaticViewSitemap

sitemaps = {
    'static': StaticViewSitemap,
}

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    
    # Sitemap
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    
    # Super Admin
    path('superadmin/', include('superadmin.urls', namespace='superadmin')),
    
    # Authentication
    path('accounts/', include('accounts.urls', namespace='accounts')),
    
    # Public site
    path('', include('frontend.urls', namespace='frontend')),
    
    # Subscriptions
    path('subscriptions/', include('subscriptions.urls', namespace='subscriptions')),
    
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
        path('online-exam/', include('online_exam.urls', namespace='online_exam')),
        path('chat/', include('chat.urls', namespace='chat')),
    ])),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
