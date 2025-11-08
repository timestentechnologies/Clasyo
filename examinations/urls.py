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
    path('marks/<int:exam_id>/students/', views.GetStudentsForMarksEntryView.as_view(), name='get_students_for_marks'),
    path('marks/<int:exam_id>/save/', views.SaveMarksEntryView.as_view(), name='save_marks_entry'),
    path('results/', views.ResultView.as_view(), name='results'),
    
    # Student exam taking
    path('<int:exam_id>/take/', views.StudentExamTakeView.as_view(), name='student_take_exam'),
    path('<int:exam_id>/submit-answer/', views.StudentSubmitAnswerView.as_view(), name='student_submit_answer'),
    path('<int:exam_id>/submit-exam/', views.StudentSubmitExamView.as_view(), name='student_submit_exam'),
    
    # Teacher grading
    path('grading/', views.TeacherGradingListView.as_view(), name='teacher_grading_list'),
    path('grading/<int:submission_id>/', views.TeacherGradeSubmissionView.as_view(), name='teacher_grade_submission'),
    path('grading/<int:submission_id>/save/', views.TeacherSaveGradingView.as_view(), name='teacher_save_grading'),
    
    # Student results and corrections
    path('my-results/', views.StudentResultsView.as_view(), name='student_results'),
    path('my-results/<int:submission_id>/', views.StudentResultDetailView.as_view(), name='student_result_detail'),
    path('correction/<int:answer_id>/submit/', views.StudentSubmitCorrectionView.as_view(), name='student_submit_correction'),
]
