from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # Dashboard
    path('', views.DashboardView.as_view(), name='dashboard'),
    
    # Notifications
    path('notifications/', views.NotificationListView.as_view(), name='notifications'),
    path('notifications/<int:pk>/mark-read/', views.MarkNotificationReadView.as_view(), name='mark_notification_read'),
    path('notifications/mark-all-read/', views.MarkAllNotificationsReadView.as_view(), name='mark_all_notifications_read'),
    
    # To-Do List
    path('todos/', views.ToDoListView.as_view(), name='todos'),
    path('todos/add/', views.ToDoCreateView.as_view(), name='todo_create'),
    path('todos/<int:pk>/toggle/', views.ToDoToggleView.as_view(), name='todo_toggle'),
    path('todos/<int:pk>/delete/', views.ToDoDeleteView.as_view(), name='todo_delete'),
    
    # Calendar
    path('calendar/', views.CalendarView.as_view(), name='calendar'),
    path('calendar/events/', views.CalendarEventListView.as_view(), name='calendar_events'),
    path('calendar/events/add/', views.CalendarEventCreateView.as_view(), name='calendar_event_create'),
    path('calendar/events/<int:pk>/delete/', views.CalendarEventDeleteView.as_view(), name='calendar_event_delete'),
    
    # Events
    path('events/', views.EventsView.as_view(), name='events'),
    
    # Profile and Settings
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('search/', views.SearchView.as_view(), name='search'),
    
    # Settings
    path('settings/', views.SystemSettingsView.as_view(), name='settings'),
    path('settings/update/', views.SystemSettingsUpdateView.as_view(), name='settings_update'),
    
    # Academic Year
    path('academic-years/', views.AcademicYearListView.as_view(), name='academic_years'),
    path('academic-years/add/', views.AcademicYearCreateView.as_view(), name='academic_year_create'),
    path('academic-years/<int:pk>/edit/', views.AcademicYearUpdateView.as_view(), name='academic_year_update'),
    path('academic-years/<int:pk>/delete/', views.AcademicYearDeleteView.as_view(), name='academic_year_delete'),
    path('academic-years/<int:year_id>/terms/', views.SessionListView.as_view(), name='session_list'),
    path('academic-years/terms/add/', views.SessionCreateView.as_view(), name='session_create'),
    path('academic-years/terms/<int:pk>/delete/', views.SessionDeleteView.as_view(), name='session_delete'),
    
    # Holidays
    path('holidays/', views.HolidayListView.as_view(), name='holidays'),
    path('holidays/add/', views.HolidayCreateView.as_view(), name='holiday_create'),
    
    # Impersonation (Login As)
    path('login-as/<int:user_id>/', views.LoginAsView.as_view(), name='login_as'),
    path('stop-impersonation/', views.StopImpersonationView.as_view(), name='stop_impersonation'),
]
