from django.urls import path
from . import views

app_name = 'dormitory'

urlpatterns = [
    path('', views.DormitoryListView.as_view(), name='dormitory_list'),
    path('rooms/', views.RoomListView.as_view(), name='rooms'),
]
