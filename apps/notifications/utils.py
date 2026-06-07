from .models import Notification


def send_notification(user, title, message, notification_type='system', data=None):
    """
    Create a notification for a user
    Call this from anywhere in the app
    """
    return Notification.objects.create(
        user=user,
        title=title,
        message=message,
        notification_type=notification_type,
        data=data or {}
    )


def send_order_notification(user, order, notification_type):
    """Send order related notifications"""
    messages = {
        'order_placed': {
            'title': 'Order Placed Successfully',
            'message': f'Your order {order.reference} has been placed successfully. Total: ₦{order.total}'
        },
        'order_confirmed': {
            'title': 'Order Confirmed',
            'message': f'Your order {order.reference} has been confirmed and is being processed.'
        },
        'order_shipped': {
            'title': 'Order Shipped',
            'message': f'Your order {order.reference} has been shipped and is on its way!'
        },
        'order_delivered': {
            'title': 'Order Delivered',
            'message': f'Your order {order.reference} has been delivered. Enjoy!'
        },
        'order_cancelled': {
            'title': 'Order Cancelled',
            'message': f'Your order {order.reference} has been cancelled.'
        },
    }

    content = messages.get(notification_type, {
        'title': 'Order Update',
        'message': f'Your order {order.reference} has been updated.'
    })

    return send_notification(
        user=user,
        title=content['title'],
        message=content['message'],
        notification_type=notification_type,
        data={
            'order_id': order.id,
            'reference': order.reference,
            'status': order.status,
        }
    )


def send_booking_notification(user, booking, notification_type):
    """Send booking related notifications"""
    messages = {
        'booking_confirmed': {
            'title': 'Booking Confirmed',
            'message': f'Your booking {booking.reference} for {booking.item.name} has been confirmed!'
        },
        'booking_cancelled': {
            'title': 'Booking Cancelled',
            'message': f'Your booking {booking.reference} has been cancelled.'
        },
        'booking_reminder': {
            'title': 'Booking Reminder',
            'message': f'Reminder: Your booking {booking.reference} for {booking.item.name} is coming up on {booking.check_in}.'
        },
    }

    content = messages.get(notification_type, {
        'title': 'Booking Update',
        'message': f'Your booking {booking.reference} has been updated.'
    })

    return send_notification(
        user=user,
        title=content['title'],
        message=content['message'],
        notification_type=notification_type,
        data={
            'booking_id': booking.id,
            'reference': booking.reference,
            'status': booking.status,
            'check_in': str(booking.check_in),
            'check_out': str(booking.check_out),
        }
    )