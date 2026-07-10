"""
Kevwe Escrow Engine
One release engine, multiple verification triggers.

Usage:
    from apps.payments.escrow import hold_funds, release_escrow, refund_escrow

    # On payment success:
    hold_funds(interaction_type='order', interaction_id=order.id,
               customer=user, business=biz, amount=total, payment=payment)

    # On verification event (OTP/check-in/completion):
    release_escrow('order', order.id, trigger='delivery_otp')

    # On cancellation/dispute resolution:
    refund_escrow('order', order.id, reason='Customer cancelled')
"""
from decimal import Decimal
from django.db import transaction
from django.utils import timezone

class EscrowTriggers:
    """Release trigger constants — no raw strings in views."""
    ORDER_DELIVERED       = 'delivery_otp'
    BOOKING_CHECKIN       = 'check_in'
    SERVICE_COMPLETED     = 'completion_otp'
    APPOINTMENT_CHECKIN   = 'check_in'
    RIDE_START            = 'ride_start'
    RIDE_COMPLETED        = 'ride_completed'
    SHIPMENT_DELIVERED    = 'delivery_otp'
    PASSENGER_BOARDED     = 'boarding'
    AUTO_RELEASE          = 'auto_release'
    ADMIN                 = 'manual'


def _get_commission_rate(business):
    """Business custom commission or platform default."""
    if business and business.custom_commission is not None:
        return Decimal(str(business.custom_commission))
    if business and business.commission_rate:
        return Decimal(str(business.commission_rate))
    return Decimal('10.00')  # platform default 10%


def hold_funds(interaction_type, interaction_id, customer, business,
               amount, payment=None, interaction_ref=None,
               auto_release_days=None):
    """
    Lock customer payment in escrow.
    Called after successful payment.
    """
    from .models import EscrowTransaction
    from apps.wallet.models import VendorWallet

    amount = Decimal(str(amount))
    rate = _get_commission_rate(business)
    commission = (amount * rate / 100).quantize(Decimal('0.01'))
    vendor_amount = amount - commission

    auto_release_at = None
    if auto_release_days:
        auto_release_at = timezone.now() + timezone.timedelta(days=auto_release_days)

    with transaction.atomic():
        escrow = EscrowTransaction.objects.create(
            interaction_type=interaction_type,
            interaction_id=interaction_id,
            interaction_ref=interaction_ref,
            customer=customer,
            business=business,
            amount=amount,
            commission_amount=commission,
            vendor_amount=vendor_amount,
            status='held',
            payment=payment,
            auto_release_at=auto_release_at,
        )

        # Credit vendor PENDING balance (locked)
        if business:
            wallet, _ = VendorWallet.objects.get_or_create(
                business=business,
                defaults={'user': business.owner},
            )
            wallet.pending_balance += vendor_amount
            wallet.save(update_fields=['pending_balance'])

    return escrow


def release_escrow(interaction_type, interaction_id, trigger='manual', notes=''):
    """
    Release held funds to vendor's available balance.
    Called by verification events (OTP verified, check-in, etc.)
    """
    from .models import EscrowTransaction
    from apps.wallet.models import VendorWallet, VendorTransaction

    with transaction.atomic():
        escrow = EscrowTransaction.objects.select_for_update().filter(
            interaction_type=interaction_type,
            interaction_id=interaction_id,
            status='held',
        ).first()

        if not escrow:
            return None  # nothing held / already released

        escrow.status = 'released'
        escrow.release_trigger = trigger
        escrow.released_at = timezone.now()
        if notes:
            escrow.notes = notes
        escrow.save()

        # Move vendor funds: pending → available
        if escrow.business:
            wallet = VendorWallet.objects.select_for_update().get(
                business=escrow.business
            )
            wallet.pending_balance   -= escrow.vendor_amount
            wallet.available_balance += escrow.vendor_amount
            wallet.total_earned      += escrow.vendor_amount
            wallet.save(update_fields=[
                'pending_balance', 'available_balance', 'total_earned'
            ])

            VendorTransaction.objects.create(
                vendor_wallet=wallet,
                transaction_type='credit',
                amount=escrow.vendor_amount,
                available_balance_after=wallet.available_balance,
                pending_balance_after=wallet.pending_balance,
                reference=escrow.reference,
                description=f'{escrow.interaction_type.title()} '
                            f'{escrow.interaction_ref or escrow.interaction_id} — '
                            f'released via {trigger}',
            )

    return escrow


