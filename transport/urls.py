from django.urls import path
from . import views

app_name = 'transport'

urlpatterns = [
    path('routes/', views.RouteListView.as_view(), name='routes'),
    path('vehicles/', views.VehicleListView.as_view(), name='vehicles'),
]
