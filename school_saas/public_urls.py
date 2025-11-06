from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('superadmin/', include('superadmin.urls', namespace='superadmin')),
    path('subscriptions/', include('subscriptions.urls', namespace='subscriptions')),
    path('', include('frontend.urls', namespace='frontend')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
