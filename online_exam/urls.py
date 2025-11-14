from django.urls import path
from . import views

app_name = 'online_exam'

urlpatterns = [
    # Dashboard
    path('', views.OnlineExamDashboardView.as_view(), name='dashboard'),
    
    # Exam management
    path('list/', views.OnlineExamListView.as_view(), name='list'),
    path('create/', views.OnlineExamCreateView.as_view(), name='create'),
    path('<int:pk>/', views.OnlineExamDetailView.as_view(), name='detail'),
    path('<int:pk>/update/', views.OnlineExamUpdateView.as_view(), name='update'),
    path('<int:pk>/delete/', views.OnlineExamDeleteView.as_view(), name='delete'),
    
    # Results and grading
    path('<int:exam_id>/results/', views.ExamResultsView.as_view(), name='results'),
    path('attempt/<int:attempt_id>/grade/', views.GradeExamAttemptView.as_view(), name='grade_attempt'),
    
    # Taking exams
    path('<int:pk>/take/', views.TakeExamView.as_view(), name='take_exam'),
    path('<int:pk>/preview/', views.PreviewExamView.as_view(), name='preview'),
    path('<int:pk>/toggle-status/', views.ToggleExamStatusView.as_view(), name='toggle_status'),
    
    # Question management
    path('<int:exam_id>/questions/', views.ManageQuestionsView.as_view(), name='manage_questions'),
    path('<int:exam_id>/questions/add/', views.AddQuestionView.as_view(), name='add_question'),
    path('<int:exam_id>/questions/<int:question_id>/edit/', views.EditQuestionView.as_view(), name='edit_question'),
    path('<int:exam_id>/questions/<int:question_id>/delete/', views.DeleteQuestionView.as_view(), name='delete_question'),
]
