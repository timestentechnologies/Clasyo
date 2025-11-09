from django.contrib import admin
from .models import Route, RouteStop, Vehicle, Driver, StudentTransport

# Register your models here

class RouteStopInline(admin.TabularInline):
    model = RouteStop
    extra = 1
    fields = ['stop_order', 'name', 'address', 'pickup_time', 'dropoff_time', 'fare_from_start']

@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = ['route_number', 'name', 'start_place', 'end_place', 'distance', 'fare', 'is_active']
    list_filter = ['is_active', 'school']
    search_fields = ['route_number', 'name', 'start_place', 'end_place']
    inlines = [RouteStopInline]

@admin.register(RouteStop)
class RouteStopAdmin(admin.ModelAdmin):
    list_display = ['route', 'stop_order', 'name', 'pickup_time', 'dropoff_time']
    list_filter = ['route']
    ordering = ['route', 'stop_order']

@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ['vehicle_number', 'vehicle_model', 'vehicle_type', 'capacity', 'route', 'is_active']
    list_filter = ['vehicle_type', 'is_active', 'school']
    search_fields = ['vehicle_number', 'vehicle_model', 'registration_number']

@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = ['name', 'phone', 'license_number', 'license_expiry', 'vehicle', 'is_active']
    list_filter = ['is_active', 'school']
    search_fields = ['name', 'phone', 'license_number']

@admin.register(StudentTransport)
class StudentTransportAdmin(admin.ModelAdmin):
    list_display = ['student', 'route', 'stop', 'vehicle', 'monthly_fee', 'is_active']
    list_filter = ['route', 'is_active']
    search_fields = ['student__first_name', 'student__last_name', 'student__admission_number']
    raw_id_fields = ['student']
