from rest_framework import serializers
from .models import Country, State, City, Zone, Address


class CountrySerializer(serializers.ModelSerializer):
    state_count = serializers.SerializerMethodField()

    class Meta:
        model = Country
        fields = (
            'id',
            'name',
            'code',
            'phone_code',
            'currency',
            'currency_symbol',
            'flag',
            'is_active',
            'state_count',
            'created_at',
        )
        read_only_fields = ('id', 'created_at')

    def get_state_count(self, obj):
        return obj.states.filter(is_active=True).count()


class StateSerializer(serializers.ModelSerializer):
    country_name = serializers.CharField(
        source='country.name',
        read_only=True
    )
    city_count = serializers.SerializerMethodField()

    class Meta:
        model = State
        fields = (
            'id',
            'name',
            'code',
            'country',
            'country_name',
            'is_active',
            'city_count',
            'created_at',
        )
        read_only_fields = ('id', 'created_at')

    def get_city_count(self, obj):
        return obj.cities.filter(is_active=True).count()


class CitySerializer(serializers.ModelSerializer):
    state_name = serializers.CharField(
        source='state.name',
        read_only=True
    )
    country_name = serializers.CharField(
        source='state.country.name',
        read_only=True
    )
    zone_count = serializers.SerializerMethodField()

    class Meta:
        model = City
        fields = (
            'id',
            'name',
            'state',
            'state_name',
            'country_name',
            'is_active',
            'zone_count',
            'created_at',
        )
        read_only_fields = ('id', 'created_at')

    def get_zone_count(self, obj):
        return obj.zones.filter(is_active=True).count()


class ZoneSerializer(serializers.ModelSerializer):
    city_name = serializers.CharField(
        source='city.name',
        read_only=True
    )
    state_name = serializers.CharField(
        source='city.state.name',
        read_only=True
    )

    class Meta:
        model = Zone
        fields = (
            'id',
            'name',
            'description',
            'city',
            'city_name',
            'state_name',
            'latitude',
            'longitude',
            'radius_km',
            'price_multiplier',
            'is_active',
            'created_at',
        )
        read_only_fields = ('id', 'created_at')


class AddressSerializer(serializers.ModelSerializer):
    country_name = serializers.CharField(
        source='country.name',
        read_only=True
    )
    state_name = serializers.CharField(
        source='state.name',
        read_only=True
    )
    city_name = serializers.CharField(
        source='city.name',
        read_only=True
    )
    zone_name = serializers.CharField(
        source='zone.name',
        read_only=True
    )
    full_address = serializers.SerializerMethodField()

    class Meta:
        model = Address
        fields = (
            'id',
            'address_type',
            'label',
            'country',
            'country_name',
            'state',
            'state_name',
            'city',
            'city_name',
            'zone',
            'zone_name',
            'street_address',
            'landmark',
            'postal_code',
            'latitude',
            'longitude',
            'is_default',
            'is_verified',
            'full_address',
            'created_at',
        )
        read_only_fields = (
            'id',
            'is_verified',
            'created_at',
        )

    def get_full_address(self, obj):
        parts = [obj.street_address]
        if obj.landmark:
            parts.append(obj.landmark)
        if obj.city:
            parts.append(obj.city.name)
        if obj.state:
            parts.append(obj.state.name)
        if obj.country:
            parts.append(obj.country.name)
        return ', '.join(parts)