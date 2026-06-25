from django.contrib import admin
from .models import (
    Industry, Business, BusinessHours,
    BusinessImage, BusinessDocument,
    Permission, BusinessRole, BusinessStaff,
)


@admin.register(Industry)
class IndustryAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'status', 'platform_commission',
        'is_featured', 'order'
    )
    list_filter  = ('status', 'is_featured')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('order',)


@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'industry', 'owner',
        'status', 'city', 'rating',
        'is_featured', 'created_at'
    )
    list_filter  = ('status', 'industry', 'is_featured', 'is_verified')
    search_fields = ('name', 'owner__email')
    ordering = ('-created_at',)


@admin.register(BusinessHours)
class BusinessHoursAdmin(admin.ModelAdmin):
    list_display = (
        'business', 'day',
        'is_open', 'opening_time', 'closing_time'
    )
    list_filter  = ('is_open', 'day')
    ordering = ('business', 'day')


@admin.register(BusinessDocument)
class BusinessDocumentAdmin(admin.ModelAdmin):
    list_display  = ('business', 'document_type', 'status')
    list_filter   = ('document_type', 'status')
    ordering = ('-created_at',)


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display  = ('name', 'codename', 'category', 'is_active')
    list_filter   = ('category', 'is_active')
    search_fields = ('name', 'codename')
    ordering = ('category', 'name')


@admin.register(BusinessRole)
class BusinessRoleAdmin(admin.ModelAdmin):
    list_display  = (
        'name', 'business',
        'is_active', 'is_default'
    )
    list_filter   = ('is_active', 'is_default')
    search_fields = ('name', 'business__name')
    filter_horizontal = ('permissions',)
    ordering = ('name',)


@admin.register(BusinessStaff)
class BusinessStaffAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'business', 'role',
        'status', 'invitation_status', 'joined_at'
    )
    list_filter   = ('status', 'invitation_status')
    search_fields = ('user__email', 'business__name')
    ordering = ('-created_at',)