from django.urls import path
from .views import (
    ShipmentListCreateView,
    ShipmentDetailView,
    TrackShipmentView,
    AdminShipmentListView,
    AdminShipmentUpdateView,
    AssignDriverView,
    EstimateShipmentPriceView,
    VerifyShipmentDeliveryView, 
    GenerateDeliveryOTPView

)

urlpatterns = [
    # Sender endpoints
    path('', ShipmentListCreateView.as_view(), name='shipments'),
    path('<int:pk>/', ShipmentDetailView.as_view(), name='shipment_detail'),
    path('estimate/', EstimateShipmentPriceView.as_view(), name='estimate_shipment'),

    # Public tracking
    path('track/<str:tracking_number>/', TrackShipmentView.as_view(), name='track_shipment'),
    path('<int:pk>/generate-otp/', GenerateDeliveryOTPView.as_view(), name='generate_delivery_otp'),
    path('<int:pk>/verify-delivery/', VerifyShipmentDeliveryView.as_view(), name='verify_delivery'),

    # Admin endpoints
    path('admin/', AdminShipmentListView.as_view(), name='admin_shipments'),
    path('admin/<int:pk>/', AdminShipmentUpdateView.as_view(), name='admin_shipment_update'),
    path('admin/<int:pk>/assign-driver/', AssignDriverView.as_view(), name='assign_driver'),
]