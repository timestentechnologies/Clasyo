from django.db import models
from django.utils.translation import gettext_lazy as _
from tenants.models import School
from students.models import Student
from accounts.models import User


class Route(models.Model):
    """Transport Route Model"""
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='transport_routes')
    name = models.CharField(_('Route Name'), max_length=200)
    route_number = models.CharField(_('Route Number'), max_length=50)
    start_place = models.CharField(_('Start Place'), max_length=200)
    end_place = models.CharField(_('End Place'), max_length=200)
    distance = models.DecimalField(_('Distance (km)'), max_digits=10, decimal_places=2, default=0)
    description = models.TextField(_('Description'), blank=True)
    fare = models.DecimalField(_('Monthly Fare'), max_digits=10, decimal_places=2, default=0)
    is_active = models.BooleanField(_('Is Active'), default=True)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Route')
        verbose_name_plural = _('Routes')
        ordering = ['route_number']
        unique_together = ['school', 'route_number']
    
    def __str__(self):
        return f"{self.route_number} - {self.name}"
    
    def get_total_stops(self):
        return self.stops.count()
    
    def get_assigned_students(self):
        return StudentTransport.objects.filter(route=self).count()


class RouteStop(models.Model):
    """Route Stop/Station Model"""
    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name='stops')
    name = models.CharField(_('Stop Name'), max_length=200)
    address = models.TextField(_('Address'), blank=True)
    stop_order = models.IntegerField(_('Stop Order'))
    pickup_time = models.TimeField(_('Pickup Time'))
    dropoff_time = models.TimeField(_('Drop-off Time'))
    fare_from_start = models.DecimalField(_('Fare from Start'), max_digits=10, decimal_places=2, default=0)
    
    class Meta:
        verbose_name = _('Route Stop')
        verbose_name_plural = _('Route Stops')
        ordering = ['route', 'stop_order']
        unique_together = ['route', 'stop_order']
    
    def __str__(self):
        return f"{self.name} (Stop #{self.stop_order})"


class Vehicle(models.Model):
    """Vehicle Model"""
    VEHICLE_TYPE_CHOICES = [
        ('bus', 'Bus'),
        ('van', 'Van'),
        ('minibus', 'Minibus'),
        ('car', 'Car'),
    ]
    
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='vehicles')
    vehicle_number = models.CharField(_('Vehicle Number'), max_length=50)
    vehicle_model = models.CharField(_('Vehicle Model'), max_length=100)
    vehicle_type = models.CharField(_('Vehicle Type'), max_length=20, choices=VEHICLE_TYPE_CHOICES, default='bus')
    capacity = models.IntegerField(_('Seating Capacity'))
    registration_number = models.CharField(_('Registration Number'), max_length=100, blank=True)
    insurance_expiry = models.DateField(_('Insurance Expiry'), null=True, blank=True)
    fitness_certificate_expiry = models.DateField(_('Fitness Certificate Expiry'), null=True, blank=True)
    route = models.ForeignKey(Route, on_delete=models.SET_NULL, null=True, blank=True, related_name='vehicles')
    is_active = models.BooleanField(_('Is Active'), default=True)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Vehicle')
        verbose_name_plural = _('Vehicles')
        ordering = ['vehicle_number']
        unique_together = ['school', 'vehicle_number']
    
    def __str__(self):
        return f"{self.vehicle_number} - {self.vehicle_model}"


class Driver(models.Model):
    """Driver Model"""
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='drivers')
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='driver_profile')
    name = models.CharField(_('Driver Name'), max_length=200)
    phone = models.CharField(_('Phone Number'), max_length=20)
    license_number = models.CharField(_('License Number'), max_length=100)
    license_expiry = models.DateField(_('License Expiry'))
    address = models.TextField(_('Address'), blank=True)
    vehicle = models.ForeignKey(Vehicle, on_delete=models.SET_NULL, null=True, blank=True, related_name='drivers')
    is_active = models.BooleanField(_('Is Active'), default=True)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Driver')
        verbose_name_plural = _('Drivers')
        ordering = ['name']
    
    def __str__(self):
        return self.name


class StudentTransport(models.Model):
    """Student Transport Assignment Model"""
    student = models.OneToOneField(Student, on_delete=models.CASCADE, related_name='transport')
    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name='student_assignments')
    stop = models.ForeignKey(RouteStop, on_delete=models.SET_NULL, null=True, blank=True, related_name='students')
    vehicle = models.ForeignKey(Vehicle, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_students')
    monthly_fee = models.DecimalField(_('Monthly Transport Fee'), max_digits=10, decimal_places=2)
    is_active = models.BooleanField(_('Is Active'), default=True)
    start_date = models.DateField(_('Start Date'))
    end_date = models.DateField(_('End Date'), null=True, blank=True)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Student Transport')
        verbose_name_plural = _('Student Transport Assignments')
        ordering = ['route', 'stop__stop_order']
    
    def __str__(self):
        return f"{self.student.get_full_name()} - {self.route.name}"
