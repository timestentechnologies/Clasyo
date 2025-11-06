from django.contrib import admin
from .models import (
    AcademicYear, Session, Holiday, Weekend, SystemSetting,
    Notification, ToDoList, CalendarEvent
)


@admin.register(AcademicYear)
class AcademicYearAdmin(admin.ModelAdmin):
    list_display = ['name', 'start_date', 'end_date', 'is_active', 'created_at']
    list_filter = ['is_active', 'start_date']
    search_fields = ['name']


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ['name', 'academic_year', 'start_date', 'end_date', 'is_active']
    list_filter = ['academic_year', 'is_active']
    search_fields = ['name']


@admin.register(Holiday)
class HolidayAdmin(admin.ModelAdmin):
    list_display = ['title', 'holiday_type', 'from_date', 'to_date', 'is_active']
    list_filter = ['holiday_type', 'is_active', 'from_date']
    search_fields = ['title', 'description']


@admin.register(Weekend)
class WeekendAdmin(admin.ModelAdmin):
    list_display = ['day', 'get_day_display', 'is_weekend']
    list_filter = ['is_weekend']


@admin.register(SystemSetting)
class SystemSettingAdmin(admin.ModelAdmin):
    fieldsets = (
        ('School Information', {
            'fields': ('school_name', 'school_code', 'school_email', 'school_phone', 'school_address')
        }),
        ('Branding', {
            'fields': ('school_logo', 'school_favicon')
        }),
        ('Academic Settings', {
            'fields': ('promote_without_exam',)
        }),
        ('Format Settings', {
            'fields': ('date_format', 'time_format', 'timezone', 'currency_code', 'currency_symbol')
        }),
        ('Features', {
            'fields': ('enable_online_admission', 'enable_email_notification', 'enable_sms_notification')
        }),
        ('Social Media', {
            'fields': ('facebook_url', 'twitter_url', 'instagram_url', 'linkedin_url', 'youtube_url')
        }),
        ('System Settings', {
            'fields': ('session_timeout', 'default_language', 'auto_backup', 'backup_time')
        }),
    )


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'notification_type', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['title', 'message', 'user__email']


@admin.register(ToDoList)
class ToDoListAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'priority', 'due_date', 'is_completed', 'created_at']
    list_filter = ['priority', 'is_completed', 'due_date']
    search_fields = ['title', 'description']


@admin.register(CalendarEvent)
class CalendarEventAdmin(admin.ModelAdmin):
    list_display = ['title', 'event_type', 'start_date', 'end_date', 'created_by', 'is_public']
    list_filter = ['event_type', 'is_public', 'start_date']
    search_fields = ['title', 'description']
    filter_horizontal = ['participants']
