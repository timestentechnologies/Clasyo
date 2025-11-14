from django.urls import path
from . import views

app_name = 'lesson_plan'

urlpatterns = [
    # Main views
    path('', views.LessonPlanDashboardView.as_view(), name='dashboard'),
    path('list/', views.LessonPlanListView.as_view(), name='list'),
    path('create/', views.LessonPlanCreateView.as_view(), name='create'),
    path('<int:pk>/', views.LessonPlanDetailView.as_view(), name='detail'),
    path('<int:pk>/update/', views.LessonPlanUpdateView.as_view(), name='update'),
    path('<int:pk>/delete/', views.LessonPlanDeleteView.as_view(), name='delete'),
    path('<int:pk>/export-pdf/', views.LessonPlanExportPDF.as_view(), name='export_pdf'),
    
    # Class-specific views
    path('class/<int:class_id>/subject/<int:subject_id>/', views.ClassLessonPlansView.as_view(), name='class_lesson_plans'),
    path('create/class/<int:class_id>/subject/<int:subject_id>/', views.LessonPlanCreateForClassView.as_view(), name='create_for_class'),
]
