from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import DriverProfile, Vehicle, DriverDocument, DriverEarnings, VehicleType

User = get_user_model()



class VehicleTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = VehicleType
        fields = (
            'id',
            'name',
            'slug',
            'description',
            'icon',
            'base_price_standard',
            'base_price_express',
            'per_km_rate',
            'per_kg_rate',
            'minimum_fare_standard',
            'minimum_fare_express',
            'max_weight_kg',
            'max_passengers',
            'is_active',
            'order',
            'created_at',
        )
        read_only_fields = ('id', 'created_at')




class VehicleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vehicle
        fields = (
            'id',
            'vehicle_type',
            'plate_number',
            'model',
            'brand',
            'color',
            'year',
            'status',
            'is_active',
            'created_at',
        )
        read_only_fields = ('id', 'created_at')


class DriverProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(
        source='user.full_name',
        read_only=True
    )
    email = serializers.CharField(
        source='user.email',
        read_only=True
    )
    phone = serializers.CharField(
        source='user.phone',
        read_only=True
    )
    avatar = serializers.ImageField(
        source='user.avatar',
        read_only=True
    )
    active_vehicle = VehicleSerializer(read_only=True)

    class Meta:
        model = DriverProfile
        fields = (
            'id',
            'full_name',
            'email',
            'phone',
            'avatar',
            'license_number',
            'license_expiry',
            'status',
            'is_available',
            'is_online',
            'current_lat',
            'current_lng',
            'total_rides',
            'total_deliveries',
            'rating',
            'active_vehicle',
            'created_at',
        )
        read_only_fields = (
            'id',
            'status',
            'total_rides',
            'total_deliveries',
            'rating',
            'created_at',
        )


class CreateDriverProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = DriverProfile
        fields = (
            'license_number',
            'license_expiry',
        )


class DriverDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = DriverDocument
        fields = (
            'id',
            'document_type',
            'document_file',
            'status',
            'notes',
            'created_at',
        )
        read_only_fields = ('id', 'status', 'notes', 'created_at')


class DriverEarningsSerializer(serializers.ModelSerializer):
    class Meta:
        model = DriverEarnings
        fields = (
            'id',
            'earning_type',
            'amount',
            'reference',
            'description',
            'is_paid',
            'created_at',
        )
        read_only_fields = ('id', 'created_at')


class UpdateLocationSerializer(serializers.Serializer):
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6)


class NearbyDriversSerializer(serializers.Serializer):
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6)
    radius_km = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=5.00
    )