from django.urls import path
from . import views

app_name = 'superadmin'

urlpatterns = [
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('schools/', views.SchoolListView.as_view(), name='schools'),
    path('schools/<int:pk>/', views.SchoolDetailView.as_view(), name='school_detail'),
    path('subscriptions/', views.SubscriptionListView.as_view(), name='subscriptions'),
]
