"""
Fraud detection scoring engine.
Scores are cumulative — multiple rules can fire on one event.

Score thresholds:
  0-30   → LOW      → log only
  31-60  → MEDIUM   → flag for admin review
  61-85  → HIGH     → flag + notify admin immediately
  86+    → CRITICAL → auto-block user + notify admin
"""
from django.utils import timezone
from datetime import timedelta


def get_risk_level(score):
    if score <= 30:
        return 'low'
    elif score <= 60:
        return 'medium'
    elif score <= 85:
        return 'high'
    return 'critical'


def create_alert(
    alert_type, title, description,
    risk_score, triggered_rules,
    user=None, metadata=None, ip_address=None
):
    """Create a FraudAlert and take appropriate action."""
    from .models import FraudAlert, BlockedEntity
    from apps.notifications.utils import send_notification
    from apps.common.utils import generate_reference

    risk_level = get_risk_level(risk_score)
    auto_blocked = False

    # Auto-block on CRITICAL
    if risk_level == 'critical' and user:
        try:
            BlockedEntity.objects.get_or_create(
                entity_type='user',
                value=str(user.id),
                defaults={
                    'reason': (
                        f'Auto-blocked: {title} '
                        f'(score: {risk_score})'
                    ),
                    'auto_blocked': True,
                    'is_active': True,
                }
            )
            # Deactivate user account
            user.is_active = False
            user.save()
            auto_blocked = True
            print(
                f"[FRAUD] Auto-blocked user {user.id} "
                f"— score {risk_score}"
            )
        except Exception as e:
            print(f"[FRAUD] Auto-block error: {e}")

    # Create alert
    alert = FraudAlert.objects.create(
        user=user,
        alert_type=alert_type,
        risk_level=risk_level,
        risk_score=risk_score,
        title=title,
        description=description,
        triggered_rules=triggered_rules,
        metadata=metadata or {},
        ip_address=ip_address,
        auto_blocked=auto_blocked,
    )

    # Notify admin for HIGH and CRITICAL
    if risk_level in ('high', 'critical'):
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            admins = User.objects.filter(
                is_staff=True, is_active=True
            )
            for admin in admins:
                send_notification(
                    user=admin,
                    title=f'🚨 Fraud Alert: {risk_level.upper()}',
                    message=(
                        f'{title} — Score: {risk_score}. '
                        f'User: {user.email if user else "Unknown"}'
                    ),
                    notification_type='system',
                    data={
                        'alert_id': alert.id,
                        'risk_level': risk_level,
                        'auto_blocked': auto_blocked,
                    }
                )
        except Exception as e:
            print(f"[FRAUD] Admin notification error: {e}")

    return alert


def score_payment(user, amount, reference, ip_address=None):
    """
    Score a payment transaction for fraud signals.
    Returns (score, triggered_rules).
    """
    from apps.payments.models import Payment

    score = 0
    triggered = []

    # Rule 1: Duplicate payment reference
    if Payment.objects.filter(reference=reference).exists():
        score += 40
        triggered.append('duplicate_payment_reference')

    # Rule 2: High velocity — 5+ payments in 1 hour
    one_hour_ago = timezone.now() - timedelta(hours=1)
    recent_payments = Payment.objects.filter(
        user=user,
        created_at__gte=one_hour_ago
    ).count()
    if recent_payments >= 5:
        score += 30
        triggered.append('high_payment_velocity')

    # Rule 3: Amount > 3x user's average order
    from apps.orders.models import Order
    from django.db.models import Avg
    avg = Order.objects.filter(
        user=user,
        payment_status='paid'
    ).aggregate(avg=Avg('total'))['avg']

    if avg and amount > (avg * 3):
        score += 20
        triggered.append('unusual_payment_amount')

    # Rule 4: New account (< 24hrs) making large payment
    account_age = timezone.now() - user.date_joined
    if account_age.total_seconds() < 86400 and amount > 50000:
        score += 25
        triggered.append('new_account_large_payment')

    return score, triggered


