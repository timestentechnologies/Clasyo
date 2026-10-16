from django.urls import path
from . import views
from .views_autocomplete import StudentAutocompleteView

app_name = 'students'

urlpatterns = [
    path('', views.StudentListView.as_view(), name='list'),
    path('add/', views.StudentCreateView.as_view(), name='add'),
    # Import/Export
    path('export/', views.StudentExportView.as_view(), name='export'),
    path('template/', views.StudentTemplateView.as_view(), name='template'),
    path('import/', views.StudentImportView.as_view(), name='import'),
    path('import/sheets/', views.StudentImportSheetsView.as_view(), name='import_sheets'),
    path('import/preview/', views.StudentImportPreviewView.as_view(), name='import_preview'),
    # Promotion
    path('promote/', views.StudentPromotionView.as_view(), name='promote'),
    path('promote/api/students/', views.get_promotion_students_api, name='promotion_students_api'),
    path('promote/history/', views.StudentPromotionHistoryView.as_view(), name='promotion_history'),
    
    path('parents/', views.ParentListView.as_view(), name='parents'),
    path('parents/<int:pk>/', views.ParentDetailView.as_view(), name='parent_detail'),
    path('<int:pk>/', views.StudentDetailView.as_view(), name='detail'),
    path('<int:pk>/subjects/', views.StudentSubjectsView.as_view(), name='subjects'),
    path('<int:pk>/edit/', views.StudentUpdateView.as_view(), name='edit'),
    path('<int:pk>/delete/', views.StudentDeleteView.as_view(), name='delete'),
    path('<int:pk>/exit/', views.StudentExitView.as_view(), name='exit'),
    path('<int:pk>/status/', views.StudentStatusUpdateView.as_view(), name='update_status'),
    path('bulk-enroll/', views.StudentBulkConfirmEnrollmentView.as_view(), name='bulk_enroll'),
    path('api/platform-schools/', views.PlatformSchoolsApiView.as_view(), name='platform_schools_api'),
    
    # Autocomplete endpoints
    path('autocomplete/', StudentAutocompleteView.as_view(), name='student_autocomplete'),
]
