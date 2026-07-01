"""
Centralized vendor/driver earnings crediting.
Vendor (business) earnings go to PENDING until delivery/booking confirmed.
Driver earnings go directly to their regular Wallet (available immediately).
"""
from decimal import Decimal
from apps.common.utils import generate_reference


def credit_order_earnings(order):
    """
    Credit vendor and driver earnings after an order is paid.
    Vendor earnings → VendorWallet (pending until delivery confirmed)
    Driver earnings → regular Wallet (available immediately)
    """
    # ── Vendor (business) earnings → VendorWallet pending ──
    if order.business and order.business_earnings:
        try:
            from .models import VendorWallet
            vendor_wallet, _ = VendorWallet.objects.get_or_create(
                business=order.business,
                defaults={
                    'user': order.business.owner,
                    'settlement_period_days': 1
                }
            )
            vendor_wallet.credit_earning(
                amount=order.business_earnings,
                description=(
                    f'Earnings from order {order.order_number} '
                    f'(pending delivery confirmation)'
                ),
                reference=generate_reference('VND'),
                order=order,
                settlement_days=1,
            )
            print(
                f"Vendor pending ₦{order.business_earnings} "
                f"for order {order.order_number}"
            )
        except Exception as e:
            print(f"Vendor earning credit error: {e}")

    # ── Driver earnings → regular Wallet (available immediately) ──
    if order.driver and order.driver_earnings:
        try:
            from apps.wallet.utils import get_or_create_wallet
            wallet = get_or_create_wallet(order.driver.user)
            wallet.credit(
                amount=order.driver_earnings,
                description=(
                    f'Delivery earnings for order '
                    f'{order.order_number}'
                ),
                reference=generate_reference('DRV'),
            )
            print(
                f"Driver credited ₦{order.driver_earnings} "
                f"for order {order.order_number}"
            )
        except Exception as e:
            print(f"Driver earning credit error: {e}")


def settle_order_earnings(order):
    """
    Move vendor business earnings from pending → available
    after delivery is confirmed (OTP verified).
    Driver earnings already credited — nothing to settle.
    """
    if not order.business:
        return

    try:
        from .models import VendorWallet
        wallet = VendorWallet.objects.filter(
            business=order.business,
        ).first()
        if wallet:
            settled = wallet.settle_for_order(order)
            print(
                f"Vendor settled ₦{settled} "
                f"for order {order.order_number}"
            )
    except Exception as e:
        print(f"Vendor settlement error: {e}")


def credit_booking_earnings(booking):
    """
    Credit vendor earnings after a booking is paid.
    Goes to VendorWallet pending until check-in.
    """
    if not booking.business or not booking.business_earnings:
        return

    try:
        from .models import VendorWallet
        vendor_wallet, _ = VendorWallet.objects.get_or_create(
            business=booking.business,
            defaults={
                'user': booking.business.owner,
                'settlement_period_days': 1
            }
        )
        vendor_wallet.credit_earning(
            amount=booking.business_earnings,
            description=(
                f'Earnings from booking {booking.booking_number} '
                f'(pending check-in)'
            ),
            reference=generate_reference('BKG'),
            booking=booking,
            settlement_days=1,
        )
        print(
            f"Vendor pending ₦{booking.business_earnings} "
            f"for booking {booking.booking_number}"
        )
    except Exception as e:
        print(f"Booking earning credit error: {e}")


def settle_booking_earnings(booking):
    """
    Move vendor earnings from pending → available
    after guest checks in.
    """
    if not booking.business:
        return

    try:
        from .models import VendorWallet
        wallet = VendorWallet.objects.filter(
            business=booking.business,
        ).first()
        if wallet:
            settled = wallet.settle_for_booking(booking)
            print(
                f"Vendor settled ₦{settled} "
                f"for booking {booking.booking_number}"
            )
    except Exception as e:
        print(f"Booking settlement error: {e}")