def score_account(user, ip_address=None):
    """
    Score account activity for fraud signals.
    Returns (score, triggered_rules).
    """
    score = 0
    triggered = []

    # Rule 1: Multiple failed logins in 10 minutes
    # (checks OTP attempts as a proxy)
    ten_mins_ago = timezone.now() - timedelta(minutes=10)
    try:
        from apps.authentication.models import OTP
        failed_otps = OTP.objects.filter(
            user=user,
            created_at__gte=ten_mins_ago,
            is_used=False
        ).count()
        if failed_otps >= 3:
            score += 30
            triggered.append('multiple_failed_logins')
    except Exception:
        pass

    # Rule 2: Multiple accounts with same phone
    if user.phone:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        same_phone = User.objects.filter(
            phone=user.phone
        ).exclude(id=user.id).count()
        if same_phone > 0:
            score += 30
            triggered.append('duplicate_phone_number')

    # Rule 3: Account < 24hrs placing orders
    account_age = timezone.now() - user.date_joined
    from apps.orders.models import Order
    has_orders = Order.objects.filter(user=user).exists()
    if account_age.total_seconds() < 86400 and has_orders:
        score += 20
        triggered.append('new_account_with_orders')

    return score, triggered


def score_order(user, order):
    """
    Score an order for fraud signals.
    Returns (score, triggered_rules).
    """
    score = 0
    triggered = []

    # Rule 1: 3+ refund requests in 30 days
    thirty_days_ago = timezone.now() - timedelta(days=30)
    from apps.orders.models import Order
    refund_count = Order.objects.filter(
        user=user,
        status='refunded',
        created_at__gte=thirty_days_ago
    ).count()
    if refund_count >= 3:
        score += 40
        triggered.append('high_refund_rate')

    # Rule 2: Order placed + cancelled 3x in 7 days
    seven_days_ago = timezone.now() - timedelta(days=7)
    cancelled_count = Order.objects.filter(
        user=user,
        status='cancelled',
        created_at__gte=seven_days_ago
    ).count()
    if cancelled_count >= 3:
        score += 20
        triggered.append('high_cancellation_rate')

    # Rule 3: High value order from new account
    account_age = timezone.now() - user.date_joined
    if (
        account_age.total_seconds() < 86400
        and order.total > 100000
    ):
        score += 25
        triggered.append('new_account_high_value_order')

    # Rule 4: Same address, multiple different users ordering
    if order.delivery_address:
        same_address_users = Order.objects.filter(
            delivery_address=order.delivery_address,
            created_at__gte=thirty_days_ago
        ).exclude(
            user=user
        ).values('user').distinct().count()
        if same_address_users >= 3:
            score += 15
            triggered.append('shared_delivery_address')

    return score, triggered


def evaluate_and_alert(
    alert_type, user, score,
    triggered_rules, context=None,
    ip_address=None
):
    """
    Evaluate total score and create alert if above LOW threshold.
    """
    if score <= 0:
        return None

    risk_level = get_risk_level(score)

    # Only create alerts for MEDIUM and above
    if risk_level == 'low':
        print(
            f"[FRAUD] LOW risk ({score}pts) for user "
            f"{user.id if user else 'unknown'} — logged only"
        )
        return None

    title_map = {
        'payment': 'Suspicious Payment Detected',
        'account': 'Suspicious Account Activity',
        'order': 'Suspicious Order Pattern',
    }

    return create_alert(
        alert_type=alert_type,
        title=title_map.get(alert_type, 'Fraud Alert'),
        description=(
            f'Risk score: {score}. '
            f'Triggered rules: {", ".join(triggered_rules)}'
        ),
        risk_score=score,
        triggered_rules=triggered_rules,
        user=user,
        metadata=context or {},
        ip_address=ip_address,
    )


def is_blocked(entity_type, value):
    """Check if an entity is currently blocked."""
    from .models import BlockedEntity
    try:
        entity = BlockedEntity.objects.get(
            entity_type=entity_type,
            value=str(value),
            is_active=True
        )
        return entity.is_valid()
    except BlockedEntity.DoesNotExist:
        return False

def track_velocity(user, event_type, ip_address=None):
    """
    Increment velocity counter for a user event.
    Returns the VelocityTracking object.
    """
    from .models import VelocityTracking
    tracking, _ = VelocityTracking.objects.get_or_create(
        user=user,
        event_type=event_type,
        defaults={'ip_address': ip_address}
    )
    tracking.increment(ip_address=ip_address)
    return tracking


def log_fraud_event(
    event_type, user=None, ip_address=None,
    user_agent=None, metadata=None,
    risk_score_added=0, alert=None
):
    """Log a raw fraud event."""
    from .models import FraudEvent
    return FraudEvent.objects.create(
        user=user,
        event_type=event_type,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata=metadata or {},
        risk_score_added=risk_score_added,
        alert=alert,
    )


