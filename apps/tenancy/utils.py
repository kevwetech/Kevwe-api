from .models import UsageMetric
from django.utils import timezone
from datetime import timedelta


def create_audit_log(
    action,
    description,
    tenant=None,
    user=None,
    object_type=None,
    object_id=None,
    object_repr=None,
    changes=None,
    severity='info',
    metadata=None,
    request=None,
):
    """
    Helper function to create audit logs
    Call this from anywhere in the codebase
    """
    from .models import AuditLog

    ip_address = None
    user_agent = None
    endpoint = None

    if request:
        ip_address = request.META.get(
            'HTTP_X_FORWARDED_FOR',
            request.META.get('REMOTE_ADDR')
        )
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        endpoint = request.path

    AuditLog.objects.create(
        tenant=tenant,
        user=user,
        action=action,
        severity=severity,
        description=description,
        object_type=object_type,
        object_id=str(object_id) if object_id else None,
        object_repr=object_repr,
        changes=changes or {},
        ip_address=ip_address,
        user_agent=user_agent,
        endpoint=endpoint,
        metadata=metadata,
    )


def create_activity(
    tenant,
    title,
    activity_type='other',
    description=None,
    user=None,
    icon=None,
    color=None,
    object_type=None,
    object_id=None,
    object_url=None,
    metadata=None,
):
    """
    Helper to create activity feed entries
    """
    from .models import ActivityFeed

    ActivityFeed.objects.create(
        tenant=tenant,
        user=user,
        activity_type=activity_type,
        title=title,
        description=description,
        icon=icon,
        color=color,
        object_type=object_type,
        object_id=str(object_id) if object_id else None,
        object_url=object_url,
        metadata=metadata,
    )


def update_usage_metrics(tenant, date=None):
    """
    Calculate and update daily usage metrics
    for a tenant
    """

    if not date:
        date = timezone.now().date()

    import datetime

    period_start = timezone.make_aware(
        datetime.datetime.combine(date, datetime.time.min)
    )
    period_end = period_start + timedelta(days=1)

    # Get or create metric
    metric, _ = UsageMetric.objects.get_or_create(
        tenant=tenant,
        period='daily',
        date=date,
        defaults={
            'period_start': period_start,
            'period_end': period_end,
        }
    )

    # Calculate API calls
    from .models import APIUsage
    api_usage = APIUsage.objects.filter(
        tenant=tenant,
        date=date
    )
    metric.total_api_calls = api_usage.count()
    metric.successful_api_calls = api_usage.filter(
        status_code__lt=400
    ).count()
    metric.failed_api_calls = api_usage.filter(
        status_code__gte=400
    ).count()

    # Calculate business metrics
    from apps.orders.models import Order
    from apps.deliveries.models import DeliveryRequest
    from apps.shipments.models import Shipment
    from apps.rides.models import Ride
    from apps.payments.models import Payment

    metric.total_orders = Order.objects.filter(
        created_at__date=date
    ).count()
    metric.total_deliveries = DeliveryRequest.objects.filter(
        created_at__date=date
    ).count()
    metric.total_shipments = Shipment.objects.filter(
        created_at__date=date
    ).count()
    metric.total_rides = Ride.objects.filter(
        created_at__date=date
    ).count()

    # Revenue
    payments = Payment.objects.filter(
        created_at__date=date,
        status='success'
    )
    metric.total_revenue = sum(p.amount for p in payments)
    metric.total_payments = Payment.objects.filter(
        created_at__date=date
    ).count()
    metric.successful_payments = payments.count()
    metric.failed_payments = Payment.objects.filter(
        created_at__date=date,
        status='failed'
    ).count()

    metric.save()
    return metric