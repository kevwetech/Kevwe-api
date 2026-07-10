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

        elif payment_for == 'service':
            from apps.services.models import ServiceRequest
            obj = ServiceRequest.objects.get(pk=object_id)
            return obj.final_total, obj.customer

        elif payment_for == 'appointment':
            from apps.appointments.models import Appointment
            obj = Appointment.objects.get(pk=object_id)
            return obj.total_amount, obj.customer

        elif payment_for == 'transport':
            from apps.rides.models import TransportBooking
            obj = TransportBooking.objects.get(pk=object_id)
            return obj.total_amount, obj.customer

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

        elif payment_for == 'ride':
            from apps.rides.models import Ride
            ride = Ride.objects.get(pk=object_id)
            ride.payment_status = 'paid'
            ride.save()
            # Hold in escrow until trip completes
            from apps.payments.escrow import hold_funds
            hold_funds(
                interaction_type='ride',
                interaction_id=ride.id,
                customer=ride.rider,
                business=None,  # platform rides — or driver's business if fleet
                amount=ride.estimated_fare,
                interaction_ref=ride.reference,
            )

        elif payment_for == 'shipment':
            from apps.shipments.models import Shipment
            shipment = Shipment.objects.get(pk=object_id)
            shipment.payment_status = 'paid'
            shipment.save()
            from apps.payments.escrow import hold_funds
            hold_funds(
                interaction_type='shipment',
                interaction_id=shipment.id,
                customer=shipment.sender,
                business=shipment.business,
                amount=shipment.price,
                interaction_ref=shipment.tracking_number,
                auto_release_days=3,
            )

        elif payment_for == 'service':
            from apps.services.models import ServiceRequest
            sr = ServiceRequest.objects.get(pk=object_id)
            sr.status = 'paid'
            sr.save()
            from apps.payments.escrow import hold_funds
            hold_funds(
                interaction_type='service',
                interaction_id=sr.id,
                customer=sr.customer,
                business=sr.business,
                amount=sr.final_total,
                interaction_ref=sr.reference,
                auto_release_days=3,
            )

        elif payment_for == 'appointment':
            from apps.appointments.models import Appointment
            appt = Appointment.objects.get(pk=object_id)
            appt.payment_status = 'paid'
            appt.save()
            from apps.payments.escrow import hold_funds
            hold_funds(
                interaction_type='appointment',
                interaction_id=appt.id,
                customer=appt.customer,
                business=appt.business,
                amount=appt.total_amount,
                interaction_ref=appt.reference,
                auto_release_days=1,
            )

        elif payment_for == 'transport':
            from apps.rides.models import TransportBooking
            tb = TransportBooking.objects.get(pk=object_id)
            tb.payment_status = 'paid'
            tb.status = 'confirmed'
            tb.save()
            from apps.payments.escrow import hold_funds
            hold_funds(
                interaction_type='transport',
                interaction_id=tb.id,
                customer=tb.customer,
                business=tb.business,
                amount=tb.total_amount,
                interaction_ref=tb.reference,
            )

        return True
    except Exception:
        return False