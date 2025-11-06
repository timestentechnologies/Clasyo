from django.urls import path
from . import views

app_name = 'communication'

urlpatterns = [
    path('notices/', views.NoticeListView.as_view(), name='notices'),
    path('messages/', views.MessageListView.as_view(), name='messages'),
    path('messages/send/', views.MessageSendView.as_view(), name='message_send'),
    path('recipients/<str:recipient_type>/', views.RecipientListView.as_view(), name='recipient_list'),
    path('messages/create/', views.MessageListView.as_view(), name='message_create'),
    path('messages/<int:pk>/', views.MessageDetailView.as_view(), name='message_detail'),
    path('messages/<int:pk>/delete/', views.MessageDeleteView.as_view(), name='message_delete'),
]
