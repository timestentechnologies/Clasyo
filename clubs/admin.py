from django.contrib import admin
from .models import Club, ClubMembership, ClubActivity, ClubAttendance, ClubAchievement, ClubResource

@admin.register(Club)
class ClubAdmin(admin.ModelAdmin):
    list_display = ['name', 'club_type', 'school', 'teacher_advisor', 'is_active', 'created_at']
    list_filter = ['club_type', 'is_active', 'created_at', 'school']
    search_fields = ['name', 'description', 'school__name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'club_type', 'school', 'is_active')
        }),
        ('Leadership', {
            'fields': ('teacher_advisor', 'student_president', 'student_secretary')
        }),
        ('Meeting Details', {
            'fields': ('meeting_day', 'meeting_time', 'meeting_venue')
        }),
        ('Membership Settings', {
            'fields': ('max_members', 'membership_fee', 'requires_application', 'application_deadline')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

@admin.register(ClubMembership)
class ClubMembershipAdmin(admin.ModelAdmin):
    list_display = ['student', 'club', 'status', 'application_date', 'join_date', 'fee_paid']
    list_filter = ['status', 'fee_paid', 'application_date', 'club__club_type']
    search_fields = ['student__first_name', 'student__last_name', 'club__name']
    readonly_fields = ['application_date', 'updated_at']
    
    fieldsets = (
        ('Membership Details', {
            'fields': ('student', 'club', 'status', 'join_date')
        }),
        ('Application', {
            'fields': ('application_reason', 'parent_consent')
        }),
        ('Financial', {
            'fields': ('fee_paid', 'fee_paid_date', 'fee_amount_paid')
        }),
        ('Position', {
            'fields': ('position_held',)
        }),
        ('Timestamps', {
            'fields': ('application_date', 'updated_at'),
            'classes': ('collapse',)
        })
    )

@admin.register(ClubActivity)
class ClubActivityAdmin(admin.ModelAdmin):
    list_display = ['title', 'club', 'activity_type', 'date', 'venue', 'is_cancelled']
    list_filter = ['activity_type', 'is_cancelled', 'date', 'club__club_type']
    search_fields = ['title', 'description', 'club__name', 'venue']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'date'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('club', 'title', 'description', 'activity_type')
        }),
        ('Schedule', {
            'fields': ('date', 'duration', 'venue')
        }),
        ('Participation', {
            'fields': ('max_participants', 'is_mandatory', 'points_awarded')
        }),
        ('Status', {
            'fields': ('is_cancelled', 'cancellation_reason')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

@admin.register(ClubAttendance)
class ClubAttendanceAdmin(admin.ModelAdmin):
    list_display = ['student', 'activity', 'status', 'check_in_time']
    list_filter = ['status', 'activity__activity_type', 'activity__date']
    search_fields = ['student__first_name', 'student__last_name', 'activity__title']
    readonly_fields = ['created_at']

@admin.register(ClubAchievement)
class ClubAchievementAdmin(admin.ModelAdmin):
    list_display = ['title', 'club', 'achievement_type', 'date_achieved', 'level']
    list_filter = ['achievement_type', 'date_achieved', 'level', 'club__club_type']
    search_fields = ['title', 'description', 'club__name', 'level']
    readonly_fields = ['created_at']
    date_hierarchy = 'date_achieved'
    
    fieldsets = (
        ('Achievement Details', {
            'fields': ('club', 'title', 'description', 'achievement_type', 'date_achieved', 'level')
        }),
        ('Participants', {
            'fields': ('participants',)
        }),
        ('Documentation', {
            'fields': ('certificate', 'photos')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )

@admin.register(ClubResource)
class ClubResourceAdmin(admin.ModelAdmin):
    list_display = ['title', 'club', 'resource_type', 'is_public', 'uploaded_by', 'created_at']
    list_filter = ['resource_type', 'is_public', 'created_at', 'club__club_type']
    search_fields = ['title', 'description', 'club__name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Resource Details', {
            'fields': ('club', 'title', 'description', 'resource_type')
        }),
        ('Content', {
            'fields': ('file', 'url')
        }),
        ('Access', {
            'fields': ('is_public', 'uploaded_by')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
