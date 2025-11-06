from django.urls import path
from . import views

app_name = 'leave_management'

urlpatterns = [
    path('', views.LeaveListView.as_view(), name='leave_list'),
    path('apply/', views.LeaveApplyView.as_view(), name='leave_apply'),
    path('<int:pk>/approve/', views.LeaveApproveView.as_view(), name='leave_approve'),
    path('<int:pk>/reject/', views.LeaveRejectView.as_view(), name='leave_reject'),
    # API endpoints
    path('api/teachers/', views.TeachersAPIView.as_view(), name='api_teachers'),
    path('api/students/', views.StudentsAPIView.as_view(), name='api_students'),
    path('api/staff/', views.StaffAPIView.as_view(), name='api_staff'),
]
