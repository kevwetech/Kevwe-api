from rest_framework import serializers
from .models import DeliveryZone, DeliveryRequest, DeliveryTracking


class DeliveryZoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryZone
        fields = (
            'id',
            'name',
            'state',
            'city',
            'base_price',
            'price_per_km',
            'is_active',
        )
        read_only_fields = ('id',)


class DeliveryTrackingSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryTracking
        fields = (
            'id',
            'status',
            'description',
            'location',
            'latitude',
            'longitude',
            'created_at',
        )
        read_only_fields = ('id', 'created_at')


class DeliveryRequestSerializer(serializers.ModelSerializer):
    tracking_history = DeliveryTrackingSerializer(
        source='tracking',
        many=True,
        read_only=True
    )
    dispatcher_name = serializers.CharField(
        source='driver.user.full_name',
        read_only=True
    )
    dispatcher_phone = serializers.CharField(
        source='driver.user.phone',
        read_only=True
    )
    dispatcher_lat = serializers.DecimalField(
        source='driver.current_lat',
        max_digits=9,
        decimal_places=6,
        read_only=True
    )
    dispatcher_lng = serializers.DecimalField(
        source='driver.current_lng',
        max_digits=9,
        decimal_places=6,
        read_only=True
    )
    payment_model = serializers.CharField(
        default='marketplace',
        required=False
    )
    payment_method = serializers.CharField(
        default='wallet',
        required=False
    )
    order_number = serializers.CharField(
        source='order.order_number',
        read_only=True
    )

    class Meta:
        model = DeliveryRequest
        fields = (
            'id',
            'reference',
            'tracking_number',
            'order',
            'order_number',
            'status',
            'payment_status',
            'payment_model',
            'payment_method',
            'package_name',
            'package_description',
            'package_size',
            'fragile',
            'weight',
            'pickup_name',
            'pickup_phone',
            'pickup_address',
            'pickup_city',
            'pickup_state',
            'pickup_lat',
            'pickup_lng',
            'dropoff_name',
            'dropoff_phone',
            'dropoff_address',
            'dropoff_city',
            'dropoff_state',
            'dropoff_lat',
            'dropoff_lng',
            'current_lat',
            'current_lng',
            'current_location',
            'dispatcher_name',
            'dispatcher_phone',
            'dispatcher_lat',
            'dispatcher_lng',
            'price',
            'picked_up_at',
            'delivered_at',
            'notes',
            'delivery_proof',
            'rating',
            'review',
            'tracking_history',
            'created_at',
            'updated_at',
        )
        read_only_fields = (
            'id',
            'reference',
            'tracking_number',
            'order',
            'status',
            'price',
            'picked_up_at',
            'delivered_at',
            'created_at',
            'updated_at',
        )


class CreateDeliverySerializer(serializers.Serializer):
    # ── Option B: saved address IDs ──
    pickup_address_id = serializers.IntegerField(required=False)
    dropoff_address_id = serializers.IntegerField(required=False)

    # Package
    package_name = serializers.CharField()
    package_description = serializers.CharField(
        required=False, allow_blank=True
    )
    package_size = serializers.ChoiceField(
        choices=['small', 'medium', 'large'],
        default='small'
    )
    fragile = serializers.BooleanField(default=False)
    weight = serializers.DecimalField(
        max_digits=10, decimal_places=2, default=1.0
    )
    

    # Pickup manual
    pickup_name = serializers.CharField(required=False, allow_blank=True)
    pickup_phone = serializers.CharField(required=False, allow_blank=True)
    pickup_address = serializers.CharField(required=False, allow_blank=True)
    pickup_city = serializers.CharField(required=False, allow_blank=True)
    pickup_state = serializers.CharField(required=False, allow_blank=True)
    pickup_lat = serializers.DecimalField(
        max_digits=9, decimal_places=6, required=False
    )
    pickup_lng = serializers.DecimalField(
        max_digits=9, decimal_places=6, required=False
    )
    pickup_city_id = serializers.IntegerField(required=False)
    pickup_state_id = serializers.IntegerField(required=False)
    pickup_zone_id = serializers.IntegerField(required=False)

    # Dropoff manual
    dropoff_name = serializers.CharField(required=False, allow_blank=True)
    dropoff_phone = serializers.CharField(required=False, allow_blank=True)
    dropoff_address = serializers.CharField(required=False, allow_blank=True)
    dropoff_city = serializers.CharField(required=False, allow_blank=True)
    dropoff_state = serializers.CharField(required=False, allow_blank=True)
    dropoff_lat = serializers.DecimalField(
        max_digits=9, decimal_places=6, required=False
    )
    dropoff_lng = serializers.DecimalField(
        max_digits=9, decimal_places=6, required=False
    )
    dropoff_city_id = serializers.IntegerField(required=False)
    dropoff_state_id = serializers.IntegerField(required=False)
    dropoff_zone_id = serializers.IntegerField(required=False)

    # Options
    vehicle_type_id = serializers.IntegerField(required=False)
    service_type = serializers.ChoiceField(
        choices=['standard', 'express'],
        default='standard'
    )
    payment_method = serializers.ChoiceField(
        choices=['wallet', 'paystack', 'flutterwave'],
        default='wallet'
    )
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        if not data.get('pickup_address_id'):
            if not data.get('pickup_name'):
                raise serializers.ValidationError(
                    'pickup_name required when not using saved address'
                )
            if not data.get('pickup_phone'):
                raise serializers.ValidationError(
                    'pickup_phone required when not using saved address'
                )
            if not data.get('pickup_address'):
                raise serializers.ValidationError(
                    'pickup_address required when not using saved address'
                )

        if not data.get('dropoff_address_id'):
            if not data.get('dropoff_name'):
                raise serializers.ValidationError(
                    'dropoff_name required when not using saved address'
                )
            if not data.get('dropoff_phone'):
                raise serializers.ValidationError(
                    'dropoff_phone required when not using saved address'
                )
            if not data.get('dropoff_address'):
                raise serializers.ValidationError(
                    'dropoff_address required when not using saved address'
                )

        return data

class RateDeliverySerializer(serializers.Serializer):
    rating = serializers.IntegerField(min_value=1, max_value=5)
    review = serializers.CharField(
        required=False,
        allow_blank=True
    )