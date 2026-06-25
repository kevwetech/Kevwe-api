def handle_subscription_payment(
    reference, gateway, amount=None, gateway_response=None
):
    """
    Called by Paystack/Flutterwave webhooks
    when subscription payment is confirmed
    """
    from django.utils import timezone
    from datetime import timedelta
    from .models import (
        BusinessSubscriptionPayment,
        BusinessSubscriptionHistory,
        BusinessSubscription,
        BusinessPlan,
    )

    # Find pending payment by reference
    try:
        payment = BusinessSubscriptionPayment.objects.get(
            reference=reference,
            status='pending'
        )
    except BusinessSubscriptionPayment.DoesNotExist:
        # Try to find from gateway metadata
        if gateway_response:
            metadata = gateway_response.get('metadata', {})
            business_id = metadata.get('business_id')
            plan_id = metadata.get('plan_id')
            billing_cycle = metadata.get('billing_cycle', 'monthly')

            if business_id and plan_id:
                try:
                    from apps.marketplace.models import Business
                    business = Business.objects.get(pk=business_id)
                    plan = BusinessPlan.objects.get(pk=plan_id)

                    # Create subscription if not exists
                    now = timezone.now()
                    if billing_cycle == 'monthly':
                        end_date = now + timedelta(days=30)
                    else:
                        end_date = now + timedelta(days=365)

                    sub, _ = BusinessSubscription.objects.update_or_create(
                        business=business,
                        defaults={
                            'plan': plan,
                            'billing_cycle': billing_cycle,
                            'status': 'active',
                            'start_date': now,
                            'end_date': end_date,
                            'next_billing_date': end_date,
                            'last_renewed_at': now,
                            'amount_paid': amount or 0,
                            'payment_reference': reference,
                        }
                    )

                    # Create payment record
                    from apps.common.utils import generate_reference
                    payment = BusinessSubscriptionPayment.objects.create(
                        subscription=sub,
                        business=business,
                        plan=plan,
                        payment_type='new',
                        gateway=gateway,
                        billing_cycle=billing_cycle,
                        amount=amount or 0,
                        net_amount=amount or 0,
                        reference=reference,
                        gateway_reference=str(
                            gateway_response.get('id', '')
                        ),
                        gateway_response=gateway_response or {},
                        period_start=now,
                        period_end=end_date,
                        status='success',
                        paid_at=now,
                    )

                    # Record history
                    BusinessSubscriptionHistory.objects.create(
                        business=business,
                        plan=plan,
                        action='subscribed',
                        billing_cycle=billing_cycle,
                        amount=amount or 0,
                        payment_reference=reference,
                        notes=f'Auto-activated via {gateway} webhook',
                    )

                    # Notify
                    from apps.notifications.utils import send_notification
                    send_notification(
                        user=business.owner,
                        title=f'{plan.name} Subscription Active! ✅',
                        message=(
                            f'Your payment was confirmed. '
                            f'{plan.name} subscription is now '
                            f'active until {end_date.date()}.'
                        ),
                        notification_type='system',
                    )

                    return True, f'Subscription created and activated until {end_date.date()}'

                except Exception as e:
                    return False, f'Error creating subscription: {e}'

        return False, 'Payment not found or already processed'

    # Payment found — activate subscription
    payment.status = 'success'
    payment.paid_at = timezone.now()
    payment.gateway_reference = str(
        gateway_response.get('id', '')
    ) if gateway_response else ''
    payment.gateway_response = gateway_response or {}
    if amount:
        payment.net_amount = amount
    payment.save()

    sub     = payment.subscription
    business = payment.business
    plan    = payment.plan
    now     = timezone.now()

    # Calculate end date
    if sub.billing_cycle == 'monthly':
        end_date = now + timedelta(days=30)
    elif sub.billing_cycle == 'yearly':
        end_date = now + timedelta(days=365)
    else:
        end_date = now + timedelta(days=36500)

    # Determine action
    if sub.status == 'trial':
        action = 'trial_converted'
    elif sub.status in ['expired', 'grace_period', 'past_due']:
        action = 'renewed'
    else:
        action = 'subscribed'

    # Activate subscription
    sub.status            = 'active'
    sub.end_date          = end_date
    sub.grace_period_end  = None
    sub.next_billing_date = end_date
    sub.last_renewed_at   = now
    sub.amount_paid       = payment.amount
    sub.payment_reference = reference
    sub.suspension_reason = None
    sub.suspended_at      = None
    sub.suspended_by      = None
    sub.save()

    # Sync usage counters
    sub.sync_usage_counters()

    # Update payment period
    payment.period_start = now
    payment.period_end   = end_date
    payment.save()

    # Record history
    BusinessSubscriptionHistory.objects.create(
        business=business,
        plan=plan,
        action=action,
        billing_cycle=sub.billing_cycle,
        amount=payment.amount,
        payment_reference=reference,
        notes=f'Auto-activated via {gateway} webhook',
    )

    # Notify vendor
    from apps.notifications.utils import send_notification
    send_notification(
        user=business.owner,
        title=f'{plan.name} Subscription Active! ✅',
        message=(
            f'Your payment of ₦{payment.amount} was confirmed. '
            f'{plan.name} subscription is now active until '
            f'{end_date.date()}.'
        ),
        notification_type='system',
        data={
            'subscription_id': sub.id,
            'plan': plan.name,
            'end_date': str(end_date.date()),
        }
    )

    return True, f'Subscription activated until {end_date.date()}'


def handle_subscription_payment_failed(reference, reason=''):
    """Called when payment fails"""
    from .models import BusinessSubscriptionPayment
    from apps.notifications.utils import send_notification

    try:
        payment = BusinessSubscriptionPayment.objects.get(
            reference=reference,
            status='pending'
        )
    except BusinessSubscriptionPayment.DoesNotExist:
        return False, 'Payment not found'

    payment.status = 'failed'
    payment.notes  = reason
    payment.save()

    sub = payment.subscription
    if sub and sub.is_active:
        sub.status = 'past_due'
        sub.save()

    send_notification(
        user=payment.business.owner,
        title='Subscription Payment Failed ❌',
        message=(
            f'Your payment of ₦{payment.amount} for '
            f'{payment.plan.name} failed. '
            f'Reason: {reason}. '
            f'Please try again.'
        ),
        notification_type='system',
    )

    return True, 'Payment marked as failed'