from django.contrib import admin
from .models import BookableItem, Booking, BookingTracking

@admin.register(BookableItem)
class BookableItemAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'item_type', 'price_per_unit',
        'is_available', 'created_at'
    )
    list_filter = ('item_type', 'is_available')
    search_fields = ('name',)
    ordering = ('-created_at',)

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        'reference', 'user', 'item',
        'status', 'total', 'created_at'
    )
    list_filter = ('status',)
    search_fields = ('reference', 'user__email')
    ordering = ('-created_at',)

@admin.register(BookingTracking)
class BookingTrackingAdmin(admin.ModelAdmin):
    list_display = ('booking', 'status', 'created_at')
    list_filter = ('status',)
    ordering = ('-created_at',)