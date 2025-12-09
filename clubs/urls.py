from django.urls import path
from . import views

app_name = 'clubs'

urlpatterns = [
    # Dashboard and overview
    path('', views.club_dashboard, name='dashboard'),
    
    # Club management
    path('list/', views.ClubListView.as_view(), name='club_list'),
    path('create/', views.ClubCreateView.as_view(), name='club_create'),
    path('<int:pk>/', views.ClubDetailView.as_view(), name='club_detail'),
    path('<int:pk>/edit/', views.ClubUpdateView.as_view(), name='club_edit'),
    path('<int:pk>/delete/', views.ClubDeleteView.as_view(), name='club_delete'),
    
    # Membership management
    path('<int:club_id>/join/', views.join_club, name='join_club'),
    path('<int:club_id>/leave/', views.leave_club, name='leave_club'),
    path('<int:club_id>/members/', views.manage_memberships, name='manage_memberships'),
    
    # Student's clubs
    path('my-clubs/', views.MyClubsView.as_view(), name='my_clubs'),
    
    # Activities
    path('<int:club_id>/activities/', views.ClubActivityListView.as_view(), name='activity_list'),
]
