from django.urls import path
from . import views

app_name = 'superadmin'

urlpatterns = [
    # Dashboard
    path('', views.DashboardView.as_view(), name='dashboard'),
    
    # Schools
    path('schools/', views.SchoolListView.as_view(), name='schools'),
    path('schools/create/', views.SchoolCreateView.as_view(), name='school_create'),
    path('schools/<int:pk>/', views.SchoolDetailView.as_view(), name='school_detail'),
    path('schools/<int:pk>/edit/', views.SchoolUpdateView.as_view(), name='school_edit'),
    path('schools/<int:pk>/delete/', views.SchoolDeleteView.as_view(), name='school_delete'),
    
    # School Admins
    path('admins/', views.AdminUserListView.as_view(), name='admins'),
    path('admins/create/', views.AdminUserCreateView.as_view(), name='admin_create'),
    path('admins/<int:pk>/edit/', views.AdminUserUpdateView.as_view(), name='admin_edit'),
    
    # Subscriptions
    path('subscriptions/', views.SubscriptionListView.as_view(), name='subscriptions'),
]
