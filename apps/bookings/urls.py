from django.urls import path
from .views import (
    BookableItemListCreateView,
    BookableItemDetailView,
    BookingListCreateView,
    BookingDetailView,
    AdminBookingListView,
    AdminBookingUpdateView,
    BookingTrackingView,
)

urlpatterns = [
    # Bookable items
    path('items/', BookableItemListCreateView.as_view(), name='bookable_items'),
    path('items/<int:pk>/', BookableItemDetailView.as_view(), name='bookable_item_detail'),

    # Bookings
    path('', BookingListCreateView.as_view(), name='bookings'),
    path('<int:pk>/', BookingDetailView.as_view(), name='booking_detail'),
    path('<int:pk>/tracking/', BookingTrackingView.as_view(), name='booking_tracking'),

    # Admin
    path('admin/', AdminBookingListView.as_view(), name='admin_bookings'),
    path('admin/<int:pk>/', AdminBookingUpdateView.as_view(), name='admin_booking_update'),
]