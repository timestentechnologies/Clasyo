from django.urls import path
from . import views
from .views import (
    GlobalAIConfigurationListView, GlobalAIConfigurationCreateView,
    GlobalAIConfigurationUpdateView, GlobalAIConfigurationDeleteView,
    SchoolAIConfigurationListView, SchoolAIConfigurationCreateView,
    SchoolAIConfigurationUpdateView, SchoolAIConfigurationDeleteView
)

urlpatterns = [
    # Global AI Configurations
    path('ai/config/global/', GlobalAIConfigurationListView.as_view(), name='ai_config_global_list'),
    path('ai/config/global/add/', GlobalAIConfigurationCreateView.as_view(), name='ai_config_global_add'),
    path('ai/config/global/<int:pk>/edit/', GlobalAIConfigurationUpdateView.as_view(), name='ai_config_global_edit'),
    path('ai/config/global/<int:pk>/delete/', GlobalAIConfigurationDeleteView.as_view(), name='ai_config_global_delete'),
    
    # School AI Configurations
    path('ai/config/school/', SchoolAIConfigurationListView.as_view(), name='ai_config_school_list'),
    path('ai/config/school/add/', SchoolAIConfigurationCreateView.as_view(), name='ai_config_school_add'),
    path('ai/config/school/<int:pk>/edit/', SchoolAIConfigurationUpdateView.as_view(), name='ai_config_school_edit'),
    path('ai/config/school/<int:pk>/delete/', SchoolAIConfigurationDeleteView.as_view(), name='ai_config_school_delete'),
]
