from django.contrib import admin
from .models import RideVehicleType, Ride, RideTracking

@admin.register(RideVehicleType)
class RideVehicleTypeAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'base_fare', 'per_km_rate',
        'per_minute_rate', 'is_active'
    )
    list_filter = ('is_active',)
    search_fields = ('name',)

@admin.register(Ride)
class RideAdmin(admin.ModelAdmin):
    list_display = (
        'reference', 'rider', 'driver', 'status',
        'estimated_fare', 'actual_fare', 'created_at'
    )
    list_filter = ('status', 'payment_method', 'payment_status')
    search_fields = ('reference', 'rider__email')
    ordering = ('-created_at',)

@admin.register(RideTracking)
class RideTrackingAdmin(admin.ModelAdmin):
    list_display = ('ride', 'status', 'created_at')
    list_filter = ('status',)
    ordering = ('-created_at',)