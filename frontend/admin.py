from django.contrib import admin
from .models import FAQ, PageContent, ContactMessage

# Register your models here



@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ['question', 'category', 'is_active', 'order']
    list_editable = ['is_active', 'order']
    list_filter = ['category', 'is_active']
    search_fields = ['question', 'answer']

@admin.register(PageContent)
class PageContentAdmin(admin.ModelAdmin):
    list_display = ['page', 'title', 'is_active', 'updated_at']
    list_filter = ['page', 'is_active']

@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'subject', 'is_read', 'replied', 'created_at']
    list_filter = ['is_read', 'replied', 'created_at']
    search_fields = ['name', 'email', 'subject', 'message']
    readonly_fields = ['name', 'email', 'phone', 'subject', 'message', 'created_at']
