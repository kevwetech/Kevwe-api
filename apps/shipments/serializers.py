from rest_framework import serializers
from .models import Shipment, ShipmentTracking


class ShipmentTrackingSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShipmentTracking
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


class ShipmentSerializer(serializers.ModelSerializer):
    tracking_history = ShipmentTrackingSerializer(
        source='tracking',
        many=True,
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
    driver_lat = serializers.DecimalField(
        source='driver.current_lat',
        max_digits=9,
        decimal_places=6,
        read_only=True
    )
    driver_lng = serializers.DecimalField(
        source='driver.current_lng',
        max_digits=9,
        decimal_places=6,
        read_only=True
    )

    class Meta:
        model = Shipment
        fields = (
            'id',
            'reference',
            'tracking_number',
            'status',
            'payment_status',
            'package_name',
            'package_description',
            'package_size',
            'weight',
            'fragile',
            'pickup_name',
            'pickup_phone',
            'pickup_address',
            'pickup_city',
            'pickup_state',
            'pickup_lat',
            'pickup_lng',
            'receiver_name',
            'receiver_phone',
            'receiver_email',
            'delivery_address',
            'delivery_city',
            'delivery_state',
            'delivery_lat',
            'delivery_lng',
            'current_lat',
            'current_lng',
            'current_location',
            'driver_name',
            'driver_phone',
            'driver_lat',
            'driver_lng',
            'price',
            'estimated_delivery',
            'notes',
            'tracking_history',
            'created_at',
            'updated_at',
        )
        read_only_fields = (
            'id',
            'reference',
            'tracking_number',
            'status',
            'price',
            'driver_name',
            'driver_phone',
            'driver_lat',
            'driver_lng',
            'created_at',
            'updated_at',
        )


class CreateShipmentSerializer(serializers.Serializer):
    # ── Option B: saved address IDs ──
    pickup_address_id = serializers.IntegerField(required=False)
    delivery_address_id = serializers.IntegerField(required=False)

    # ── Option C: manual entry ──
    package_name = serializers.CharField()
    package_description = serializers.CharField(
        required=False, allow_blank=True
    )
    package_size = serializers.ChoiceField(
        choices=['small', 'medium', 'large', 'extra_large'],
        default='small'
    )
    weight = serializers.DecimalField(max_digits=10, decimal_places=2)
    fragile = serializers.BooleanField(default=False)

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

    # Delivery manual
    receiver_name = serializers.CharField(required=False, allow_blank=True)
    receiver_phone = serializers.CharField(required=False, allow_blank=True)
    receiver_email = serializers.EmailField(required=False)
    delivery_address = serializers.CharField(required=False, allow_blank=True)
    delivery_city = serializers.CharField(required=False, allow_blank=True)
    delivery_state = serializers.CharField(required=False, allow_blank=True)
    delivery_lat = serializers.DecimalField(
        max_digits=9, decimal_places=6, required=False
    )
    delivery_lng = serializers.DecimalField(
        max_digits=9, decimal_places=6, required=False
    )
    delivery_city_id = serializers.IntegerField(required=False)
    delivery_state_id = serializers.IntegerField(required=False)
    delivery_zone_id = serializers.IntegerField(required=False)

    # Pricing options
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
        """
        Either pickup_address_id OR manual pickup fields required
        Either delivery_address_id OR manual delivery fields required
        """
        if not data.get('pickup_address_id'):
            if not data.get('pickup_name'):
                raise serializers.ValidationError(
                    'pickup_name is required when not using saved address'
                )
            if not data.get('pickup_phone'):
                raise serializers.ValidationError(
                    'pickup_phone is required when not using saved address'
                )
            if not data.get('pickup_address'):
                raise serializers.ValidationError(
                    'pickup_address is required when not using saved address'
                )

        if not data.get('delivery_address_id'):
            if not data.get('receiver_name'):
                raise serializers.ValidationError(
                    'receiver_name is required when not using saved address'
                )
            if not data.get('receiver_phone'):
                raise serializers.ValidationError(
                    'receiver_phone is required when not using saved address'
                )
            if not data.get('delivery_address'):
                raise serializers.ValidationError(
                    'delivery_address is required when not using saved address'
                )

        return data