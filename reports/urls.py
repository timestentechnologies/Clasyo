from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('', views.ReportsIndexView.as_view(), name='index'),
    
    # Student Reports
    path('students/enrollment/', views.StudentEnrollmentReportView.as_view(), name='student_enrollment'),
    path('students/enrollment/export/<str:format>/', views.ExportStudentEnrollmentView.as_view(), name='export_enrollment'),
]
