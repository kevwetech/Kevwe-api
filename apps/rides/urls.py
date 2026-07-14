from django.urls import path
# ── Add these to apps/rides/urls.py ──────────────
# (append after existing urlpatterns)

from .views import (
    # existing
    VehicleTypeListView, EstimateFareView, RequestRideView,
    RideDetailView, RideListView, RateRideView,
    DriverRideView, AdminRideListView,
    # new transport
    TransportRouteSearchView, TransportRouteListView,
    TransportScheduleListView, TransportScheduleDetailView,
    BookTransportView, MyTransportBookingsView,
    TransportBookingDetailView, TransportBoardingView,
    TransportTrackingView, TransportRatingView,
    TransportVehicleView, TransportCancellationPolicyView,
    VerifyRideStartView, TransportRouteDetailView, 
    TransportRouteCreateView, VehicleTypeDetailView
)

urlpatterns = [
    # ── Ride-hailing (existing) ───────────────────
    path('vehicle-types/',          VehicleTypeListView.as_view(),   name='vehicle_types'),
    path('estimate/',               EstimateFareView.as_view(),      name='estimate_fare'),
    path('request/',                RequestRideView.as_view(),       name='request_ride'),
    path('my-rides/',               RideListView.as_view(),          name='my_rides'),
    path('<int:pk>/',               RideDetailView.as_view(),        name='ride_detail'),
    path('<int:pk>/rate/',          RateRideView.as_view(),          name='rate_ride'),
    path('driver/rides/',           DriverRideView.as_view(),        name='driver_rides'),
    path('driver/rides/<int:pk>/',  DriverRideView.as_view(),        name='driver_ride_update'),
    path('admin/',                  AdminRideListView.as_view(),     name='admin_rides'),

    # ── Transport module ──────────────────────────
    # Routes
    path('transport/routes/',                   TransportRouteListView.as_view(),        name='transport_routes'),
    path('transport/routes/search/',            TransportRouteSearchView.as_view(),      name='transport_route_search'),
    path('vehicle-types/<int:pk>/', VehicleTypeDetailView.as_view(), name='vehicle_type_detail'),
    path('routes/', TransportRouteCreateView.as_view(), name='transport_route_create'),
    path('routes/<int:pk>/', TransportRouteDetailView.as_view(), name='transport_route_detail'),


    # Schedules
    path('transport/schedules/',                TransportScheduleListView.as_view(),     name='transport_schedules'),
    path('transport/schedules/<int:pk>/',       TransportScheduleDetailView.as_view(),   name='transport_schedule_detail'),
    path('transport/schedules/<int:pk>/tracking/', TransportTrackingView.as_view(),      name='transport_tracking'),

    # Bookings
    path('transport/book/',                     BookTransportView.as_view(),             name='transport_book'),
    path('transport/my-bookings/',              MyTransportBookingsView.as_view(),       name='my_transport_bookings'),
    path('transport/bookings/<int:pk>/',        TransportBookingDetailView.as_view(),    name='transport_booking_detail'),
    path('transport/bookings/<int:pk>/rate/',   TransportRatingView.as_view(),           name='transport_rate'),
    

    # Boarding
    path('transport/board/',                    TransportBoardingView.as_view(),         name='transport_board'),

    # Fleet management
    path('transport/vehicles/',                 TransportVehicleView.as_view(),          name='transport_vehicles'),

    # Cancellation policy
    path('transport/cancellation-policy/',      TransportCancellationPolicyView.as_view(), name='transport_cancellation_policy'),

    path('<int:pk>/verify-start/', VerifyRideStartView.as_view(), name='verify_ride_start'),
]