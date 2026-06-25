from django.urls import path
from .views import (
    BookableItemListCreateView,
    BookableItemDetailView,
    BookingPolicyView,
    CheckAvailabilityView,
    GetAvailableSlotsView,
    BookingListCreateView,
    BookingDetailView,
    CancelBookingView,
    VendorBookingListView,
    VendorUpdateBookingView,
    ItemCalendarView,
    SetAvailabilityView,
    BookingPaymentView,
    BookingGuestView,
    ValidateCouponView,
    BookingCouponListCreateView,
    BookingInvoiceView,
    BookingReminderView,
)

urlpatterns = [
    # Bookable items
    path('items/', BookableItemListCreateView.as_view(), name='bookable_items'),
    path('items/<int:pk>/', BookableItemDetailView.as_view(), name='bookable_item_detail'),

    # Policy
    path('items/<int:item_id>/policy/', BookingPolicyView.as_view(), name='booking_policy'),

    # Availability
    path('check-availability/', CheckAvailabilityView.as_view(), name='check_availability'),
    path('items/<int:item_id>/slots/', GetAvailableSlotsView.as_view(), name='available_slots'),
    path('items/<int:item_id>/calendar/', ItemCalendarView.as_view(), name='item_calendar'),
    path('items/<int:item_id>/availability/', SetAvailabilityView.as_view(), name='set_availability'),

    # Bookings
    path('', BookingListCreateView.as_view(), name='bookings'),
    path('<int:pk>/', BookingDetailView.as_view(), name='booking_detail'),
    path('<int:pk>/cancel/', CancelBookingView.as_view(), name='cancel_booking'),

    # Booking payments
    path('<int:pk>/payments/', BookingPaymentView.as_view(), name='booking_payments'),

    # Booking guests
    path('<int:pk>/guests/', BookingGuestView.as_view(), name='booking_guests'),
    path('<int:pk>/guests/<int:guest_id>/', BookingGuestView.as_view(), name='remove_guest'),

    # Invoice
    path('<int:pk>/invoice/', BookingInvoiceView.as_view(), name='booking_invoice'),

    # Reminders
    path('<int:pk>/reminders/', BookingReminderView.as_view(), name='booking_reminders'),

    # Coupons
    path('coupons/', BookingCouponListCreateView.as_view(), name='booking_coupons'),
    path('coupons/validate/', ValidateCouponView.as_view(), name='validate_coupon'),

    # Vendor
    path('business/<int:business_id>/', VendorBookingListView.as_view(), name='vendor_bookings'),
    path('business/<int:business_id>/<int:pk>/', VendorUpdateBookingView.as_view(), name='vendor_update_booking'),
]