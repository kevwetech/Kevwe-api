def generate_business_analytics(business, date=None):
    """Generate analytics snapshot for a business"""
    from .models import BusinessAnalytics
    from apps.orders.models import Order, OrderItem
    from apps.reviews.models import Review
    from django.utils import timezone
    from django.db.models import Sum, Count, Avg
    from collections import defaultdict

    if not date:
        date = timezone.now().date()

    # Get orders for this date
    orders = Order.objects.filter(
        business=business,
        created_at__date=date
    )

    total_orders = orders.count()
    completed = orders.filter(status='delivered').count()
    cancelled = orders.filter(status='cancelled').count()
    pending = orders.filter(
        status__in=['pending', 'confirmed', 'preparing']
    ).count()

    # Revenue
    completed_orders = orders.filter(status='delivered')
    gross_revenue = sum(
        o.subtotal for o in completed_orders
    )
    net_revenue = sum(
        o.business_earnings for o in completed_orders
    )
    delivery_revenue = sum(
        o.delivery_fee for o in completed_orders
    )
    platform_commission = sum(
        o.platform_commission for o in completed_orders
    )

    # Completion rate
    completion_rate = (
        (completed / total_orders * 100)
        if total_orders > 0 else 0
    )

    # Average order value
    avg_order_value = (
        gross_revenue / completed
        if completed > 0 else 0
    )

    # Customers
    customer_ids = orders.values_list(
        'user_id', flat=True
    ).distinct()
    total_customers = len(customer_ids)

    # New vs returning
    from apps.orders.models import Order as O
    new_customers = 0
    returning_customers = 0
    for customer_id in customer_ids:
        prev_orders = O.objects.filter(
            user_id=customer_id,
            business=business,
            created_at__date__lt=date
        ).exists()
        if prev_orders:
            returning_customers += 1
        else:
            new_customers += 1

    # Items sold
    items = OrderItem.objects.filter(
        order__in=completed_orders
    )
    total_items_sold = sum(i.quantity for i in items)

    # Top products
    product_sales = defaultdict(lambda: {
        'qty': 0, 'revenue': 0, 'name': ''
    })
    for item in items:
        if item.product:
            product_sales[item.product_id]['qty'] += item.quantity
            product_sales[item.product_id]['revenue'] += float(
                item.subtotal
            )
            product_sales[item.product_id]['name'] = item.product_name

    top_products = sorted(
        [
            {
                'product_id': k,
                'name': v['name'],
                'qty': v['qty'],
                'revenue': v['revenue']
            }
            for k, v in product_sales.items()
        ],
        key=lambda x: x['qty'],
        reverse=True
    )[:5]

    # Reviews
    reviews = Review.objects.filter(
        objects_type='business',
        objects_id=business.id,
        created_at__date=date
    )
    total_reviews = reviews.count()
    avg_rating = (
        sum(r.rating for r in reviews) / total_reviews
        if total_reviews > 0 else 0
    )

    # Save or update analytics
    analytics, created = BusinessAnalytics.objects.update_or_create(
        business=business,
        date=date,
        defaults={
            'total_orders': total_orders,
            'completed_orders': completed,
            'cancelled_orders': cancelled,
            'pending_orders': pending,
            'completion_rate': round(completion_rate, 2),
            'gross_revenue': gross_revenue,
            'net_revenue': net_revenue,
            'delivery_revenue': delivery_revenue,
            'platform_commission': platform_commission,
            'total_customers': total_customers,
            'new_customers': new_customers,
            'returning_customers': returning_customers,
            'total_items_sold': total_items_sold,
            'top_products': top_products,
            'avg_order_value': round(avg_order_value, 2),
            'avg_rating': round(avg_rating, 2),
            'total_reviews': total_reviews,
        }
    )
    return analytics


def generate_platform_analytics(date=None):
    """Generate platform-wide analytics"""
    from .models import PlatformAnalytics
    from apps.orders.models import Order
    from apps.marketplace.models import Business
    from apps.reviews.models import Review
    from apps.commissions.models import Commission
    from django.contrib.auth import get_user_model
    from django.utils import timezone

    User = get_user_model()

    if not date:
        date = timezone.now().date()

    # Businesses
    total_businesses = Business.objects.filter(
        status='active'
    ).count()
    new_businesses = Business.objects.filter(
        created_at__date=date
    ).count()
    active_businesses = Business.objects.filter(
        status='active',
        is_active=True
    ).count()

    # Users
    total_users = User.objects.count()
    new_users = User.objects.filter(created_at__date=date).count()
    
    total_vendors = User.objects.filter(
        role='vendor'
    ).count()
    total_drivers = User.objects.filter(
        role='driver'
    ).count()
    total_customers = User.objects.filter(
        role='customer'
    ).count()

    # Orders
    orders = Order.objects.filter(created_at__date=date)
    total_orders = orders.count()
    completed = orders.filter(status='delivered').count()
    cancelled = orders.filter(status='cancelled').count()

    # Revenue
    commissions = Commission.objects.filter(
        created_at__date=date
    )
    gross_volume = sum(
        c.gross_amount for c in commissions
    )
    platform_revenue = sum(
        c.platform_commission for c in commissions
    )
    vendor_payouts = sum(
        c.vendor_earnings for c in commissions
    )
    driver_payouts = sum(
        c.driver_earnings for c in commissions
    )

    # Reviews
    reviews = Review.objects.filter(created_at__date=date)
    total_reviews = reviews.count()
    avg_rating = (
        sum(r.rating for r in reviews) / total_reviews
        if total_reviews > 0 else 0
    )

    # Industry breakdown
    from apps.marketplace.models import Industry
    industry_breakdown = {}
    for industry in Industry.objects.filter(status='active'):
        industry_orders = orders.filter(
            business__industry=industry
        )
        industry_revenue = sum(
            o.subtotal for o in industry_orders.filter(
                status='delivered'
            )
        )
        industry_breakdown[industry.slug] = {
            'name': industry.name,
            'orders': industry_orders.count(),
            'revenue': float(industry_revenue),
        }

    analytics, _ = PlatformAnalytics.objects.update_or_create(
        date=date,
        defaults={
            'total_businesses': total_businesses,
            'new_businesses': new_businesses,
            'active_businesses': active_businesses,
            'total_users': total_users,
            'new_users': new_users,
            'active_users': new_users,
            'total_customers': total_customers,
            'total_vendors': total_vendors,
            'total_drivers': total_drivers,
            'total_orders': total_orders,
            'completed_orders': completed,
            'cancelled_orders': cancelled,
            'gross_volume': gross_volume,
            'platform_revenue': platform_revenue,
            'vendor_payouts': vendor_payouts,
            'driver_payouts': driver_payouts,
            'total_reviews': total_reviews,
            'avg_platform_rating': round(avg_rating, 2),
            'industry_breakdown': industry_breakdown,
        }
    )
    return analytics


def track_event(
    event_type,
    request=None,
    user=None,
    object_type=None,
    object_id=None,
    metadata=None
):
    """Track an analytics event"""
    from .models import AnalyticsEvent

    ip_address = None
    user_agent = None
    session_id = None

    if request:
        ip_address = request.META.get(
            'HTTP_X_FORWARDED_FOR',
            request.META.get('REMOTE_ADDR')
        )
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        session_id = request.session.session_key
        if not user and request.user.is_authenticated:
            user = request.user

    AnalyticsEvent.objects.create(
        user=user,
        event_type=event_type,
        object_type=object_type,
        object_id=object_id,
        session_id=session_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata=metadata or {},
    )