import uuid
from apps.common.utils import generate_reference


def get_payment_amount(payment_for, object_id):
    """Get amount for different payment types"""
    try:
        if payment_for == 'order':
            from apps.orders.models import Order
            obj = Order.objects.get(pk=object_id)
            return obj.total, obj.user

        elif payment_for == 'booking':
            from apps.bookings.models import Booking
            obj = Booking.objects.get(pk=object_id)
            return obj.total, obj.user

        elif payment_for == 'ride':
            from apps.rides.models import Ride
            obj = Ride.objects.get(pk=object_id)
            return obj.estimated_fare, obj.rider

        elif payment_for == 'shipment':
            from apps.shipments.models import Shipment
            obj = Shipment.objects.get(pk=object_id)
            return obj.price, obj.sender

    except Exception:
        return None, None


def mark_as_paid(payment_for, object_id):
    """Mark order/booking/ride/shipment as paid"""
    try:
        if payment_for == 'order':
            from apps.orders.models import Order
            order = Order.objects.get(pk=object_id)
            order.payment_status = 'paid'
            order.status = 'confirmed'
            order.save()

            # Send notification
            from apps.notifications.utils import send_order_notification
            send_order_notification(
                user=order.user,
                order=order,
                notification_type='order_confirmed'
            )

        elif payment_for == 'booking':
            from apps.bookings.models import Booking
            booking = Booking.objects.get(pk=object_id)
            booking.payment_status = 'paid'
            booking.status = 'confirmed'
            booking.save()

            # Send notification
            from apps.notifications.utils import send_booking_notification
            send_booking_notification(
                user=booking.user,
                booking=booking,
                notification_type='booking_confirmed'
            )

        elif payment_for == 'ride':
            from apps.rides.models import Ride
            ride = Ride.objects.get(pk=object_id)
            ride.payment_status = 'paid'
            ride.save()

        elif payment_for == 'shipment':
            from apps.shipments.models import Shipment
            shipment = Shipment.objects.get(pk=object_id)
            shipment.payment_status = 'paid'
            shipment.save()

        return True
    except Exception:
        return False