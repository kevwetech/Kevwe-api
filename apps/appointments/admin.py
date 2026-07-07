from django.contrib import admin
from .models import (
    AppointmentService, AppointmentStaff,
    AppointmentSlot, AppointmentBlock,
    AppointmentAvailabilityException,
    Appointment, AppointmentTracking,
    AppointmentPayment, AppointmentRating,
    AppointmentWaitlist, AppointmentReminder,
)

@admin.register(AppointmentService)
class AppointmentServiceAdmin(admin.ModelAdmin):
    list_display = ['name', 'business', 'duration_minutes', 'price', 'requires_confirmation', 'is_active']
    list_filter  = ['is_active', 'requires_confirmation']

@admin.register(AppointmentStaff)
class AppointmentStaffAdmin(admin.ModelAdmin):
    list_display = ['name', 'business', 'title', 'is_online_bookable', 'is_active']

@admin.register(AppointmentSlot)
class AppointmentSlotAdmin(admin.ModelAdmin):
    list_display = ['business', 'staff', 'day', 'start_time', 'end_time', 'max_bookings', 'is_active']
    list_filter  = ['day', 'is_active']

@admin.register(AppointmentBlock)
class AppointmentBlockAdmin(admin.ModelAdmin):
    list_display = ['business', 'staff', 'date', 'all_day', 'reason']

@admin.register(AppointmentAvailabilityException)
class AppointmentAvailabilityExceptionAdmin(admin.ModelAdmin):
    list_display = ['business', 'date', 'exception_type', 'start_time', 'end_time']

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ['reference', 'customer_name', 'business', 'service_name', 'date', 'start_time', 'status', 'payment_status']
    list_filter  = ['status', 'payment_status', 'date']
    search_fields = ['reference', 'customer_name', 'check_in_code']

@admin.register(AppointmentPayment)
class AppointmentPaymentAdmin(admin.ModelAdmin):
    list_display = ['appointment', 'payment_type', 'amount', 'status', 'paid_at']

@admin.register(AppointmentRating)
class AppointmentRatingAdmin(admin.ModelAdmin):
    list_display = ['appointment', 'overall_rating', 'staff_rating', 'is_public']

@admin.register(AppointmentWaitlist)
class AppointmentWaitlistAdmin(admin.ModelAdmin):
    list_display = ['customer', 'service', 'preferred_date', 'status']
    list_filter  = ['status']

@admin.register(AppointmentReminder)
class AppointmentReminderAdmin(admin.ModelAdmin):
    list_display = ['appointment', 'reminder_type', 'channel', 'status', 'scheduled_at']
    list_filter  = ['status', 'reminder_type', 'channel']