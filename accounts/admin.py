from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User, Role, Permission, UserLoginLog


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['email', 'first_name', 'last_name', 'role', 'is_active', 'is_verified', 'created_at']
    list_filter = ['role', 'is_active', 'is_verified', 'gender', 'created_at']
    search_fields = ['email', 'first_name', 'last_name', 'employee_id']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at', 'last_login', 'last_login_ip']
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal Info'), {
            'fields': ('first_name', 'last_name', 'avatar', 'gender', 'date_of_birth', 'blood_group')
        }),
        (_('Contact Information'), {
            'fields': ('phone', 'mobile', 'address', 'city', 'state', 'country', 'postal_code')
        }),
        (_('Emergency Contact'), {
            'fields': ('emergency_contact_name', 'emergency_contact_phone', 'emergency_contact_relation')
        }),
        (_('Role & Employment'), {
            'fields': ('role', 'employee_id', 'department', 'designation', 'join_date')
        }),
        (_('Permissions'), {
            'fields': ('is_active', 'is_verified', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Important dates'), {
            'fields': ('last_login', 'last_login_ip', 'created_at', 'updated_at')
        }),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'first_name', 'last_name', 'role', 'is_active'),
        }),
    )


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'is_active', 'is_system_role', 'created_at']
    list_filter = ['is_active', 'is_system_role', 'created_at']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ['name', 'module', 'can_view', 'can_add', 'can_edit', 'can_delete']
    list_filter = ['module', 'can_view', 'can_add', 'can_edit', 'can_delete']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(UserLoginLog)
class UserLoginLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'ip_address', 'login_time', 'logout_time', 'session_duration']
    list_filter = ['login_time']
    search_fields = ['user__email', 'ip_address']
    readonly_fields = ['user', 'ip_address', 'user_agent', 'login_time', 'logout_time', 'session_duration']
    date_hierarchy = 'login_time'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
