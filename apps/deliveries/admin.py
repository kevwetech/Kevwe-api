from django.contrib import admin
from .models import DeliveryZone, DeliveryRequest, DeliveryTracking, CompanyEarnings

@admin.register(DeliveryZone)
class DeliveryZoneAdmin(admin.ModelAdmin):
    list_display = (
        'zone_name', 'city', 'state',
        'base_price', 'is_active'
    )
    list_filter = ('is_active', 'state')
    search_fields = ('zone_name', 'city', 'state')
    ordering = ('city',)

@admin.register(DeliveryRequest)
class DeliveryRequestAdmin(admin.ModelAdmin):
    list_display = (
        'tracking_number', 'customer', 'status',
        'payment_status', 'price', 'created_at'
    )
    list_filter = ('status', 'payment_status')
    search_fields = ('tracking_number', 'customer__email')
    ordering = ('-created_at',)

@admin.register(DeliveryTracking)
class DeliveryTrackingAdmin(admin.ModelAdmin):
    list_display = ('delivery', 'status', 'location', 'created_at')
    list_filter = ('status',)
    ordering = ('-created_at',)

@admin.register(CompanyEarnings)
class CompanyEarningsAdmin(admin.ModelAdmin):
    list_display= ('amount', 'earning_type', 'reference', 'description')

