from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    # Main views (legacy)
    path('', views.ReportsIndexView.as_view(), name='index'),
    
    # Student Reports (legacy)
    path('students/enrollment/', views.StudentEnrollmentReportView.as_view(), name='student_enrollment'),
    path('students/enrollment/export/<str:format>/', views.ExportStudentEnrollmentView.as_view(), name='export_enrollment'),
    
    # New report system URLs
    path('dashboard/', views.ReportDashboardView.as_view(), name='dashboard'),
    path('types/', views.ReportTypeListView.as_view(), name='report_types'),
    path('saved/', views.SavedReportListView.as_view(), name='saved_reports'),
    path('view/<int:pk>/', views.SavedReportDetailView.as_view(), name='report_detail'),
]
