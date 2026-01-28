from django.contrib import admin
from .models import (
    PaymentConfiguration, SchoolPaymentConfiguration,
    GlobalAIConfiguration, SchoolAIConfiguration,
)


@admin.register(PaymentConfiguration)
class PaymentConfigurationAdmin(admin.ModelAdmin):
    """Admin configuration for PaymentConfiguration"""
    list_display = ['gateway', 'environment', 'is_active', 'created_at', 'updated_at']
    list_filter = ['gateway', 'environment', 'is_active', 'created_at']
    search_fields = ['gateway']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('gateway', 'environment', 'is_active')
        }),
        ('M-Pesa Configuration', {
            'fields': (
                'mpesa_consumer_key', 'mpesa_consumer_secret', 
                'mpesa_passkey', 'mpesa_shortcode', 'mpesa_paybill_number',
                'mpesa_paybill_account_name', 'mpesa_paybill_instructions',
                'mpesa_till_number', 'mpesa_buygoods_instructions',
                'mpesa_send_money_recipient', 'mpesa_send_money_instructions',
                'mpesa_pochi_number', 'mpesa_pochi_instructions'
            ),
            'classes': ('collapse',),
        }),
        ('PayPal Configuration', {
            'fields': ('paypal_client_id', 'paypal_client_secret', 'paypal_webhook_id'),
            'classes': ('collapse',),
        }),
        ('Stripe Configuration', {
            'fields': ('stripe_publishable_key', 'stripe_secret_key', 'stripe_webhook_secret'),
            'classes': ('collapse',),
        }),
        ('Bank Configuration', {
            'fields': ('bank_name', 'bank_account_name', 'bank_account_number', 'bank_branch', 'bank_swift_code'),
            'classes': ('collapse',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )


@admin.register(SchoolPaymentConfiguration)
class SchoolPaymentConfigurationAdmin(admin.ModelAdmin):
    """Admin configuration for SchoolPaymentConfiguration"""
    list_display = ['school', 'gateway', 'environment', 'is_active', 'created_at', 'updated_at']
    list_filter = ['gateway', 'environment', 'is_active', 'created_at']
    search_fields = ['school__name', 'gateway']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('school', 'gateway', 'environment', 'is_active')
        }),
        ('M-Pesa STK Push Configuration', {
            'fields': ('mpesa_consumer_key', 'mpesa_consumer_secret', 'mpesa_passkey', 'mpesa_shortcode'),
            'classes': ('collapse',),
        }),
        ('M-Pesa Manual Paybill Configuration', {
            'fields': (
                'mpesa_paybill_number',
                'mpesa_paybill_account_number',
                'mpesa_paybill_account_name',
                'mpesa_paybill_bank_name',
                'mpesa_paybill_instructions',
            ),
            'classes': ('collapse',),
        }),
        ('M-Pesa Buy Goods & Services (Till)', {
            'fields': ('mpesa_till_number', 'mpesa_buygoods_instructions'),
            'classes': ('collapse',),
        }),
        ('M-Pesa Send Money', {
            'fields': ('mpesa_send_money_recipient', 'mpesa_send_money_instructions'),
            'classes': ('collapse',),
        }),
        ('M-Pesa Pochi la Biashara', {
            'fields': ('mpesa_pochi_number', 'mpesa_pochi_instructions'),
            'classes': ('collapse',),
        }),
        ('PayPal Configuration', {
            'fields': ('paypal_email',),
            'classes': ('collapse',),
        }),
        ('Bank Configuration', {
            'fields': ('bank_name', 'bank_account_name', 'bank_account_number', 'bank_branch'),
            'classes': ('collapse',),
        }),
        ('Payment Instructions', {
            'fields': ('payment_instructions',),
            'classes': ('collapse',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )


@admin.register(GlobalAIConfiguration)
class GlobalAIConfigurationAdmin(admin.ModelAdmin):
    """Admin interface for global AI settings"""
    list_display = ['provider', 'is_active', 'temperature', 'max_tokens', 'updated_at']
    list_filter = ['provider', 'is_active']
    search_fields = ['provider', 'openai_model', 'anthropic_model']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(SchoolAIConfiguration)
class SchoolAIConfigurationAdmin(admin.ModelAdmin):
    """Admin interface for school-specific AI settings"""
    list_display = ['school', 'is_active', 'use_global_settings', 'provider', 'updated_at']
    list_filter = ['is_active', 'use_global_settings', 'provider']
    search_fields = ['school__name', 'provider']
    readonly_fields = ['created_at', 'updated_at']