def update_fraud_score(
    user, event_type, event_score,
    triggered_rules, event_reference='',
    metadata=None, ip_address=None
):
    """
    Create a per-event FraudScore and update
    the user's cumulative score.
    """
    from .models import FraudScore
    from .utils import get_risk_level

    # Get current cumulative score
    last_score = FraudScore.objects.filter(
        user=user
    ).order_by('-created_at').first()

    cumulative = (
        last_score.cumulative_score if last_score else 0
    ) + event_score

    return FraudScore.objects.create(
        user=user,
        event_type=event_type,
        event_score=event_score,
        triggered_rules=triggered_rules,
        event_reference=event_reference,
        metadata=metadata or {},
        ip_address=ip_address,
        cumulative_score=cumulative,
        risk_level=get_risk_level(cumulative),
    )


def log_action(
    action_type, reason,
    performed_by=None, target_user=None,
    alert=None, metadata=None,
    ip_address=None, is_system=False
):
    """Log a fraud action (admin or system)."""
    from .models import FraudActionLog
    return FraudActionLog.objects.create(
        action_type=action_type,
        performed_by=performed_by,
        target_user=target_user,
        alert=alert,
        is_system_action=is_system,
        reason=reason,
        metadata=metadata or {},
        ip_address=ip_address,
    )


def record_device(user, fingerprint_data):
    """
    Record or update a device fingerprint.
    Returns (fingerprint, is_new_device).
    """
    import hashlib
    import json
    from .models import DeviceFingerprint

    # Build hash from stable device attributes
    hash_input = json.dumps({
        'user_agent': fingerprint_data.get('user_agent', ''),
        'screen_resolution': fingerprint_data.get(
            'screen_resolution', ''
        ),
        'timezone': fingerprint_data.get('timezone', ''),
        'language': fingerprint_data.get('language', ''),
    }, sort_keys=True)

    fingerprint_hash = hashlib.sha256(
        hash_input.encode()
    ).hexdigest()

    fingerprint, created = DeviceFingerprint.objects.get_or_create(
        user=user,
        fingerprint_hash=fingerprint_hash,
        defaults={
            'ip_address': fingerprint_data.get('ip_address'),
            'user_agent': fingerprint_data.get('user_agent'),
            'browser': fingerprint_data.get('browser'),
            'os': fingerprint_data.get('os'),
            'device_type': fingerprint_data.get('device_type'),
            'screen_resolution': fingerprint_data.get(
                'screen_resolution'
            ),
            'timezone': fingerprint_data.get('timezone'),
            'language': fingerprint_data.get('language'),
            'country': fingerprint_data.get('country'),
            'city': fingerprint_data.get('city'),
        }
    )

    if not created:
        fingerprint.seen_count += 1
        fingerprint.ip_address = fingerprint_data.get(
            'ip_address', fingerprint.ip_address
        )
        fingerprint.save()

    return fingerprint, created


def is_whitelisted(entity_type, value):
    """Check if an entity is whitelisted."""
    from .models import Whitelist
    try:
        entry = Whitelist.objects.get(
            entity_type=entity_type,
            value=str(value),
            is_active=True
        )
        return entry.is_valid()
    except Whitelist.DoesNotExist:
        return False


def create_chargeback(
    user, amount, reason, description,
    chargeback_type='customer_dispute',
    order=None, payment_reference='',
    gateway='', gateway_chargeback_id=''
):
    """Create a chargeback record and fire a fraud alert."""
    from .models import Chargeback
    from apps.common.utils import generate_reference

    chargeback = Chargeback.objects.create(
        reference=generate_reference('CBK'),
        chargeback_type=chargeback_type,
        user=user,
        order=order,
        amount=amount,
        reason=reason,
        description=description,
        payment_reference=payment_reference,
        gateway=gateway,
        gateway_chargeback_id=gateway_chargeback_id,
    )

    # Auto-create a fraud alert for the chargeback
    alert = create_alert(
        alert_type='payment',
        title=f'Chargeback Filed — {reason}',
        description=(
            f'{"Customer dispute" if chargeback_type == "customer_dispute" else "Gateway chargeback"} '
            f'of ₦{amount} filed. Reason: {reason}'
        ),
        risk_score=50,
        triggered_rules=['chargeback_filed'],
        user=user,
        metadata={
            'chargeback_id': chargeback.id,
            'reference': chargeback.reference,
            'amount': str(amount),
            'order_id': order.id if order else None,
        }
    )

    chargeback.alert = alert
    chargeback.save()

    # Log the action
    log_action(
        action_type='chargeback_filed',
        reason=f'Chargeback filed: {reason}',
        target_user=user,
        alert=alert,
        is_system=True,
        metadata={'chargeback_reference': chargeback.reference}
    )

    return chargeback