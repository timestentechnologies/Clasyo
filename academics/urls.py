from django.urls import path
from . import views

app_name = 'academics'

urlpatterns = [
    # Classes
    path('classes/', views.ClassListView.as_view(), name='class_list'),
    path('classes/add/', views.ClassCreateView.as_view(), name='class_create'),
    path('classes/<int:pk>/', views.get_class_api, name='class_detail_api'),
    path('classes/<int:pk>/edit/', views.ClassUpdateView.as_view(), name='class_update'),
    path('classes/<int:pk>/delete/', views.ClassDeleteView.as_view(), name='class_delete'),
    
    # Sections
    path('sections/', views.SectionListView.as_view(), name='section_list'),
    path('sections/add/', views.SectionCreateView.as_view(), name='section_create'),
    path('sections/<int:pk>/delete/', views.SectionDeleteView.as_view(), name='section_delete'),
    
    # Subjects
    path('subjects/', views.SubjectListView.as_view(), name='subject_list'),
    path('subjects/add/', views.SubjectCreateView.as_view(), name='subject_create'),
    path('subjects/<int:pk>/edit/', views.SubjectUpdateView.as_view(), name='subject_update'),
    path('subjects/<int:pk>/delete/', views.SubjectDeleteView.as_view(), name='subject_delete'),

    # Class-Subject Linking
    path('class-subjects/', views.ClassSubjectAssignmentsView.as_view(), name='class_subjects'),
    
    # Class Routine
    path('routine/', views.ClassRoutineView.as_view(), name='routine'),
    path('routine/add/', views.ClassRoutineCreateView.as_view(), name='routine_create'),
    
    # Class Time (Time Periods & Breaks)
    path('class-times/', views.ClassTimeListView.as_view(), name='class_time_list'),
    path('class-times/add/', views.ClassTimeCreateView.as_view(), name='class_time_create'),
    path('class-times/<int:pk>/edit/', views.ClassTimeUpdateView.as_view(), name='class_time_update'),
    path('class-times/<int:pk>/delete/', views.ClassTimeDeleteView.as_view(), name='class_time_delete'),
    
    # Classrooms (Rooms)
    path('classrooms/', views.ClassRoomListView.as_view(), name='classroom_list'),
    path('classrooms/add/', views.ClassRoomCreateView.as_view(), name='classroom_create'),
    path('classrooms/<int:pk>/edit/', views.ClassRoomUpdateView.as_view(), name='classroom_update'),
    path('classrooms/<int:pk>/delete/', views.ClassRoomDeleteView.as_view(), name='classroom_delete'),
    
    # Study Materials
    path('study-materials/', views.StudyMaterialListView.as_view(), name='study_materials'),
    path('study-materials/upload/', views.StudyMaterialUploadView.as_view(), name='study_material_upload'),
    
    # Assignments
    path('assignments/', views.AssignmentListView.as_view(), name='assignments'),
    path('assignments/create/', views.AssignmentCreateView.as_view(), name='assignment_create'),
    path('assignments/<int:pk>/', views.AssignmentDetailView.as_view(), name='assignment_detail'),
    
    # API endpoints
    path('api/teachers/', views.get_teachers_api, name='get_teachers'),
    path('api/sections/', views.get_sections_api, name='get_sections'),
    path('api/test/', views.test_api, name='test_api'),
]
