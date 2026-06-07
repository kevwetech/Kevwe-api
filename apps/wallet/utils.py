from apps.common.utils import generate_reference


def get_or_create_wallet(user):
    """Get or create wallet for user"""
    from .models import Wallet
    wallet, created = Wallet.objects.get_or_create(user=user)
    return wallet


def calculate_withdrawal_fee(amount):
    """
    Calculate withdrawal fee
    ₦50 flat fee or 1% whichever is higher
    Maximum fee: ₦500
    """
    flat_fee = 50
    percentage_fee = float(amount) * 0.01
    fee = max(flat_fee, percentage_fee)
    fee = min(fee, 500)
    return round(fee, 2)


def mark_payment_as_paid(payment_for, object_id):
    """Mark order/booking/ride as paid via wallet"""
    try:
        if payment_for == 'order':
            from apps.orders.models import Order
            order = Order.objects.get(pk=object_id)
            order.payment_status = 'paid'
            order.status = 'confirmed'
            order.save()

        elif payment_for == 'booking':
            from apps.bookings.models import Booking
            booking = Booking.objects.get(pk=object_id)
            booking.payment_status = 'paid'
            booking.status = 'confirmed'
            booking.save()

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

        elif payment_for == 'delivery':
            from apps.deliveries.models import DeliveryRequest
            delivery = DeliveryRequest.objects.get(pk=object_id)
            delivery.payment_status = 'paid'
            delivery.save()

        elif payment_for == 'subscription':
            from apps.subscriptions.models import Subscription
            subscription = Subscription.objects.get(pk=object_id)
            subscription.status = 'active'
            subscription.save()

        return True
    except Exception:
        return False