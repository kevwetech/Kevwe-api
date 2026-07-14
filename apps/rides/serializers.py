from rest_framework import serializers
from .models import (
    Ride, RideVehicleType, RideTracking,
    TransportVehicle, TransportRoute, TransportStop,
    TransportSchedule, ScheduleFare, TransportSeat,
    TransportBooking, TransportPassenger,
    TransportBoardingLog, TransportScheduleTracking,
    TransportCancellationPolicy, TransportBaggage,
    TransportRating,
)
class RideVehicleTypeSerializer(serializers.ModelSerializer):
    """Updated — add business + vehicle_category fields"""
    business_name = serializers.CharField(
        source='business.name', read_only=True)
 
    class Meta:
        model = RideVehicleType
        fields = (
            'id', 'business', 'business_name', 'vehicle_category',
            'name', 'description', 'base_fare', 'per_km_rate',
            'per_minute_rate', 'minimum_fare', 'max_passengers',
            'icon', 'is_active',
        )
        read_only_fields = ('id',)


class TransportRouteListSerializer(serializers.ModelSerializer):
    """Lightweight route list (no nested stops/schedules)"""
    business_name = serializers.CharField(
        source='business.name', read_only=True)
    stops_count = serializers.SerializerMethodField()
 
    class Meta:
        model = TransportRoute
        fields = (
            'id', 'business', 'business_name', 'name', 'route_code',
            'transport_type', 'origin', 'destination',
            'distance_km', 'estimated_duration_minutes',
            'amenities', 'is_active', 'is_return_available',
            'stops_count',
        )
 
    def get_stops_count(self, obj):
        return obj.stops.count()
 


class RideTrackingSerializer(serializers.ModelSerializer):
    class Meta:
        model = RideTracking
        fields = (
            'id',
            'driver_lat',
            'driver_lng',
            'status',
            'description',
            'created_at',
        )
        read_only_fields = ('id', 'created_at')


class RideSerializer(serializers.ModelSerializer):
    rider_name = serializers.CharField(
        source='rider.full_name',
        read_only=True
    )
    rider_phone = serializers.CharField(
        source='rider.phone',
        read_only=True
    )
    driver_name = serializers.CharField(
        source='driver.user.full_name',
        read_only=True
    )
    driver_phone = serializers.CharField(
        source='driver.user.phone',
        read_only=True
    )
    driver_rating = serializers.DecimalField(
        source='driver.rating',
        max_digits=3,
        decimal_places=2,
        read_only=True
    )
    vehicle_type_name = serializers.CharField(
        source='vehicle_type.name',
        read_only=True
    )
    tracking_history = RideTrackingSerializer(
        source='tracking',
        many=True,
        read_only=True
    )

    class Meta:
        model = Ride
        fields = (
            'id',
            'reference',
            'status',
            'payment_method',
            'payment_status',
            'rider_name',
            'rider_phone',
            'driver_name',
            'driver_phone',
            'driver_rating',
            'vehicle_type_name',
            'pickup_address',
            'pickup_lat',
            'pickup_lng',
            'destination_address',
            'destination_lat',
            'destination_lng',
            'driver_current_lat',
            'driver_current_lng',
            'estimated_fare',
            'actual_fare',
            'distance_km',
            'duration_minutes',
            'rider_rating',
            'driver_rating',
            'rider_review',
            'driver_review',
            'accepted_at',
            'started_at',
            'completed_at',
            'tracking_history',
            'created_at',
        )
        read_only_fields = (
            'id',
            'reference',
            'status',
            'estimated_fare',
            'actual_fare',
            'created_at',
        )


class RequestRideSerializer(serializers.Serializer):
    pickup_address = serializers.CharField()
    pickup_lat = serializers.DecimalField(
        max_digits=9,
        decimal_places=6
    )
    pickup_lng = serializers.DecimalField(
        max_digits=9,
        decimal_places=6
    )
    destination_address = serializers.CharField()
    destination_lat = serializers.DecimalField(
        max_digits=9,
        decimal_places=6
    )
    destination_lng = serializers.DecimalField(
        max_digits=9,
        decimal_places=6
    )
    business_id = serializers.IntegerField(required=False, allow_null=True)
    vehicle_type_id = serializers.IntegerField(required=False)
    payment_method = serializers.ChoiceField(
        choices=['card', 'wallet', 'transfer'],
        default='wallet'
    )


class RateRideSerializer(serializers.Serializer):
    rating = serializers.IntegerField(min_value=1, max_value=5)
    review = serializers.CharField(
        required=False,
        allow_blank=True
    )


