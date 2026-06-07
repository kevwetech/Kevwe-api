from django.urls import path
from .views import (
    BranchListCreateView,
    BranchDetailView,
    TerritoryListCreateView,
    TerritoryDetailView,
    FleetListCreateView,
    FleetDetailView,
    FleetVehicleListCreateView,
    FleetVehicleDetailView,
    AssignDriverToVehicleView,
    DispatchListCreateView,
    DispatchDetailView,
    DriverDispatchView,
    OperationsDashboardView,
    FuelTypeListCreateView,
    FuelRecordListCreateView,
    FuelRecordDetailView,
    VehicleFuelReportView,
    MaintenanceTypeListCreateView,
    MaintenanceRecordListCreateView,
    MaintenanceRecordDetailView,
    BranchManagerListCreateView,
    BranchManagerDetailView,
)

urlpatterns = [
    # Dashboard
    path('dashboard/', OperationsDashboardView.as_view(), name='operations_dashboard'),

    # Branches
    path('branches/', BranchListCreateView.as_view(), name='branches'),
    path('branches/<int:pk>/', BranchDetailView.as_view(), name='branch_detail'),

    # Branch Managers
    path('managers/', BranchManagerListCreateView.as_view(), name='branch_managers'),
    path('managers/<int:pk>/', BranchManagerDetailView.as_view(), name='branch_manager_detail'),

    # Territories
    path('territories/', TerritoryListCreateView.as_view(), name='territories'),
    path('territories/<int:pk>/', TerritoryDetailView.as_view(), name='territory_detail'),

    # Fleets
    path('fleets/', FleetListCreateView.as_view(), name='fleets'),
    path('fleets/<int:pk>/', FleetDetailView.as_view(), name='fleet_detail'),

    # Fleet Vehicles
    path('vehicles/', FleetVehicleListCreateView.as_view(), name='fleet_vehicles'),
    path('vehicles/<int:pk>/', FleetVehicleDetailView.as_view(), name='fleet_vehicle_detail'),
    path('vehicles/<int:pk>/assign-driver/', AssignDriverToVehicleView.as_view(), name='assign_driver_vehicle'),
    path('vehicles/<int:pk>/fuel-report/', VehicleFuelReportView.as_view(), name='vehicle_fuel_report'),

    # Dispatches
    path('dispatches/', DispatchListCreateView.as_view(), name='dispatches'),
    path('dispatches/<int:pk>/', DispatchDetailView.as_view(), name='dispatch_detail'),

    # Driver dispatches
    path('driver/dispatches/', DriverDispatchView.as_view(), name='driver_dispatches'),
    path('driver/dispatches/<int:pk>/', DriverDispatchView.as_view(), name='driver_dispatch_update'),

    # Fuel
    path('fuel-types/', FuelTypeListCreateView.as_view(), name='fuel_types'),
    path('fuel-records/', FuelRecordListCreateView.as_view(), name='fuel_records'),
    path('fuel-records/<int:pk>/', FuelRecordDetailView.as_view(), name='fuel_record_detail'),

    # Maintenance
    path('maintenance-types/', MaintenanceTypeListCreateView.as_view(), name='maintenance_types'),
    path('maintenance/', MaintenanceRecordListCreateView.as_view(), name='maintenance_records'),
    path('maintenance/<int:pk>/', MaintenanceRecordDetailView.as_view(), name='maintenance_record_detail'),
]