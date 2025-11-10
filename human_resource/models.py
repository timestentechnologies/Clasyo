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


class Teacher(models.Model):
    """Teacher Model with Salary Information"""
    user = models.OneToOneField('accounts.User', on_delete=models.CASCADE, related_name='teacher_profile')
    first_name = models.CharField(_('First Name'), max_length=150)
    last_name = models.CharField(_('Last Name'), max_length=150)
    employee_id = models.CharField(_('Employee ID'), max_length=50, unique=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='teachers')
    designation = models.ForeignKey(Designation, on_delete=models.SET_NULL, null=True, blank=True, related_name='teachers')
    
    # Salary Information
    basic_salary = models.DecimalField(_('Basic Salary'), max_digits=10, decimal_places=2, default=0)
    allowances = models.DecimalField(_('Allowances'), max_digits=10, decimal_places=2, default=0, 
                                     help_text=_('Transport, housing, medical allowances, etc.'))
    
    # Employment Details
    date_of_joining = models.DateField(_('Date of Joining'))
    employment_type = models.CharField(_('Employment Type'), max_length=50, 
                                       choices=[('permanent', 'Permanent'), ('contract', 'Contract'), ('temporary', 'Temporary')],
                                       default='permanent')
    
    # Contact
    phone = models.CharField(_('Phone Number'), max_length=20, blank=True)
    email = models.EmailField(_('Email'), blank=True)
    address = models.TextField(_('Address'), blank=True)
    
    # Status
    is_active = models.BooleanField(_('Is Active'), default=True)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Teacher')
        verbose_name_plural = _('Teachers')
        ordering = ['first_name', 'last_name']
    
    def __str__(self):
        return f"{self.first_name} {self.last_name}"
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    @property
    def gross_salary(self):
        return self.basic_salary + self.allowances


class Staff(models.Model):
    """Non-Teaching Staff Model with Salary Information"""
    user = models.OneToOneField('accounts.User', on_delete=models.CASCADE, related_name='staff_profile')
    first_name = models.CharField(_('First Name'), max_length=150)
    last_name = models.CharField(_('Last Name'), max_length=150)
    employee_id = models.CharField(_('Employee ID'), max_length=50, unique=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='staff')
    designation = models.ForeignKey(Designation, on_delete=models.SET_NULL, null=True, blank=True, related_name='staff')
    
    # Salary Information
    basic_salary = models.DecimalField(_('Basic Salary'), max_digits=10, decimal_places=2, default=0)
    allowances = models.DecimalField(_('Allowances'), max_digits=10, decimal_places=2, default=0,
                                     help_text=_('Transport, housing, medical allowances, etc.'))
    
    # Employment Details
    date_of_joining = models.DateField(_('Date of Joining'))
    employment_type = models.CharField(_('Employment Type'), max_length=50,
                                       choices=[('permanent', 'Permanent'), ('contract', 'Contract'), ('temporary', 'Temporary')],
                                       default='permanent')
    
    # Contact
    phone = models.CharField(_('Phone Number'), max_length=20, blank=True)
    email = models.EmailField(_('Email'), blank=True)
    address = models.TextField(_('Address'), blank=True)
    
    # Status
    is_active = models.BooleanField(_('Is Active'), default=True)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Staff')
        verbose_name_plural = _('Staff')
        ordering = ['first_name', 'last_name']
    
    def __str__(self):
        return f"{self.first_name} {self.last_name}"
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    @property
    def gross_salary(self):
        return self.basic_salary + self.allowances
