from django.urls import path
from . import views

app_name = 'examinations'

urlpatterns = [
    path('', views.ExamListView.as_view(), name='exam_list'),
    path('add/', views.ExamCreateView.as_view(), name='exam_create'),
    path('<int:pk>/delete/', views.ExamDeleteView.as_view(), name='exam_delete'),
    
    # Question management for online exams
    path('<int:exam_id>/questions/', views.QuestionListView.as_view(), name='question_list'),
    path('<int:exam_id>/questions/add/', views.QuestionCreateView.as_view(), name='question_create'),
    path('questions/<int:pk>/delete/', views.QuestionDeleteView.as_view(), name='question_delete'),
    
    path('grades/', views.GradeListView.as_view(), name='grade_list'),
    path('grades/add/', views.GradeCreateView.as_view(), name='grade_create'),
    path('grades/<int:pk>/edit/', views.GradeUpdateView.as_view(), name='grade_update'),
    path('grades/<int:pk>/delete/', views.GradeDeleteView.as_view(), name='grade_delete'),
    
    path('marks/', views.MarksEntryView.as_view(), name='marks_entry'),
    path('results/', views.ResultView.as_view(), name='results'),
]
