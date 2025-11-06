from django.db import models
from django.utils.translation import gettext_lazy as _


class Dormitory(models.Model):
    """Dormitory/Hostel Model"""
    name = models.CharField(_('Dormitory Name'), max_length=200)
    dormitory_type = models.CharField(_('Type'), max_length=20, 
                                     choices=[('boys', 'Boys'), ('girls', 'Girls'), ('mixed', 'Mixed')])
    description = models.TextField(_('Description'), blank=True)
    total_capacity = models.IntegerField(_('Total Capacity'), default=0)
    is_active = models.BooleanField(_('Is Active'), default=True)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('Dormitory')
        verbose_name_plural = _('Dormitories')
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Room(models.Model):
    """Dormitory Room Model"""
    dormitory = models.ForeignKey(Dormitory, on_delete=models.CASCADE, related_name='rooms')
    room_number = models.CharField(_('Room Number'), max_length=50)
    capacity = models.IntegerField(_('Capacity'), default=1)
    current_occupancy = models.IntegerField(_('Current Occupancy'), default=0)
    room_type = models.CharField(_('Room Type'), max_length=50, blank=True)
    is_active = models.BooleanField(_('Is Active'), default=True)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('Room')
        verbose_name_plural = _('Rooms')
        ordering = ['dormitory', 'room_number']
        unique_together = ['dormitory', 'room_number']
    
    def __str__(self):
        return f"{self.dormitory.name} - Room {self.room_number}"