class EstimateFareSerializer(serializers.Serializer):
    pickup_lat = serializers.DecimalField(
        max_digits=9,
        decimal_places=6
    )
    pickup_lng = serializers.DecimalField(
        max_digits=9,
        decimal_places=6
    )
    destination_lat = serializers.DecimalField(
        max_digits=9,
        decimal_places=6
    )
    destination_lng = serializers.DecimalField(
        max_digits=9,
        decimal_places=6
    )

# ── Transport Vehicle ─────────────────────────────
class TransportVehicleSerializer(serializers.ModelSerializer):
    class Meta:
        model = TransportVehicle
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')


# ── Transport Stop ────────────────────────────────
class TransportStopSerializer(serializers.ModelSerializer):
    class Meta:
        model = TransportStop
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')


# ── Transport Route ───────────────────────────────
class TransportRouteSerializer(serializers.ModelSerializer):
    business_name  = serializers.CharField(source='business.name', read_only=True)
    stops          = TransportStopSerializer(many=True, read_only=True)

    class Meta:
        model = TransportRoute
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')


# ── Schedule Fare ─────────────────────────────────
class ScheduleFareSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScheduleFare
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')


# ── Transport Seat ────────────────────────────────
class TransportSeatSerializer(serializers.ModelSerializer):
    class Meta:
        model = TransportSeat
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')


# ── Transport Schedule ────────────────────────────
class TransportScheduleSerializer(serializers.ModelSerializer):
    route_name       = serializers.CharField(source='route.name', read_only=True)
    origin           = serializers.CharField(source='route.origin', read_only=True)
    destination      = serializers.CharField(source='route.destination', read_only=True)
    transport_type   = serializers.CharField(source='route.transport_type', read_only=True)
    business_name    = serializers.CharField(source='route.business.name', read_only=True)
    available_seats  = serializers.IntegerField(read_only=True)
    fares            = ScheduleFareSerializer(many=True, read_only=True)
    seats            = TransportSeatSerializer(many=True, read_only=True)

    class Meta:
        model = TransportSchedule
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')


# ── Transport Passenger ───────────────────────────
class TransportPassengerSerializer(serializers.ModelSerializer):
    seat_number = serializers.CharField(source='seat.seat_number', read_only=True)

    class Meta:
        model = TransportPassenger
        fields = '__all__'
        read_only_fields = ('id', 'ticket_code', 'created_at', 'updated_at')


# ── Transport Booking ─────────────────────────────
class TransportBookingSerializer(serializers.ModelSerializer):
    customer_name    = serializers.CharField(source='customer.full_name', read_only=True)
    schedule_detail  = TransportScheduleSerializer(source='schedule', read_only=True)
    passengers       = TransportPassengerSerializer(many=True, read_only=True)
    passenger_count  = serializers.IntegerField(read_only=True)

    class Meta:
        model = TransportBooking
        fields = '__all__'
        read_only_fields = (
            'id', 'reference', 'status', 'payment_status',
            'created_at', 'updated_at'
        )


# ── Boarding Log ──────────────────────────────────
class TransportBoardingLogSerializer(serializers.ModelSerializer):
    passenger_name = serializers.CharField(source='passenger.name', read_only=True)
    scanned_by_name = serializers.CharField(source='scanned_by.full_name', read_only=True)

    class Meta:
        model = TransportBoardingLog
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')


# ── Schedule Tracking ─────────────────────────────
class TransportScheduleTrackingSerializer(serializers.ModelSerializer):
    class Meta:
        model = TransportScheduleTracking
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')


# ── Cancellation Policy ───────────────────────────
class TransportCancellationPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = TransportCancellationPolicy
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')


# ── Baggage ───────────────────────────────────────
class TransportBaggageSerializer(serializers.ModelSerializer):
    class Meta:
        model = TransportBaggage
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')


# ── Rating ────────────────────────────────────────
class TransportRatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = TransportRating
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')


# ── Input serializers ─────────────────────────────
class BookTransportSerializer(serializers.Serializer):
    """Input for booking transport tickets."""
    schedule_id    = serializers.IntegerField()
    passengers     = serializers.ListField(
        child=serializers.DictField(),
        min_length=1,
        max_length=10,
    )
    payment_method = serializers.ChoiceField(
        choices=['card', 'wallet', 'transfer'],
        default='card'
    )

    # passenger dict fields:
    # { name, phone, email, seat_class, seat_id (optional) }


class SearchRouteSerializer(serializers.Serializer):
    """Input for searching available routes."""
    origin      = serializers.CharField()
    destination = serializers.CharField()
    date        = serializers.DateField()
    passengers  = serializers.IntegerField(default=1, min_value=1, max_value=10)
    seat_class  = serializers.ChoiceField(
        choices=['economy', 'business', 'first', 'vip'],
        default='economy',
        required=False,
    )