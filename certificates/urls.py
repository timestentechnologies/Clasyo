from django.urls import path
from . import views

app_name = 'certificates'

urlpatterns = [
    # Certificate Type URLs
    path('types/', views.CertificateTypeListView.as_view(), name='type_list'),  # Also used as manage_types
    path('types/create/', views.CertificateTypeCreateView.as_view(), name='type_create'),
    path('types/<int:pk>/update/', views.CertificateTypeUpdateView.as_view(), name='type_update'),
    path('types/<int:pk>/delete/', views.CertificateTypeDeleteView.as_view(), name='type_delete'),
    
    # Certificate URLs
    path('', views.CertificateListView.as_view(), name='list'),
    path('create/', views.CertificateCreateView.as_view(), name='create'),
    path('<int:pk>/', views.CertificateDetailView.as_view(), name='view'),
    path('<int:pk>/edit/', views.CertificateUpdateView.as_view(), name='edit'),
    path('<int:pk>/delete/', views.CertificateDeleteView.as_view(), name='delete'),
    path('<int:pk>/download/', views.CertificateDownloadView.as_view(), name='download'),
    path('<int:pk>/revoke/', views.CertificateRevokeView.as_view(), name='revoke'),
    path('batch-print/', views.PrintBatchCertificatesView.as_view(), name='batch_print'),
    
    # Certificate Verification
    path('verify/', views.CertificateVerifyView.as_view(), name='verify'),
    path('verify/<uuid:certificate_uuid>/', views.CertificateVerifyView.as_view(), name='verify'),
    
    # ID Card Template URLs
    path('templates/', views.IDCardTemplateListView.as_view(), name='template_list'),
    path('templates/create/', views.IDCardTemplateCreateView.as_view(), name='add_template'),
    path('templates/<int:pk>/update/', views.IDCardTemplateUpdateView.as_view(), name='template_update'),
    path('templates/<int:pk>/delete/', views.IDCardTemplateDeleteView.as_view(), name='template_delete'),
    
    # ID Card URLs
    path('idcard/', views.IDCardListView.as_view(), name='idcard_list'),
    path('idcard/create/', views.IDCardCreateView.as_view(), name='idcard_create'),
    path('idcard/<int:pk>/', views.IDCardDetailView.as_view(), name='idcard_detail'),
    path('idcard/<int:pk>/update/', views.IDCardUpdateView.as_view(), name='idcard_update'),
    path('idcard/<int:pk>/print/', views.PrintIDCardView.as_view(), name='idcard_print'),
    path('idcard/<int:pk>/mark-lost/', views.MarkIDCardLostView.as_view(), name='idcard_mark_lost'),
    path('idcard/bulk-create/', views.BulkIDCardCreateView.as_view(), name='idcard_bulk_create'),
]
