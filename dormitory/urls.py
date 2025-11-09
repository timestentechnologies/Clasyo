from django.urls import path
from . import views

app_name = 'dormitory'

urlpatterns = [
    path('', views.DormitoryListView.as_view(), name='dormitory_list'),
    path('rooms/', views.RoomListView.as_view(), name='rooms'),
    path('allocations/', views.RoomAllocationListView.as_view(), name='allocations'),
    path('allocations/add/', views.AllocateRoomView.as_view(), name='allocate_room'),
    path('reports/occupancy/', views.OccupancyReportView.as_view(), name='occupancy_report'),
]
