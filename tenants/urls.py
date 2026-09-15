from django.urls import path
from . import views

app_name = 'tenants'

urlpatterns = [
    path('workspace-setup/<slug:school_slug>/', views.WorkspaceProvisioningView.as_view(), name='workspace_provisioning'),
    path('api/provision/<slug:school_slug>/', views.WorkspaceProvisioningApiView.as_view(), name='api_provision'),
    path('api/status/<slug:school_slug>/', views.WorkspaceStatusApiView.as_view(), name='api_status'),
]
