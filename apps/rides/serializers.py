from rest_framework import serializers
from .models import Ride, RideVehicleType, RideTracking


class RideVehicleTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = RideVehicleType
        fields = (
            'id',
            'name',
            'description',
            'base_fare',
            'per_km_rate',
            'per_minute_rate',
            'minimum_fare',
            'max_passengers',
            'icon',
            'is_active',
        )
        read_only_fields = ('id',)


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
    vehicle_type_id = serializers.IntegerField(required=False)
    payment_method = serializers.ChoiceField(
        choices=['cash', 'card', 'wallet', 'transfer'],
        default='cash'
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