def refund_escrow(interaction_type, interaction_id, reason=''):
    """
    Refund held funds to customer.
    Called on cancellation or dispute resolution in customer's favor.
    """
    from .models import EscrowTransaction
    from apps.wallet.models import VendorWallet, Wallet, WalletTransaction

    with transaction.atomic():
        escrow = EscrowTransaction.objects.select_for_update().filter(
            interaction_type=interaction_type,
            interaction_id=interaction_id,
            status='held',
        ).first()

        if not escrow:
            return None

        escrow.status = 'refunded'
        escrow.refunded_at = timezone.now()
        escrow.notes = reason
        escrow.save()

        # Remove from vendor pending
        if escrow.business:
            wallet = VendorWallet.objects.select_for_update().get(
                business=escrow.business
            )
            wallet.pending_balance -= escrow.vendor_amount
            wallet.total_refunded  += escrow.vendor_amount
            wallet.save(update_fields=['pending_balance', 'total_refunded'])

        # Credit customer wallet
        cust_wallet, _ = Wallet.objects.get_or_create(user=escrow.customer)
        cust_wallet.balance += escrow.amount
        cust_wallet.save(update_fields=['balance'])

        WalletTransaction.objects.create(
            wallet=cust_wallet,
            transaction_type='credit',
            amount=escrow.amount,
            balance_after=cust_wallet.balance,
            reference=escrow.reference,
            description=f'Refund — {escrow.interaction_type} '
                        f'{escrow.interaction_ref or escrow.interaction_id}: {reason}',
        )

    return escrow

def _log_transition(escrow, from_status, to_status, trigger=None, actor=None, ip=None, notes=''):
    from .models import EscrowLog
    EscrowLog.objects.create(
        escrow=escrow,
        from_status=from_status,
        to_status=to_status,
        trigger=trigger,
        actor=actor,
        ip_address=ip,
        notes=notes,
    )


def release_escrow_by_reference(reference, trigger='manual', actor=None, ip=None, notes=''):
    """Release using unique escrow reference — safest method."""
    from .models import EscrowTransaction
    escrow = EscrowTransaction.objects.filter(
        reference=reference, status='held'
    ).first()
    if not escrow:
        return None
    return _do_release(escrow, trigger, actor, ip, notes)


def open_dispute(interaction_type, interaction_id, actor=None, ip=None, reason=''):
    """Customer opens dispute — funds stay locked."""
    from .models import EscrowTransaction
    with transaction.atomic():
        escrow = EscrowTransaction.objects.select_for_update().filter(
            interaction_type=interaction_type,
            interaction_id=interaction_id,
            status='held',
        ).first()
        if not escrow:
            return None
        old = escrow.status
        escrow.status = 'disputed'
        escrow.notes = reason
        escrow.save()
        _log_transition(escrow, old, 'disputed', actor=actor, ip=ip, notes=reason)
    return escrow


def resolve_dispute(reference, resolution, actor=None, ip=None, notes=''):
    """
    Admin resolves dispute.
    resolution: 'release' (vendor wins) or 'refund' (customer wins)
    """
    from .models import EscrowTransaction
    escrow = EscrowTransaction.objects.filter(
        reference=reference, status='disputed'
    ).first()
    if not escrow:
        return None

    # Temporarily set back to held so release/refund logic works
    escrow.status = 'held'
    escrow.save()

    if resolution == 'release':
        return _do_release(escrow, EscrowTriggers.ADMIN, actor, ip, notes)
    else:
        return refund_escrow(escrow.interaction_type, escrow.interaction_id,
                            reason=notes or 'Dispute resolved in customer favor')

                            

def start_release_countdown(interaction_type, interaction_id, days=3):
    """
    Start the auto-release countdown from the SERVICE EVENT
    (package delivered, job marked complete), NOT the payment date.

    This is the FALLBACK for unresponsive customers:
      - Customer verifies (OTP/check-in) → release_escrow() fires immediately
      - Customer silent, no dispute      → auto-release after `days`
      - Customer opens dispute           → status='disputed', countdown ignored

    Usage:
        # Driver marks shipment delivered (GPS verified):
        start_release_countdown('shipment', shipment.id, days=3)

        # Provider marks job complete:
        start_release_countdown('service', sr.id, days=2)
    """
    from .models import EscrowTransaction

    escrow = EscrowTransaction.objects.filter(
        interaction_type=interaction_type,
        interaction_id=interaction_id,
        status='held',
    ).first()

    if escrow:
        escrow.auto_release_at = timezone.now() + timezone.timedelta(days=days)
        escrow.save(update_fields=['auto_release_at'])

    return escrow