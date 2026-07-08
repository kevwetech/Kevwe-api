from django.urls import path
from apps.tracking.consumers import (
    RideTrackingConsumer,
    DriverRideConsumer,
    ShipmentTrackingConsumer,
    DriverShipmentConsumer,
    BookingTrackingConsumer,
    AppointmentTrackingConsumer,
    ServiceTrackingConsumer,
)
from apps.deliveries.consumers import DeliveryTrackingConsumer


websocket_urlpatterns = [
    # existing
    path('ws/rides/<int:ride_id>/',               RideTrackingConsumer.as_asgi()),
    path('ws/driver/rides/<int:driver_id>/',      DriverRideConsumer.as_asgi()),
    path('ws/shipments/<str:tracking_number>/',   ShipmentTrackingConsumer.as_asgi()),
    path('ws/driver/shipments/<int:driver_id>/',  DriverShipmentConsumer.as_asgi()),
    path('ws/deliveries/<str:tracking_number>/',  DeliveryTrackingConsumer.as_asgi()),
    # new
    path('ws/bookings/<str:reference>/',          BookingTrackingConsumer.as_asgi()),
    path('ws/appointments/<str:reference>/',      AppointmentTrackingConsumer.as_asgi()),
    path('ws/services/<str:reference>/',          ServiceTrackingConsumer.as_asgi()),
]