from django.urls import path
from .views import (
    RegisterDriverView,
    DriverProfileView,
    DriverAvailabilityView,
    UpdateLocationView,
    VehicleListCreateView,
    VehicleDetailView,
    SetActiveVehicleView,
    DriverDocumentView,
    DriverEarningsView,
    NearbyDriversView,
    AdminDriverListView,
    AdminDriverVerifyView,
    VehicleTypeListCreateView,   # ← add this
    VehicleTypeDetailView,
)

urlpatterns = [
    # Driver registration & profile
    path('register/', RegisterDriverView.as_view(), name='driver_register'),
    path('profile/', DriverProfileView.as_view(), name='driver_profile'),
    path('availability/', DriverAvailabilityView.as_view(), name='driver_availability'),
    path('location/', UpdateLocationView.as_view(), name='driver_location'),

    # Vehicles
    path('vehicles/', VehicleListCreateView.as_view(), name='driver_vehicles'),
    path('vehicles/<int:pk>/', VehicleDetailView.as_view(), name='driver_vehicle_detail'),
    path('vehicles/<int:pk>/set-active/', SetActiveVehicleView.as_view(), name='set_active_vehicle'),

    # Vehicle types
    path('vehicle-types/', VehicleTypeListCreateView.as_view(), name='vehicle_types'),
    path('vehicle-types/<int:pk>/', VehicleTypeDetailView.as_view(), name='vehicle_type_detail'),

    # Documents
    path('documents/', DriverDocumentView.as_view(), name='driver_documents'),

    # Earnings
    path('earnings/', DriverEarningsView.as_view(), name='driver_earnings'),

    # Nearby drivers
    path('nearby/', NearbyDriversView.as_view(), name='nearby_drivers'),

    # Admin
    path('admin/', AdminDriverListView.as_view(), name='admin_drivers'),
    path('admin/<int:pk>/verify/', AdminDriverVerifyView.as_view(), name='admin_driver_verify'),
]