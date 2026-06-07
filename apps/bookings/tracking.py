from .models import BookingTracking


BOOKING_STEPS = [
    {
        'status': 'pending',
        'label': 'Booking Requested',
        'description': 'Your booking request has been received',
        'icon': '📋'
    },
    {
        'status': 'confirmed',
        'label': 'Booking Confirmed',
        'description': 'Your booking has been confirmed',
        'icon': '✅'
    },
    {
        'status': 'checked_in',
        'label': 'Checked In',
        'description': 'You have successfully checked in',
        'icon': '🏨'
    },
    {
        'status': 'checked_out',
        'label': 'Checked Out',
        'description': 'You have successfully checked out',
        'icon': '👋'
    },
]


def create_booking_tracking(booking, status, description=None):
    """Create a tracking entry for a booking"""
    default_description = next(
        (step['description'] for step in BOOKING_STEPS
         if step['status'] == status),
        'Booking status updated'
    )
    return BookingTracking.objects.create(
        booking=booking,
        status=status,
        description=description or default_description,
    )


def get_booking_tracking_data(booking):
    """Get full tracking data for a booking"""
    tracking_entries = BookingTracking.objects.filter(
        booking=booking
    )
    tracking_dict = {
        entry.status: entry
        for entry in tracking_entries
    }

    steps = []
    current_index = next(
        (i for i, step in enumerate(BOOKING_STEPS)
         if step['status'] == booking.status),
        0
    )

    for i, step in enumerate(BOOKING_STEPS):
        entry = tracking_dict.get(step['status'])
        steps.append({
            'status': step['status'],
            'label': step['label'],
            'description': entry.description if entry else step['description'],
            'icon': step['icon'],
            'timestamp': entry.created_at if entry else None,
            'completed': i <= current_index,
            'current': step['status'] == booking.status,
        })

    return {
        'reference': booking.reference,
        'current_status': booking.status,
        'payment_status': booking.payment_status,
        'check_in': booking.check_in,
        'check_out': booking.check_out,
        'guest_name': booking.guest_name,
        'item_name': booking.item.name,
        'tracking_steps': steps,
        'history': [
            {
                'status': entry.status,
                'description': entry.description,
                'timestamp': entry.created_at,
            }
            for entry in tracking_entries
        ]
    }