from django.contrib import admin
from .models import Department, Designation, Teacher, Staff

# Register your models here

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'head', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'code', 'description']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(Designation)
class DesignationAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'level', 'is_active', 'created_at']
    list_filter = ['is_active', 'level', 'created_at']
    search_fields = ['name', 'code', 'description']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ['employee_id', 'first_name', 'last_name', 'department', 'designation', 'basic_salary', 'is_active']
    list_filter = ['is_active', 'department', 'designation', 'employment_type']
    search_fields = ['employee_id', 'first_name', 'last_name', 'email', 'phone']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Personal Information', {
            'fields': ('user', 'first_name', 'last_name', 'employee_id', 'email', 'phone', 'address')
        }),
        ('Employment Details', {
            'fields': ('department', 'designation', 'employment_type', 'date_of_joining')
        }),
        ('Salary Information', {
            'fields': ('basic_salary', 'allowances')
        }),
        ('Status', {
            'fields': ('is_active', 'created_at', 'updated_at')
        }),
    )

@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display = ['employee_id', 'first_name', 'last_name', 'department', 'designation', 'basic_salary', 'is_active']
    list_filter = ['is_active', 'department', 'designation', 'employment_type']
    search_fields = ['employee_id', 'first_name', 'last_name', 'email', 'phone']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Personal Information', {
            'fields': ('user', 'first_name', 'last_name', 'employee_id', 'email', 'phone', 'address')
        }),
        ('Employment Details', {
            'fields': ('department', 'designation', 'employment_type', 'date_of_joining')
        }),
        ('Salary Information', {
            'fields': ('basic_salary', 'allowances')
        }),
        ('Status', {
            'fields': ('is_active', 'created_at', 'updated_at')
        }),
    )
