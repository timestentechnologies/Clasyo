from django.contrib import admin
from .models import School, Domain


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'phone', 'city', 'subscription_plan', 'is_active', 'created_on']
    list_filter = ['is_active', 'is_trial', 'is_verified', 'created_on']
    search_fields = ['name', 'email', 'phone', 'city']
    readonly_fields = ['created_on', 'updated_on']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'logo')
        }),
        ('Contact Information', {
            'fields': ('email', 'phone', 'address', 'city', 'state', 'country', 'postal_code', 'website')
        }),
        ('School Details', {
            'fields': ('established_date', 'registration_number')
        }),
        ('Subscription', {
            'fields': ('subscription_plan', 'subscription_start_date', 'subscription_end_date', 
                      'is_trial', 'trial_end_date')
        }),
        ('Limits', {
            'fields': ('max_students', 'max_teachers', 'max_staff')
        }),
        ('Settings', {
            'fields': ('academic_year_start_month', 'date_format', 'time_format', 
                      'currency', 'currency_symbol', 'timezone')
        }),
        ('Features', {
            'fields': ('enable_online_exam', 'enable_online_payment', 'enable_chat', 
                      'enable_sms', 'enable_library', 'enable_transport', 
                      'enable_dormitory', 'enable_inventory')
        }),
        ('Status', {
            'fields': ('is_active', 'is_verified', 'created_on', 'updated_on')
        }),
    )


@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    list_display = ['domain', 'school', 'is_primary', 'created_at']
    list_filter = ['is_primary', 'created_at']
    search_fields = ['domain', 'school__name']
