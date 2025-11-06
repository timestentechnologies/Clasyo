from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls', namespace='accounts')),
    path('students/', include('students.urls', namespace='students')),
    path('academics/', include('academics.urls', namespace='academics')),
    path('fees/', include('fees.urls', namespace='fees')),
    path('examinations/', include('examinations.urls', namespace='examinations')),
    path('online-exam/', include('online_exam.urls', namespace='online_exam')),
    path('homework/', include('homework.urls', namespace='homework')),
    path('hr/', include('human_resource.urls', namespace='hr')),
    path('leave/', include('leave_management.urls', namespace='leave')),
    path('communication/', include('communication.urls', namespace='communication')),
    path('library/', include('library.urls', namespace='library')),
    path('inventory/', include('inventory.urls', namespace='inventory')),
    path('transport/', include('transport.urls', namespace='transport')),
    path('dormitory/', include('dormitory.urls', namespace='dormitory')),
    path('reports/', include('reports.urls', namespace='reports')),
    path('certificates/', include('certificates.urls', namespace='certificates')),
    path('attendance/', include('attendance.urls', namespace='attendance')),
    path('lesson-plan/', include('lesson_plan.urls', namespace='lesson_plan')),
    path('chat/', include('chat.urls', namespace='chat')),
    path('', include('core.urls', namespace='core')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
