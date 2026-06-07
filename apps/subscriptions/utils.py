from django.utils import timezone
from datetime import timedelta


def get_subscription_end_date(billing_cycle, trial_days=0):
    """Calculate subscription end date"""
    now = timezone.now()

    if trial_days > 0:
        return now + timedelta(days=trial_days)

    if billing_cycle == 'monthly':
        return now + timedelta(days=30)
    elif billing_cycle == 'yearly':
        return now + timedelta(days=365)
    elif billing_cycle == 'lifetime':
        return now + timedelta(days=365 * 100)

    return now + timedelta(days=30)


def check_subscription_limit(user, limit_type):
    """
    Check if user has reached their plan limits
    Returns True if within limits, False if exceeded
    """
    try:
        subscription = user.subscription
        if not subscription.is_active:
            return False

        plan = subscription.plan

        if limit_type == 'products':
            if plan.max_products == 0:
                return True  # unlimited
            from apps.products.models import Product
            count = Product.objects.filter(
                # filter by user if you have owner field
            ).count()
            return count < plan.max_products

        elif limit_type == 'orders':
            if plan.max_orders == 0:
                return True  # unlimited
            from apps.orders.models import Order
            count = Order.objects.filter(user=user).count()
            return count < plan.max_orders

        return True

    except Exception:
        return False