from django.db import models
from django.utils.translation import gettext_lazy as _


class Route(models.Model):
    """Transport Route Model"""
    name = models.CharField(_('Route Name'), max_length=200)
    route_number = models.CharField(_('Route Number'), max_length=50, unique=True)
    description = models.TextField(_('Description'), blank=True)
    fare = models.DecimalField(_('Fare'), max_digits=10, decimal_places=2, default=0)
    is_active = models.BooleanField(_('Is Active'), default=True)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('Route')
        verbose_name_plural = _('Routes')
        ordering = ['route_number']
    
    def __str__(self):
        return f"{self.route_number} - {self.name}"
