from django.db import models
from django.utils.translation import gettext_lazy as _


class Department(models.Model):
    """Department model for HR"""
    name = models.CharField(_('Department Name'), max_length=200)
    code = models.CharField(_('Department Code'), max_length=50, unique=True)
    description = models.TextField(_('Description'), blank=True)
    head = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, 
                            null=True, blank=True, related_name='headed_departments')
    is_active = models.BooleanField(_('Is Active'), default=True)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Department')
        verbose_name_plural = _('Departments')
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Designation(models.Model):
    """Designation/Position model for HR"""
    name = models.CharField(_('Designation Name'), max_length=200)
    code = models.CharField(_('Designation Code'), max_length=50, unique=True)
    description = models.TextField(_('Description'), blank=True)
    level = models.IntegerField(_('Level'), default=1, help_text=_('Hierarchy level (1=highest)'))
    is_active = models.BooleanField(_('Is Active'), default=True)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Designation')
        verbose_name_plural = _('Designations')
        ordering = ['level', 'name']
    
    def __str__(self):
        return self.name
