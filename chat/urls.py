from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    # Dashboard
    path('', views.ChatDashboardView.as_view(), name='dashboard'),
    path('groups/', views.ChatGroupListView.as_view(), name='group_list'),
    
    # Chat Group Management
    path('groups/create/', views.ChatGroupCreateView.as_view(), name='group_create'),
    path('groups/<int:pk>/', views.ChatGroupDetailView.as_view(), name='group_detail'),
    path('groups/<int:pk>/update/', views.ChatGroupUpdateView.as_view(), name='group_update'),
    path('groups/<int:pk>/delete/', views.ChatGroupDeleteView.as_view(), name='group_delete'),
    
    # Group Membership
    path('groups/<int:group_id>/members/', views.ChatGroupMemberListView.as_view(), name='group_members'),
    path('groups/<int:group_id>/join/', views.ChatGroupJoinView.as_view(), name='group_join'),
    path('groups/<int:group_id>/leave/', views.ChatGroupLeaveView.as_view(), name='group_leave'),
    path('groups/<int:group_id>/invite/', views.ChatGroupInviteView.as_view(), name='group_invite'),
    path('invitations/<int:invitation_id>/accept/', views.ChatGroupAcceptInvitationView.as_view(), name='accept_invitation'),
    
    # Messages
    path('groups/<int:group_id>/messages/create/', views.ChatMessageCreateView.as_view(), name='message_create'),
    path('messages/<int:pk>/delete/', views.ChatMessageDeleteView.as_view(), name='message_delete'),
]
