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
    GenerateDeliveryOTPView,
    MarkDeliveredView,
    ShipmentServiceCategoryDetailView,
    ShipmentServiceCategoryListCreateView,
    ShipmentVehicleTypeDetailView,
    ShipmentVehicleTypeListCreateView,
    ShipmentVehicleCategoryListView
)

urlpatterns = [
    # Sender endpoints
    path('', ShipmentListCreateView.as_view(), name='shipments'),
    path('<int:pk>/', ShipmentDetailView.as_view(), name='shipment_detail'),
    path('estimate/', EstimateShipmentPriceView.as_view(), name='estimate_shipment'),

    path('vehicle-categories/', ShipmentVehicleCategoryListView.as_view(), name='shipment_vehicle_categories'),
    path('vehicle-types/', ShipmentVehicleTypeListCreateView.as_view(), name='shipment_vehicle_types'),
    path('vehicle-types/<int:pk>/', ShipmentVehicleTypeDetailView.as_view(), name='shipment_vehicle_type_detail'),
    path('service-categories/', ShipmentServiceCategoryListCreateView.as_view(), name='shipment_service_categories'),
    path('service-categories/<int:pk>/', ShipmentServiceCategoryDetailView.as_view(), name='shipment_service_category_detail'),

    # Public tracking
    path('track/<str:tracking_number>/', TrackShipmentView.as_view(), name='track_shipment'),
    path('<int:pk>/generate-otp/', GenerateDeliveryOTPView.as_view(), name='generate_delivery_otp'),
    path('<int:pk>/verify-delivery/', VerifyShipmentDeliveryView.as_view(), name='verify_delivery'),
    path('<int:pk>/mark-delivered/', MarkDeliveredView.as_view(), name='mark_delivered'),
    # Admin endpoints
    path('admin/', AdminShipmentListView.as_view(), name='admin_shipments'),
    path('admin/<int:pk>/', AdminShipmentUpdateView.as_view(), name='admin_shipment_update'),
    path('admin/<int:pk>/assign-driver/', AssignDriverView.as_view(), name='assign_driver'),
]