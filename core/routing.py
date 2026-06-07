from django.urls import path
from apps.tracking.consumers import (
    RideTrackingConsumer,
    DriverRideConsumer,
    ShipmentTrackingConsumer,
    DriverShipmentConsumer,
)
from apps.deliveries.consumers import DeliveryTrackingConsumer

websocket_urlpatterns = [
    # Ride tracking
    path('ws/rides/<int:ride_id>/', RideTrackingConsumer.as_asgi()),
    path('ws/driver/rides/<int:driver_id>/', DriverRideConsumer.as_asgi()),

    # Shipment tracking
    path('ws/shipments/<str:tracking_number>/', ShipmentTrackingConsumer.as_asgi()),
    path('ws/driver/shipments/<int:driver_id>/', DriverShipmentConsumer.as_asgi()),

    # Delivery tracking
    path('ws/deliveries/<str:tracking_number>/', DeliveryTrackingConsumer.as_asgi()),
]