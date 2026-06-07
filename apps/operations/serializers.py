from rest_framework import serializers
from .models import (
    Branch,
    Territory,
    Fleet,
    FleetVehicle,
    Dispatch,
    FuelType,
    FuelRecord,
    MaintenanceType,       
    MaintenanceRecord,     
    BranchManager,         
)

class BranchSerializer(serializers.ModelSerializer):
    manager_name = serializers.CharField(
        source='manager.full_name',
        read_only=True
    )
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
    total_fleets = serializers.SerializerMethodField()
    total_vehicles = serializers.SerializerMethodField()

    class Meta:
        model = Branch
        fields = (
            'id',
            'name',
            'code',
            'branch_type',
            'status',
            'manager',
            'manager_name',
            'email',
            'phone',
            'alternate_phone',
            'address',
            'country',
            'country_name',
            'state',
            'state_name',
            'city',
            'city_name',
            'zone',
            'latitude',
            'longitude',
            'opening_time',
            'closing_time',
            'working_days',
            'is_active',
            'total_fleets',
            'total_vehicles',
            'created_at',
        )
        read_only_fields = ('id', 'created_at')

    def get_total_fleets(self, obj):
        return obj.fleets.filter(is_active=True).count()

    def get_total_vehicles(self, obj):
        return sum(
            f.vehicles.count()
            for f in obj.fleets.filter(is_active=True)
        )


class TerritorySerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(
        source='branch.name',
        read_only=True
    )
    states_list = serializers.SerializerMethodField()
    cities_list = serializers.SerializerMethodField()
    zones_list = serializers.SerializerMethodField()

    class Meta:
        model = Territory
        fields = (
            'id',
            'branch',
            'branch_name',
            'name',
            'description',
            'countries',
            'states',
            'cities',
            'zones',
            'states_list',
            'cities_list',
            'zones_list',
            'is_active',
            'created_at',
        )
        read_only_fields = ('id', 'created_at')

    def get_states_list(self, obj):
        return [
            {'id': s.id, 'name': s.name}
            for s in obj.states.all()
        ]

    def get_cities_list(self, obj):
        return [
            {'id': c.id, 'name': c.name}
            for c in obj.cities.all()
        ]

    def get_zones_list(self, obj):
        return [
            {'id': z.id, 'name': z.name}
            for z in obj.zones.all()
        ]


class FleetSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(
        source='branch.name',
        read_only=True
    )
    total_vehicles = serializers.IntegerField(read_only=True)
    available_vehicles = serializers.IntegerField(read_only=True)

    class Meta:
        model = Fleet
        fields = (
            'id',
            'branch',
            'branch_name',
            'name',
            'description',
            'is_active',
            'total_vehicles',
            'available_vehicles',
            'created_at',
        )
        read_only_fields = ('id', 'created_at')


class FleetVehicleSerializer(serializers.ModelSerializer):
    fleet_name = serializers.CharField(
        source='fleet.name',
        read_only=True
    )
    branch_name = serializers.CharField(
        source='fleet.branch.name',
        read_only=True
    )
    driver_name = serializers.CharField(
        source='driver.user.full_name',
        read_only=True
    )
    vehicle_type_name = serializers.CharField(
        source='vehicle_type.name',
        read_only=True
    )

    class Meta:
        model = FleetVehicle
        fields = (
            'id',
            'fleet',
            'fleet_name',
            'branch_name',
            'vehicle_type',
            'vehicle_type_name',
            'driver',
            'driver_name',
            'plate_number',
            'brand',
            'model',
            'year',
            'color',
            'status',

            # Documents
            'license_number',
            'registration_number',
            'insurance_number',
            'insurance_expiry',
            'license_expiry',
            'registration_expiry',

            'current_lat',
            'current_lng',
            'last_location_update',
            'last_service_date',
            'next_service_date',
            'mileage',
            'notes',
            'created_at',
        )
        read_only_fields = ('id', 'created_at')





class DispatchSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(
        source='branch.name',
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
    vehicle_plate = serializers.CharField(
        source='fleet_vehicle.plate_number',
        read_only=True
    )

    class Meta:
        model = Dispatch
        fields = (
            'id',
            'reference',
            'branch',
            'branch_name',
            'fleet',
            'fleet_vehicle',
            'vehicle_plate',
            'driver',
            'driver_name',
            'driver_phone',
            'dispatch_type',
            'delivery',
            'shipment',
            'status',
            'assigned_at',
            'picked_up_at',
            'delivered_at',
            'current_lat',
            'current_lng',
            'notes',
            'priority',
            'created_at',
        )
        read_only_fields = (
            'id',
            'reference',
            'created_at',
        )


class FuelTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = FuelType
        fields = (
            'id',
            'name',
            'unit',
            'price_per_unit',
            'is_active',
            'created_at',
        )
        read_only_fields = ('id', 'created_at')


class FuelRecordSerializer(serializers.ModelSerializer):
    vehicle_plate = serializers.CharField(
        source='fleet_vehicle.plate_number',
        read_only=True
    )
    driver_name = serializers.CharField(
        source='driver.user.full_name',
        read_only=True
    )
    branch_name = serializers.CharField(
        source='branch.name',
        read_only=True
    )
    fuel_type_name = serializers.CharField(
        source='fuel_type.name',
        read_only=True
    )
    km_per_litre = serializers.FloatField(read_only=True)

    class Meta:
        model = FuelRecord
        fields = (
            'id',
            'fleet_vehicle',
            'vehicle_plate',
            'driver',
            'driver_name',
            'branch',
            'branch_name',
            'fuel_type',
            'fuel_type_name',
            'record_type',
            'quantity',
            'price_per_unit',
            'total_cost',
            'mileage_before',
            'mileage_after',
            'km_per_litre',
            'station_name',
            'station_location',
            'receipt_number',
            'receipt_image',
            'notes',
            'created_at',
        )
        read_only_fields = (
            'id',
            'total_cost',
            'km_per_litre',
            'created_at',
        )



class MaintenanceRecordSerializer(serializers.ModelSerializer):
    vehicle_plate_display = serializers.CharField(
        source='fleet_vehicle.plate_number',
        read_only=True
    )
    branch_name = serializers.CharField(
        source='branch.name',
        read_only=True
    )
    maintenance_type_name = serializers.CharField(
        source='maintenance_type.name',
        read_only=True
    )
    performed_by_name = serializers.CharField(
        source='performed_by.full_name',
        read_only=True
    )

    class Meta:
        model = MaintenanceRecord
        fields = (
            'id',
            'fleet_vehicle',
            'vehicle_plate_display',
            'branch',
            'branch_name',
            'maintenance_type',
            'maintenance_type_name',

            # Vehicle details
            'vehicle_name',
            'vehicle_model',
            'plate_number',
            'license_number',
            'registration_number',

            # Maintenance details
            'title',
            'description',
            'status',
            'priority',
            'scheduled_date',
            'started_at',
            'completed_at',
            'estimated_cost',
            'actual_cost',
            'mileage_at_service',
            'next_service_mileage',
            'service_provider',
            'service_location',
            'performed_by',
            'performed_by_name',
            'parts_replaced',
            'notes',
            'receipt_image',
            'created_at',
        )
        read_only_fields = (
            'id',
            'started_at',
            'completed_at',
            'created_at',
        )


class MaintenanceTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaintenanceType
        fields = (
            'id',
            'name',
            'description',
            'is_active',
            'created_at',
        )
        read_only_fields = ('id', 'created_at')


class MaintenanceRecordSerializer(serializers.ModelSerializer):
    vehicle_plate = serializers.CharField(
        source='fleet_vehicle.plate_number',
        read_only=True
    )
    branch_name = serializers.CharField(
        source='branch.name',
        read_only=True
    )
    maintenance_type_name = serializers.CharField(
        source='maintenance_type.name',
        read_only=True
    )
    performed_by_name = serializers.CharField(
        source='performed_by.full_name',
        read_only=True
    )

    class Meta:
        model = MaintenanceRecord
        fields = (
            'id',
            'fleet_vehicle',
            'vehicle_plate',
            'branch',
            'branch_name',
            'maintenance_type',
            'maintenance_type_name',
            'title',
            'description',
            'status',
            'priority',
            'scheduled_date',
            'started_at',
            'completed_at',
            'estimated_cost',
            'actual_cost',
            'mileage_at_service',
            'next_service_mileage',
            'service_provider',
            'service_location',
            'performed_by',
            'performed_by_name',
            'parts_replaced',
            'notes',
            'receipt_image',
            'created_at',
        )
        read_only_fields = (
            'id',
            'started_at',
            'completed_at',
            'created_at',
        )


class BranchManagerSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(
        source='user.full_name',
        read_only=True
    )
    user_email = serializers.CharField(
        source='user.email',
        read_only=True
    )
    user_phone = serializers.CharField(
        source='user.phone',
        read_only=True
    )
    branch_name = serializers.CharField(
        source='branch.name',
        read_only=True
    )

    class Meta:
        model = BranchManager
        fields = (
            'id',
            'branch',
            'branch_name',
            'user',
            'user_name',
            'user_email',
            'user_phone',
            'status',
            'assigned_date',
            'end_date',
            'can_approve_dispatches',
            'can_manage_fleet',
            'can_manage_drivers',
            'can_view_reports',
            'can_manage_fuel',
            'can_manage_maintenance',
            'notes',
            'created_at',
        )
        read_only_fields = ('id', 'created_at')