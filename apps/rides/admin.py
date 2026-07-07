from django.contrib import admin
from .models import (
    RideVehicleType, Ride, RideTracking,
    TransportVehicle, TransportRoute, TransportStop,
    TransportSchedule, ScheduleFare, TransportSeat,
    TransportBooking, TransportPassenger,
    TransportBoardingLog, TransportScheduleTracking,
    TransportCancellationPolicy, ScheduleDriverAssignment,
    TransportBaggage, TransportRating,
)

@admin.register(RideVehicleType)
class RideVehicleTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'base_fare', 'per_km_rate', 'is_active']

@admin.register(Ride)
class RideAdmin(admin.ModelAdmin):
    list_display = ['reference', 'rider', 'driver', 'status', 'payment_status', 'created_at']
    list_filter  = ['status', 'payment_status']

@admin.register(TransportVehicle)
class TransportVehicleAdmin(admin.ModelAdmin):
    list_display = ['name', 'business', 'vehicle_type', 'plate_number', 'total_capacity', 'status']
    list_filter  = ['vehicle_type', 'status']

@admin.register(TransportRoute)
class TransportRouteAdmin(admin.ModelAdmin):
    list_display = ['name', 'business', 'transport_type', 'origin', 'destination', 'is_active']
    list_filter  = ['transport_type', 'is_active']

@admin.register(TransportStop)
class TransportStopAdmin(admin.ModelAdmin):
    list_display = ['route', 'city', 'order', 'is_origin', 'is_destination']
    list_filter  = ['route']

@admin.register(TransportSchedule)
class TransportScheduleAdmin(admin.ModelAdmin):
    list_display = ['route', 'departure_date', 'departure_time', 'total_seats', 'available_seats', 'status']
    list_filter  = ['status', 'departure_date']

@admin.register(ScheduleFare)
class ScheduleFareAdmin(admin.ModelAdmin):
    list_display = ['schedule', 'seat_class', 'price', 'is_active']
    list_filter  = ['seat_class']

@admin.register(TransportSeat)
class TransportSeatAdmin(admin.ModelAdmin):
    list_display = ['schedule', 'seat_number', 'seat_class', 'status']
    list_filter  = ['status', 'seat_class']

@admin.register(TransportBooking)
class TransportBookingAdmin(admin.ModelAdmin):
    list_display = ['reference', 'customer', 'schedule', 'total_amount', 'status', 'payment_status']
    list_filter  = ['status', 'payment_status']

@admin.register(TransportPassenger)
class TransportPassengerAdmin(admin.ModelAdmin):
    list_display = ['name', 'booking', 'seat', 'seat_class', 'boarding_status', 'ticket_code']
    list_filter  = ['boarding_status', 'seat_class']

@admin.register(TransportBoardingLog)
class TransportBoardingLogAdmin(admin.ModelAdmin):
    list_display = ['passenger', 'action', 'scanned_by', 'created_at']

@admin.register(TransportScheduleTracking)
class TransportScheduleTrackingAdmin(admin.ModelAdmin):
    list_display = ['schedule', 'status', 'city', 'created_at']

@admin.register(TransportCancellationPolicy)
class TransportCancellationPolicyAdmin(admin.ModelAdmin):
    list_display = ['business', 'hours_before', 'refund_percentage']

@admin.register(ScheduleDriverAssignment)
class ScheduleDriverAssignmentAdmin(admin.ModelAdmin):
    list_display = ['schedule', 'driver', 'assigned_at', 'is_active']

@admin.register(TransportBaggage)
class TransportBaggageAdmin(admin.ModelAdmin):
    list_display = ['passenger', 'tag_number', 'weight_kg', 'fee', 'status']

@admin.register(TransportRating)
class TransportRatingAdmin(admin.ModelAdmin):
    list_display = ['booking', 'overall_rating', 'driver_rating', 'vehicle_rating']