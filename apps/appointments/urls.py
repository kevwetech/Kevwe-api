from django.urls import path
from .views import (
    AppointmentServiceListView, AppointmentServiceDetailView,
    AppointmentStaffListView, AppointmentAvailabilityView,
    BookAppointmentView, MyAppointmentsView,
    AppointmentDetailView, AppointmentCheckInView,
    AppointmentRatingView, AppointmentWaitlistView,
    BusinessAppointmentsView, AppointmentSlotView,
)

urlpatterns = [
    # Services
    path('services/',           AppointmentServiceListView.as_view(),   name='appointment_services'),
    path('services/<int:pk>/',  AppointmentServiceDetailView.as_view(), name='appointment_service_detail'),

    # Staff
    path('staff/',              AppointmentStaffListView.as_view(),     name='appointment_staff'),

    # Slots
    path('slots/',              AppointmentSlotView.as_view(),          name='appointment_slots'),

    # Availability
    path('availability/',       AppointmentAvailabilityView.as_view(),  name='appointment_availability'),

    # Booking
    path('book/',               BookAppointmentView.as_view(),          name='book_appointment'),
    path('my/',                 MyAppointmentsView.as_view(),           name='my_appointments'),
    path('<int:pk>/',           AppointmentDetailView.as_view(),        name='appointment_detail'),
    path('<int:pk>/rate/',      AppointmentRatingView.as_view(),        name='rate_appointment'),

    # Check-in
    path('check-in/',           AppointmentCheckInView.as_view(),       name='appointment_check_in'),

    # Waitlist
    path('waitlist/',           AppointmentWaitlistView.as_view(),      name='appointment_waitlist'),

    # Business dashboard
    path('business/<int:business_id>/', BusinessAppointmentsView.as_view(), name='business_appointments'),
]