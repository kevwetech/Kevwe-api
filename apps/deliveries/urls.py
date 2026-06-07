from django.urls import path
from .views import (
    DeliveryZoneListView,
    DeliveryRequestListCreateView,
    DeliveryRequestDetailView,
    TrackDeliveryView,
    RateDeliveryView,
    DriverDeliveryView,
    UploadDeliveryProofView,
    AdminDeliveryListView,
    AdminDeliveryUpdateView,
)

urlpatterns = [
    # Delivery zones
    path('zones/', DeliveryZoneListView.as_view(), name='delivery_zones'),

    # Customer endpoints
    path('', DeliveryRequestListCreateView.as_view(), name='deliveries'),
    path('<int:pk>/', DeliveryRequestDetailView.as_view(), name='delivery_detail'),
    path('<int:pk>/rate/', RateDeliveryView.as_view(), name='rate_delivery'),

    # Public tracking
    path('track/<str:tracking_number>/', TrackDeliveryView.as_view(), name='track_delivery'),

    # Dispatcher endpoints
    path('driver/', DriverDeliveryView.as_view(), name='driver_deliveries'),
    path('driver/<int:pk>/', DriverDeliveryView.as_view(), name='driver_delivery_update'),
    path('driver/<int:pk>/proof/', UploadDeliveryProofView.as_view(), name='upload_proof'),

    # Admin endpoints
    path('admin/', AdminDeliveryListView.as_view(), name='admin_deliveries'),
    path('admin/<int:pk>/', AdminDeliveryUpdateView.as_view(), name='admin_delivery_update'),
]