from django.contrib import admin
from .models import Shipment, ShipmentTracking

@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):
    list_display = (
        'tracking_number', 'sender', 'status',
        'payment_status', 'price', 'created_at'
    )
    list_filter = ('status', 'payment_status')
    search_fields = ('tracking_number', 'sender__email', 'receiver_name')
    ordering = ('-created_at',)

@admin.register(ShipmentTracking)
class ShipmentTrackingAdmin(admin.ModelAdmin):
    list_display = ('shipment', 'status', 'location', 'created_at')
    list_filter = ('status',)
    search_fields = ('shipment__tracking_number',)
    ordering = ('-created_at',)