from django.contrib import admin
from .models import (
    Industry, BusinessCategory, Business,
    BusinessSettings, OrderSettings,
    BookingSettings, ServiceSettings,
    BusinessHours, BusinessImage, BusinessDocument,
    BusinessSubtype, AppointmentSettings,
    RideSettings, ShipmentSettings,
    BusinessFAQ, BusinessPromotion,
    BusinessPolicy, BusinessContentBlock,
    InteractionForm
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
    list_display = ('name', 'industry', 'interaction_type', 'enabled_summary', 'is_active')

    fieldsets = (
        (None, {'fields': ('industry', 'name', 'slug', 'description',
                           'icon', 'image', 'order', 'is_active')}),
        ('Primary interaction', {
            'fields': ('interaction_type',),
            'description': 'The default experience only — first tab and main CTA. '
                           'Businesses here can offer everything ticked below.',
        }),
        ('Enabled interactions', {
            'fields': ('has_order_settings', 'has_booking_settings',
                       'has_appointment_settings', 'has_service_settings',
                       'has_scheduled_service_settings', 'has_ride_settings',
                       'has_transport_settings', 'has_shipment_settings'),
            'description': 'Every capability a business in this category may switch on. '
                           'Hotel → Bookings + Orders. Salon → Appointments + Services + Orders. '
                           'Restaurant → Orders + Bookings.',
        }),
        ('Commission & compliance', {
            'fields': ('platform_commission', 'requires_certification'),
            'classes': ('collapse',),
        }),
    )

    def enabled_summary(self, obj):
        return ', '.join(obj.enabled_interactions) or '—'
    enabled_summary.short_description = 'Enabled'

class BusinessImageInline(admin.TabularInline):
    model = BusinessImage
    extra = 0


@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    inlines = [BusinessImageInline]
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


@admin.register(BusinessSubtype)
class BusinessSubtypeAdmin(admin.ModelAdmin):
    list_display  = ['name', 'interaction_type', 'slug', 'is_active', 'order']
    list_filter   = ['interaction_type', 'is_active']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['interaction_type', 'order']

@admin.register(AppointmentSettings)
class AppointmentSettingsAdmin(admin.ModelAdmin):
    list_display = ['business', 'subtype', 'slot_duration_minutes']

@admin.register(RideSettings)
class RideSettingsAdmin(admin.ModelAdmin):
    list_display = ['business', 'ride_type', 'fleet_size', 'allows_instant_booking']
    list_filter  = ['ride_type']

@admin.register(ShipmentSettings)
class ShipmentSettingsAdmin(admin.ModelAdmin):
    list_display = ['business', 'shipment_type', 'base_fee', 'offers_pickup', 'offers_insurance']
    list_filter  = ['shipment_type']


class BusinessFAQInline(admin.TabularInline):
    model = BusinessFAQ
    extra = 1
    fields = ('question', 'answer', 'order', 'is_active')

class BusinessPromotionInline(admin.TabularInline):
    model = BusinessPromotion
    extra = 0
    fields = ('kind', 'title', 'icon', 'starts_at', 'ends_at', 'order', 'is_active')

class BusinessPolicyInline(admin.TabularInline):
    model = BusinessPolicy
    extra = 0
    fields = ('policy_type', 'title', 'order', 'is_active')

class BusinessContentBlockInline(admin.StackedInline):
    model = BusinessContentBlock
    extra = 0
    fields = ('title', 'content', 'image', 'order', 'is_active')



@admin.register(InteractionForm)
class InteractionFormAdmin(admin.ModelAdmin):
    list_display = ('form_key', 'interaction_type', 'scope_label_display', 'name')
    list_filter = ('interaction_type',)
    search_fields = ('form_key', 'name')

    fieldsets = (
        (None, {'fields': ('interaction_type', 'form_key', 'name')}),
        ('Scope — set exactly ONE', {
            'fields': ('industry', 'category', 'business'),
            'description': 'Business beats category beats industry when more than '
                          'one row could match the same business.',
        }),
        ('Field contract', {
            'fields': ('schema',),
            'description': 'Validation contract for the booking engine — NOT a '
                          'rendering instruction. The dedicated frontend page for '
                          'this form_key decides its own UI independently.',
        }),
    )

    def scope_label_display(self, obj):
        return obj.scope_label
    scope_label_display.short_description = 'Scope'
