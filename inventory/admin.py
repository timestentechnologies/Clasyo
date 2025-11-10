from django.contrib import admin
from .models import (
    ItemCategory, Item, Supplier, PurchaseOrder, PurchaseOrderItem,
    ItemDistribution, Expense, StaffPayment
)


@admin.register(ItemCategory)
class ItemCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'category_type', 'is_active', 'created_at']
    list_filter = ['category_type', 'is_active']
    search_fields = ['name']


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'category', 'unit_price', 'quantity_in_stock', 'reorder_level', 'is_active']
    list_filter = ['category', 'is_active']
    search_fields = ['code', 'name']


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ['name', 'contact_person', 'phone', 'email', 'city', 'is_active']
    list_filter = ['is_active', 'city']
    search_fields = ['name', 'contact_person', 'email']


class PurchaseOrderItemInline(admin.TabularInline):
    model = PurchaseOrderItem
    extra = 1


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ['po_number', 'supplier', 'status', 'order_date', 'total_amount', 'created_by']
    list_filter = ['status', 'order_date']
    search_fields = ['po_number', 'supplier__name']
    inlines = [PurchaseOrderItemInline]


@admin.register(ItemDistribution)
class ItemDistributionAdmin(admin.ModelAdmin):
    list_display = ['item', 'recipient_name', 'recipient_type', 'quantity', 'distribution_date', 'distributed_by']
    list_filter = ['recipient_type', 'distribution_date']
    search_fields = ['recipient_name', 'item__name']


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ['expense_number', 'expense_type', 'description', 'amount', 'expense_date', 'payee_name']
    list_filter = ['expense_type', 'expense_date', 'payment_method']
    search_fields = ['expense_number', 'description', 'payee_name']


@admin.register(StaffPayment)
class StaffPaymentAdmin(admin.ModelAdmin):
    list_display = ['payment_number', 'staff_name', 'staff_type', 'net_salary', 'payment_date', 'status']
    list_filter = ['staff_type', 'status', 'payment_date']
    search_fields = ['payment_number', 'staff_name']
