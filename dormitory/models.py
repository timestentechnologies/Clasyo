from django.db import models
from django.utils.translation import gettext_lazy as _
from tenants.models import School
from students.models import Student


class Dormitory(models.Model):
    """Dormitory/Hostel Model"""
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='dormitories', null=True, blank=True)
    name = models.CharField(_('Dormitory Name'), max_length=200)
    dormitory_type = models.CharField(_('Type'), max_length=20, 
                                     choices=[('boys', 'Boys'), ('girls', 'Girls'), ('mixed', 'Mixed')])
    address = models.TextField(_('Address'), blank=True)
    description = models.TextField(_('Description'), blank=True)
    total_capacity = models.IntegerField(_('Total Capacity'), default=0)
    is_active = models.BooleanField(_('Is Active'), default=True)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Dormitory')
        verbose_name_plural = _('Dormitories')
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def get_total_rooms(self):
        return self.rooms.count()
    
    def get_occupied_rooms(self):
        return self.rooms.filter(current_occupancy__gt=0).count()
    
    def get_occupancy_percentage(self):
        if self.total_capacity > 0:
            occupied = RoomAllocation.objects.filter(room__dormitory=self, is_active=True).count()
            return (occupied / self.total_capacity) * 100
        return 0


class Room(models.Model):
    """Dormitory Room Model"""
    dormitory = models.ForeignKey(Dormitory, on_delete=models.CASCADE, related_name='rooms')
    room_number = models.CharField(_('Room Number'), max_length=50)
    capacity = models.IntegerField(_('Capacity'), default=1)
    current_occupancy = models.IntegerField(_('Current Occupancy'), default=0)
    room_type = models.CharField(_('Room Type'), max_length=50, blank=True)
    floor = models.IntegerField(_('Floor Number'), default=1, blank=True)
    is_active = models.BooleanField(_('Is Active'), default=True)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Room')
        verbose_name_plural = _('Rooms')
        ordering = ['dormitory', 'room_number']
        unique_together = ['dormitory', 'room_number']
    
    def __str__(self):
        return f"{self.dormitory.name} - Room {self.room_number}"
    
    def is_full(self):
        return self.current_occupancy >= self.capacity
    
    def available_beds(self):
        return max(0, self.capacity - self.current_occupancy)


class RoomAllocation(models.Model):
    """Student Room Allocation Model"""
    student = models.OneToOneField(Student, on_delete=models.CASCADE, related_name='room_allocation')
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='allocations')
    bed_number = models.CharField(_('Bed Number'), max_length=20, blank=True)
    monthly_fee = models.DecimalField(_('Monthly Dormitory Fee'), max_digits=10, decimal_places=2)
    start_date = models.DateField(_('Allocation Start Date'))
    end_date = models.DateField(_('Allocation End Date'), null=True, blank=True)
    is_active = models.BooleanField(_('Is Active'), default=True)
    remarks = models.TextField(_('Remarks'), blank=True)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Room Allocation')
        verbose_name_plural = _('Room Allocations')
        ordering = ['room', 'student']
    
    def __str__(self):
        return f"{self.student.get_full_name()} - {self.room}"
    
    def save(self, *args, **kwargs):
        # Update room occupancy
        if self.pk is None:  # New allocation
            self.room.current_occupancy += 1
            self.room.save()
        super().save(*args, **kwargs)
