from django.urls import path
from . import views

app_name = 'homework'

urlpatterns = [
    # Dashboard
    path('', views.HomeworkDashboardView.as_view(), name='dashboard'),
    
    # Assignment management
    path('list/', views.HomeworkAssignmentListView.as_view(), name='list'),
    path('create/', views.HomeworkAssignmentCreateView.as_view(), name='create'),
    path('<int:pk>/', views.HomeworkAssignmentDetailView.as_view(), name='detail'),
    path('<int:pk>/update/', views.HomeworkAssignmentUpdateView.as_view(), name='update'),
    path('<int:pk>/delete/', views.HomeworkAssignmentDeleteView.as_view(), name='delete'),
    
    # Submission management
    path('<int:assignment_id>/submit/', views.HomeworkSubmitView.as_view(), name='submit'),
    path('submission/<int:pk>/', views.HomeworkSubmissionDetailView.as_view(), name='view_submission'),
    path('submission/<int:pk>/grade/', views.HomeworkSubmissionGradeView.as_view(), name='grade_submission'),
    path('submission/<int:submission_id>/comments/add/', views.AddCommentView.as_view(), name='add_comment'),
    
    # Student views
    path('my-assignments/', views.StudentHomeworkListView.as_view(), name='student_assignments'),
    
    # Teacher class views
    path('class/<int:class_id>/', views.ClassHomeworkListView.as_view(), name='class_assignments'),
    path('class/<int:class_id>/submissions/', views.ClassSubmissionsView.as_view(), name='class_submissions'),
]
