from django.contrib import admin
from .models import (
    BookableItem,
    BookableItemAvailability,
    BookingPolicy,
    Booking,
    BookingTracking,
    BookingAddOn,
    BookingPayment,
    BookingGuest,
    BookingCoupon,
    CouponUsage,
    BookingInvoice,
    BookingReminder,
)


@admin.register(BookableItem)
class BookableItemAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'business', 'item_type',
        'price_per_unit', 'unit_label',
        'capacity', 'is_available',
        'is_active', 'is_featured'
    )
    list_filter = ('item_type', 'is_available', 'is_active')
    search_fields = ('name', 'business__name')
    ordering = ('business', 'order', 'name')


@admin.register(BookingPolicy)
class BookingPolicyAdmin(admin.ModelAdmin):
    list_display = (
        'item', 'booking_mode',
        'slots_per_day', 'total_seats',
        'free_cancellation_hours'
    )
    list_filter = ('booking_mode',)
    search_fields = ('item__name',)


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        'booking_number', 'item', 'business',
        'guest_name', 'check_in', 'check_out',
        'status', 'payment_status', 'total'
    )
    list_filter = ('status', 'payment_status', 'payment_method')
    search_fields = (
        'booking_number', 'reference',
        'guest_name', 'guest_email'
    )
    ordering = ('-created_at',)


@admin.register(BookingPayment)
class BookingPaymentAdmin(admin.ModelAdmin):
    list_display = (
        'reference', 'booking', 'payment_type',
        'gateway', 'amount', 'status', 'paid_at'
    )
    list_filter = ('payment_type', 'gateway', 'status')
    search_fields = ('reference', 'booking__booking_number')
    ordering = ('-created_at',)


@admin.register(BookingGuest)
class BookingGuestAdmin(admin.ModelAdmin):
    list_display = (
        'full_name', 'guest_type',
        'booking', 'nationality'
    )
    list_filter = ('guest_type',)
    search_fields = ('full_name', 'booking__booking_number')


@admin.register(BookingCoupon)
class BookingCouponAdmin(admin.ModelAdmin):
    list_display = (
        'code', 'name', 'business',
        'discount_type', 'discount_value',
        'total_uses', 'status', 'valid_until'
    )
    list_filter = ('discount_type', 'status')
    search_fields = ('code', 'name', 'business__name')
    ordering = ('-created_at',)


@admin.register(BookingInvoice)
class BookingInvoiceAdmin(admin.ModelAdmin):
    list_display = (
        'invoice_number', 'booking',
        'billed_to_name', 'total',
        'status', 'issue_date'
    )
    list_filter = ('status',)
    search_fields = (
        'invoice_number',
        'booking__booking_number',
        'billed_to_name'
    )
    ordering = ('-created_at',)


@admin.register(BookingReminder)
class BookingReminderAdmin(admin.ModelAdmin):
    list_display = (
        'reminder_type', 'booking',
        'channel', 'send_at',
        'status', 'sent_at'
    )
    list_filter = ('reminder_type', 'channel', 'status')
    search_fields = ('booking__booking_number',)
    ordering = ('send_at',)