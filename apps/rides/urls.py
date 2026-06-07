from django.urls import path
from .views import (
    VehicleTypeListView,
    EstimateFareView,
    RequestRideView,
    RideDetailView,
    RideListView,
    RateRideView,
    DriverRideView,
    AdminRideListView,
)

urlpatterns = [
    # Vehicle types
    path('vehicle-types/', VehicleTypeListView.as_view(), name='vehicle_types'),

    # Fare estimation
    path('estimate/', EstimateFareView.as_view(), name='estimate_fare'),

    # Rider endpoints
    path('request/', RequestRideView.as_view(), name='request_ride'),
    path('my-rides/', RideListView.as_view(), name='my_rides'),
    path('<int:pk>/', RideDetailView.as_view(), name='ride_detail'),
    path('<int:pk>/rate/', RateRideView.as_view(), name='rate_ride'),

    # Driver endpoints
    path('driver/rides/', DriverRideView.as_view(), name='driver_rides'),
    path('driver/rides/<int:pk>/', DriverRideView.as_view(), name='driver_ride_update'),

    # Admin endpoints
    path('admin/', AdminRideListView.as_view(), name='admin_rides'),
]