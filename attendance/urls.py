from django.urls import path
from . import views

app_name = 'attendance'

urlpatterns = [
    path('mark/', views.MarkAttendanceView.as_view(), name='mark_attendance'),
    path('report/', views.AttendanceReportView.as_view(), name='attendance_report'),
    path('student/<int:student_id>/', views.StudentAttendanceView.as_view(), name='student_attendance'),
    path('my-attendance/', views.MyAttendanceView.as_view(), name='my_attendance'),
]
