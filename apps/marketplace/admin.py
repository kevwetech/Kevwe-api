from django.contrib import admin
from .models import (
    Industry, BusinessCategory, Business,
    BusinessSettings, OrderSettings,
    BookingSettings, ServiceSettings,
    BusinessHours, BusinessImage, BusinessDocument,
)


@admin.register(Industry)
class IndustryAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'default_interaction_type',
        'platform_commission', 'status',
        'is_featured', 'order'
    )
    list_filter = ('status', 'default_interaction_type')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}


@admin.register(BusinessCategory)
class BusinessCategoryAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'industry', 'interaction_type',
        'has_order_settings', 'has_booking_settings',
        'has_service_settings', 'is_active'
    )
    list_filter = (
        'industry', 'has_order_settings',
        'has_booking_settings', 'has_service_settings',
        'is_active'
    )
    search_fields = ('name', 'industry__name')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'owner', 'industry', 'category',
        'status', 'is_verified', 'is_featured',
        'is_open', 'city', 'created_at'
    )
    list_filter = (
        'status', 'is_verified', 'is_featured',
        'industry', 'is_active'
    )
    search_fields = ('name', 'owner__email', 'phone')
    readonly_fields = (
        'approved_at', 'approved_by',
        'created_at', 'updated_at',
        'interaction_type', 'commission_rate'
    )
    fieldsets = (
        ('Identity', {
            'fields': (
                'owner', 'industry', 'category',
                'name', 'slug', 'tagline', 'description',
                'tags'
            )
        }),
        ('Media', {
            'fields': ('logo', 'cover_image')
        }),
        ('Contact', {
            'fields': (
                'email', 'phone', 'whatsapp', 'website'
            )
        }),
        ('Location', {
            'fields': (
                'address', 'country', 'state',
                'city', 'zone', 'latitude', 'longitude'
            )
        }),
        ('Commission', {
            'fields': ('custom_commission',)
        }),
        ('Verification', {
            'fields': (
                'status', 'is_verified', 'is_active',
                'is_featured', 'is_open',
                'rejection_reason',
                'approved_at', 'approved_by'
            )
        }),
        ('SEO', {
            'fields': ('meta_title', 'meta_description'),
            'classes': ('collapse',)
        }),
    )


@admin.register(BusinessSettings)
class BusinessSettingsAdmin(admin.ModelAdmin):
    list_display = (
        'business', 'is_24_hours',
        'accepts_online_orders', 'auto_accept_orders',
        'settlement_period_days'
    )
    search_fields = ('business__name',)


@admin.register(OrderSettings)
class OrderSettingsAdmin(admin.ModelAdmin):
    list_display = (
        'business', 'delivery_enabled', 'pickup_enabled',
        'min_order_amount', 'delivery_fee',
        'estimated_delivery_minutes'
    )
    search_fields = ('business__name',)


@admin.register(BookingSettings)
class BookingSettingsAdmin(admin.ModelAdmin):
    list_display = (
        'business', 'check_in_time', 'check_out_time',
        'requires_deposit', 'requires_guest_kyc',
        'instant_booking', 'cancellation_hours'
    )
    search_fields = ('business__name',)


@admin.register(ServiceSettings)
class ServiceSettingsAdmin(admin.ModelAdmin):
    list_display = (
        'business', 'is_mobile', 'is_on_site',
        'inspection_fee_required', 'default_pricing_type',
        'accepts_emergency', 'is_insured'
    )
    search_fields = ('business__name',)


class BusinessHoursInline(admin.TabularInline):
    model = BusinessHours
    extra = 0


class BusinessImageInline(admin.TabularInline):
    model = BusinessImage
    extra = 0


class BusinessDocumentInline(admin.TabularInline):
    model = BusinessDocument
    extra = 0


@admin.register(BusinessHours)
class BusinessHoursAdmin(admin.ModelAdmin):
    list_display = (
        'business', 'day', 'is_open',
        'opening_time', 'closing_time', 'is_24_hours'
    )
    list_filter = ('day', 'is_open')


@admin.register(BusinessImage)
class BusinessImageAdmin(admin.ModelAdmin):
    list_display = (
        'business', 'caption', 'is_primary', 'order'
    )


@admin.register(BusinessDocument)
class BusinessDocumentAdmin(admin.ModelAdmin):
    list_display = (
        'business', 'document_type', 'status',
        'expiry_date', 'reviewed_by', 'reviewed_at'
    )
    list_filter = ('document_type', 'status')
    search_fields = ('business__name',)
    readonly_fields = ('reviewed_at',)