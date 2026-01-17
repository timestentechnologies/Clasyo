from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import gettext_lazy as _
from phonenumber_field.modelfields import PhoneNumberField
from django_countries.fields import CountryField


class UserManager(BaseUserManager):
    """Custom user manager"""
    
    def create_user(self, email, password=None, **extra_fields):
        """Create and return a regular user"""
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        """Create and return a superuser"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('role', 'superadmin')
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Custom User Model"""
    ROLE_CHOICES = [
        ('superadmin', 'Super Admin'),
        ('admin', 'School Admin'),
        ('teacher', 'Teacher'),
        ('accountant', 'Accountant'),
        ('librarian', 'Librarian'),
        ('receptionist', 'Receptionist'),
        ('parent', 'Parent'),
        ('student', 'Student'),
    ]
    
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ]
    
    username = None
    email = models.EmailField(_('Email Address'), unique=True)
    
    # Role and Permissions
    role = models.CharField(_('Role'), max_length=20, choices=ROLE_CHOICES)
    
    # Personal Information
    first_name = models.CharField(_('First Name'), max_length=150)
    last_name = models.CharField(_('Last Name'), max_length=150)
    phone = PhoneNumberField(_('Phone Number'), blank=True, null=True)
    mobile = PhoneNumberField(_('Mobile Number'), blank=True, null=True)
    
    # Profile
    avatar = models.ImageField(_('Avatar'), upload_to='avatars/', blank=True, null=True)
    gender = models.CharField(_('Gender'), max_length=10, choices=GENDER_CHOICES, blank=True)
    date_of_birth = models.DateField(_('Date of Birth'), blank=True, null=True)
    blood_group = models.CharField(_('Blood Group'), max_length=10, blank=True)
    
    # Address
    address = models.TextField(_('Address'), blank=True)
    city = models.CharField(_('City'), max_length=100, blank=True)
    state = models.CharField(_('State'), max_length=100, blank=True)
    country = CountryField(_('Country'), blank=True)
    postal_code = models.CharField(_('Postal Code'), max_length=20, blank=True)
    
    # Emergency Contact
    emergency_contact_name = models.CharField(_('Emergency Contact Name'), max_length=150, blank=True)
    emergency_contact_phone = PhoneNumberField(_('Emergency Contact Phone'), blank=True, null=True)
    emergency_contact_relation = models.CharField(_('Emergency Contact Relation'), max_length=50, blank=True)
    
    # Employment (for staff)
    employee_id = models.CharField(_('Employee ID'), max_length=50, blank=True, unique=True, null=True)
    department = models.ForeignKey('human_resource.Department', on_delete=models.SET_NULL, 
                                  null=True, blank=True, related_name='employees')
    designation = models.ForeignKey('human_resource.Designation', on_delete=models.SET_NULL, 
                                   null=True, blank=True, related_name='employees')
    school = models.ForeignKey('tenants.School', on_delete=models.SET_NULL, 
                               null=True, blank=True, related_name='admins')
    join_date = models.DateField(_('Join Date'), blank=True, null=True)
    
    # Status
    is_active = models.BooleanField(_('Active'), default=True)
    is_verified = models.BooleanField(_('Verified'), default=False)
    
    # Metadata
    last_login_ip = models.GenericIPAddressField(_('Last Login IP'), blank=True, null=True)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'role']
    
    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.get_role_display()})"
    
    def get_full_name(self):
        """Return the full name of the user"""
        return f"{self.first_name} {self.last_name}".strip()
    
    def get_short_name(self):
        """Return the short name of the user"""
        return self.first_name
    
    @property
    def is_superadmin(self):
        return self.role == 'superadmin'
    
    @property
    def is_school_admin(self):
        return self.role == 'admin'
    
    @property
    def is_teacher(self):
        return self.role == 'teacher'
    
    @property
    def is_parent(self):
        return self.role == 'parent'
    
    @property
    def is_student(self):
        return self.role == 'student'
    
    @property
    def is_staff_member(self):
        return self.role in ['admin', 'teacher', 'accountant', 'librarian', 'receptionist']


class Role(models.Model):
    """Custom Role Model for fine-grained permissions"""
    name = models.CharField(_('Role Name'), max_length=100, unique=True)
    slug = models.SlugField(_('Slug'), unique=True)
    description = models.TextField(_('Description'), blank=True)
    
    # Permissions (stored as JSON)
    permissions = models.JSONField(_('Permissions'), default=dict, blank=True)
    
    # Status
    is_active = models.BooleanField(_('Is Active'), default=True)
    is_system_role = models.BooleanField(_('Is System Role'), default=False)
    
    # Metadata
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Role')
        verbose_name_plural = _('Roles')
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Permission(models.Model):
    """Permission Model"""
    MODULE_CHOICES = [
        ('students', 'Students'),
        ('academics', 'Academics'),
        ('fees', 'Fees'),
        ('examinations', 'Examinations'),
        ('homework', 'Homework'),
        ('hr', 'Human Resource'),
        ('leave', 'Leave Management'),
        ('communication', 'Communication'),
        ('library', 'Library'),
        ('inventory', 'Inventory'),
        ('transport', 'Transport'),
        ('dormitory', 'Dormitory'),
        ('reports', 'Reports'),
        ('settings', 'Settings'),
    ]
    
    module = models.CharField(_('Module'), max_length=50, choices=MODULE_CHOICES)
    name = models.CharField(_('Permission Name'), max_length=100)
    slug = models.SlugField(_('Slug'), unique=True)
    description = models.TextField(_('Description'), blank=True)
    
    # Permission Type
    can_view = models.BooleanField(_('Can View'), default=False)
    can_add = models.BooleanField(_('Can Add'), default=False)
    can_edit = models.BooleanField(_('Can Edit'), default=False)
    can_delete = models.BooleanField(_('Can Delete'), default=False)
    
    # Metadata
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('Permission')
        verbose_name_plural = _('Permissions')
        ordering = ['module', 'name']
    
    def __str__(self):
        return f"{self.get_module_display()} - {self.name}"


class UserLoginLog(models.Model):
    """User Login Log Model"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='login_logs')
    ip_address = models.GenericIPAddressField(_('IP Address'))
    user_agent = models.TextField(_('User Agent'), blank=True)
    login_time = models.DateTimeField(_('Login Time'), auto_now_add=True)
    logout_time = models.DateTimeField(_('Logout Time'), blank=True, null=True)
    session_duration = models.DurationField(_('Session Duration'), blank=True, null=True)
    
    class Meta:
        verbose_name = _('User Login Log')
        verbose_name_plural = _('User Login Logs')
        ordering = ['-login_time']
    
    def __str__(self):
        return f"{self.user.email} - {self.login_time}"
