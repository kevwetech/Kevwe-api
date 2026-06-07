from django.contrib import admin
from .models import (
    Branch, Territory, Fleet, FleetVehicle,
    Dispatch, FuelType, FuelRecord,
    MaintenanceType, MaintenanceRecord, BranchManager
)

@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'code', 'branch_type',
        'status', 'city', 'is_active'
    )
    list_filter = ('branch_type', 'status', 'is_active')
    search_fields = ('name', 'code', 'email')
    ordering = ('name',)


@admin.register(Territory)
class TerritoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'branch', 'is_active')
    list_filter = ('is_active', 'branch')
    search_fields = ('name',)
    ordering = ('name',)


@admin.register(Fleet)
class FleetAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'branch',
        'total_vehicles', 'available_vehicles',
        'is_active'
    )
    list_filter = ('is_active', 'branch')
    search_fields = ('name',)
    ordering = ('name',)


@admin.register(FleetVehicle)
class FleetVehicleAdmin(admin.ModelAdmin):
    list_display = (
        'plate_number', 'brand', 'model',
        'fleet', 'driver', 'status'
    )
    list_filter = ('status', 'fleet__branch')
    search_fields = ('plate_number', 'brand', 'model')
    ordering = ('plate_number',)


@admin.register(Dispatch)
class DispatchAdmin(admin.ModelAdmin):
    list_display = (
        'reference', 'dispatch_type', 'branch',
        'driver', 'status', 'created_at'
    )
    list_filter = ('dispatch_type', 'status', 'branch')
    search_fields = ('reference',)
    ordering = ('-created_at',)

@admin.register(FuelType)
class FuelTypeAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'unit', 'price_per_unit', 'is_active'
    )
    list_filter = ('is_active',)
    search_fields = ('name',)

@admin.register(FuelRecord)
class FuelRecordAdmin(admin.ModelAdmin):
    list_display = (
        'fleet_vehicle', 'driver', 'record_type',
        'quantity', 'total_cost', 'created_at'
    )
    list_filter = ('record_type', 'fuel_type')
    search_fields = ('fleet_vehicle__plate_number',)
    ordering = ('-created_at',)



@admin.register(MaintenanceType)
class MaintenanceTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)

@admin.register(MaintenanceRecord)
class MaintenanceRecordAdmin(admin.ModelAdmin):
    list_display = (
        'fleet_vehicle', 'title', 'status',
        'priority', 'scheduled_date',
        'estimated_cost', 'actual_cost'
    )
    list_filter = ('status', 'priority')
    search_fields = (
        'fleet_vehicle__plate_number', 'title'
    )
    ordering = ('-created_at',)

@admin.register(BranchManager)
class BranchManagerAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'branch', 'status',
        'assigned_date', 'end_date'
    )
    list_filter = ('status', 'branch')
    search_fields = ('user__email', 'branch__name')
    ordering = ('-created_at',)