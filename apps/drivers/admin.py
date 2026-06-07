from django.contrib import admin
from .models import (
    DriverProfile, Vehicle, VehicleType,
    DriverDocument, DriverEarnings
)

@admin.register(VehicleType)
class VehicleTypeAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'base_price_standard',
        'base_price_express', 'per_km_rate',
        'per_kg_rate', 'is_active', 'order'
    )
    list_filter = ('is_active',)
    search_fields = ('name',)
    ordering = ('order',)
    prepopulated_fields = {'slug': ('name',)}

@admin.register(DriverProfile)
class DriverProfileAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'license_number', 'status',
        'is_available', 'is_online', 'rating', 'created_at'
    )
    list_filter = ('status', 'is_available', 'is_online')
    search_fields = ('user__email', 'license_number')
    ordering = ('-created_at',)

@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = (
        'plate_number', 'driver', 'vehicle_type',
        'brand', 'model', 'status', 'created_at'
    )
    list_filter = ('vehicle_type', 'status')
    search_fields = ('plate_number', 'driver__email')
    ordering = ('-created_at',)

@admin.register(DriverDocument)
class DriverDocumentAdmin(admin.ModelAdmin):
    list_display = (
        'driver', 'document_type',
        'status', 'created_at'
    )
    list_filter = ('document_type', 'status')
    search_fields = ('driver__user__email',)
    ordering = ('-created_at',)

@admin.register(DriverEarnings)
class DriverEarningsAdmin(admin.ModelAdmin):
    list_display = (
        'driver', 'earning_type', 'amount',
        'is_paid', 'created_at'
    )
    list_filter = ('earning_type', 'is_paid')
    search_fields = ('driver__user__email',)
    ordering = ('-created_at',)