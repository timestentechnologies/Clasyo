from django.contrib import admin
from .models import SubscriptionPlan, Subscription, Payment, Coupon


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'plan_type', 'price', 'billing_cycle', 'is_active', 'is_popular']
    list_filter = ['plan_type', 'billing_cycle', 'is_active', 'is_popular']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'plan_type', 'description')
        }),
        ('Pricing', {
            'fields': ('price', 'billing_cycle', 'trial_days')
        }),
        ('Limits', {
            'fields': ('max_students', 'max_teachers', 'max_staff', 'max_branches', 'storage_limit_gb')
        }),
        ('Features', {
            'fields': ('enable_online_exam', 'enable_online_payment', 'enable_chat', 
                      'enable_sms', 'enable_library', 'enable_transport', 'enable_dormitory', 
                      'enable_inventory', 'enable_hr', 'enable_reports', 'features')
        }),
        ('Display', {
            'fields': ('is_active', 'is_popular', 'display_order')
        }),
    )


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ['school', 'plan', 'start_date', 'end_date', 'status', 'is_trial', 'auto_renew']
    list_filter = ['status', 'is_trial', 'auto_renew', 'created_at']
    search_fields = ['school__name', 'plan__name']
    date_hierarchy = 'start_date'


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['payment_id', 'subscription', 'amount', 'currency', 'payment_method', 
                   'status', 'payment_date']
    list_filter = ['status', 'payment_method', 'created_at']
    search_fields = ['payment_id', 'transaction_id', 'invoice_number', 'subscription__school__name']
    readonly_fields = ['payment_id', 'invoice_number', 'invoice_date', 'created_at', 'updated_at']
    date_hierarchy = 'payment_date'


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ['code', 'discount_type', 'discount_value', 'valid_from', 'valid_until', 
                   'times_used', 'is_active']
    list_filter = ['discount_type', 'is_active', 'valid_from', 'valid_until']
    search_fields = ['code', 'description']
    filter_horizontal = ['applicable_plans']
