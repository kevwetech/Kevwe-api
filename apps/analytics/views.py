from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import timedelta, date
from apps.common.views import api_response
from apps.common.permissions import IsAdmin
from .models import (
    BusinessAnalytics,
    ProductAnalytics,
    PlatformAnalytics,
    CustomerAnalytics,
    AnalyticsEvent,
    SearchAnalytics,
    CategoryAnalytics,
    DriverAnalytics,
    VendorPerformance,
    SubscriptionAnalytics,
    PromotionAnalytics,
)
from .serializers import (
    BusinessAnalyticsSerializer,
    ProductAnalyticsSerializer,
    PlatformAnalyticsSerializer,
    CustomerAnalyticsSerializer,
    AnalyticsEventSerializer,
    SubscriptionAnalyticsSerializer,
    PromotionAnalyticsSerializer,
    VendorPerformanceSerializer,
    DriverAnalyticsSerializer,
    CategoryAnalyticsSerializer,
    SearchAnalyticsSerializer,
)


class BusinessAnalyticsView(APIView):
    """Business analytics dashboard"""
    permission_classes = [IsAuthenticated]

    def get(self, request, business_id):
        from apps.marketplace.models import Business
        try:
            business = Business.objects.get(pk=business_id)
        except Business.DoesNotExist:
            return api_response(
                'error', 'Business not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        # Check permission
        if (business.owner != request.user and
                request.user.role != 'admin'):
            return api_response(
                'error', 'Access denied',
                http_status=status.HTTP_403_FORBIDDEN
            )

        # Date range
        period = request.query_params.get('period', '7d')
        from_date = request.query_params.get('from_date')
        to_date = request.query_params.get('to_date')

        today = timezone.now().date()

        if from_date and to_date:
            start = date.fromisoformat(from_date)
            end = date.fromisoformat(to_date)
        elif period == '7d':
            start = today - timedelta(days=7)
            end = today
        elif period == '30d':
            start = today - timedelta(days=30)
            end = today
        elif period == '90d':
            start = today - timedelta(days=90)
            end = today
        elif period == 'today':
            start = today
            end = today
        else:
            start = today - timedelta(days=7)
            end = today

        # Generate today's analytics if not exists
        from .utils import generate_business_analytics
        generate_business_analytics(business, today)

        analytics = BusinessAnalytics.objects.filter(
            business=business,
            date__range=[start, end]
        ).order_by('date')

        # Aggregate totals
        total_orders = sum(a.total_orders for a in analytics)
        total_revenue = sum(a.gross_revenue for a in analytics)
        total_net = sum(a.net_revenue for a in analytics)
        total_customers = sum(a.total_customers for a in analytics)
        avg_rating = (
            sum(a.avg_rating for a in analytics if a.avg_rating > 0) /
            len([a for a in analytics if a.avg_rating > 0])
            if any(a.avg_rating > 0 for a in analytics) else 0
        )

        # Daily trend
        daily_data = BusinessAnalyticsSerializer(
            analytics, many=True
        ).data

        # Top products across period
        from collections import defaultdict
        product_totals = defaultdict(
            lambda: {'qty': 0, 'revenue': 0, 'name': ''}
        )
        for a in analytics:
            for p in a.top_products:
                pid = p.get('product_id')
                product_totals[pid]['qty'] += p.get('qty', 0)
                product_totals[pid]['revenue'] += p.get('revenue', 0)
                product_totals[pid]['name'] = p.get('name', '')

        top_products = sorted(
            [
                {
                    'product_id': k,
                    'name': v['name'],
                    'qty': v['qty'],
                    'revenue': v['revenue']
                }
                for k, v in product_totals.items()
            ],
            key=lambda x: x['qty'],
            reverse=True
        )[:5]

        return api_response(
            'success',
            'Business analytics retrieved successfully',
            data={
                'period': {
                    'from': str(start),
                    'to': str(end),
                    'days': (end - start).days + 1,
                },
                'summary': {
                    'total_orders': total_orders,
                    'total_revenue': str(total_revenue),
                    'net_revenue': str(total_net),
                    'total_customers': total_customers,
                    'avg_rating': round(avg_rating, 2),
                    'avg_order_value': str(
                        round(total_revenue / total_orders, 2)
                        if total_orders > 0 else 0
                    ),
                },
                'top_products': top_products,
                'daily': daily_data,
            }
        )

    def post(self, request, business_id):
        """Manually generate analytics for a date"""
        from apps.marketplace.models import Business
        try:
            business = Business.objects.get(pk=business_id)
        except Business.DoesNotExist:
            return api_response(
                'error', 'Business not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        date_str = request.data.get('date')
        target_date = None
        if date_str:
            target_date = date.fromisoformat(date_str)

        from .utils import generate_business_analytics
        analytics = generate_business_analytics(
            business, target_date
        )

        serializer = BusinessAnalyticsSerializer(analytics)
        return api_response(
            'success',
            'Analytics generated successfully',
            data=serializer.data,
            http_status=status.HTTP_201_CREATED
        )


class ProductAnalyticsView(APIView):
    """Product analytics"""
    permission_classes = [IsAuthenticated]

    def get(self, request, business_id, product_id):
        from apps.catalog.models import Product
        from apps.marketplace.models import Business

        try:
            business = Business.objects.get(pk=business_id)
            product = Product.objects.get(
                pk=product_id,
                business=business
            )
        except (Business.DoesNotExist, Product.DoesNotExist):
            return api_response(
                'error', 'Not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        period = request.query_params.get('period', '30d')
        today = timezone.now().date()

        if period == '7d':
            start = today - timedelta(days=7)
        elif period == '30d':
            start = today - timedelta(days=30)
        else:
            start = today - timedelta(days=30)

        analytics = ProductAnalytics.objects.filter(
            product=product,
            date__range=[start, today]
        ).order_by('date')

        total_sold = sum(a.units_sold for a in analytics)
        total_revenue = sum(a.revenue for a in analytics)
        total_views = sum(a.views for a in analytics)

        serializer = ProductAnalyticsSerializer(
            analytics, many=True
        )
        return api_response(
            'success',
            'Product analytics retrieved successfully',
            data={
                'product': {
                    'id': product.id,
                    'name': product.name,
                    'price': str(product.price),
                    'total_sold': product.total_sold,
                    'rating': str(product.rating),
                },
                'period_summary': {
                    'units_sold': total_sold,
                    'revenue': str(total_revenue),
                    'views': total_views,
                },
                'daily': serializer.data
            }
        )


class PlatformAnalyticsView(APIView):
    """Admin platform analytics"""
    permission_classes = [IsAdmin]

    def get(self, request):
        period = request.query_params.get('period', '30d')
        today = timezone.now().date()

        if period == '7d':
            start = today - timedelta(days=7)
        elif period == '30d':
            start = today - timedelta(days=30)
        elif period == '90d':
            start = today - timedelta(days=90)
        elif period == 'today':
            start = today
        else:
            start = today - timedelta(days=30)

        # Generate today's analytics
        from .utils import generate_platform_analytics
        generate_platform_analytics(today)

        analytics = PlatformAnalytics.objects.filter(
            date__range=[start, today]
        ).order_by('date')

        # Aggregates
        total_orders = sum(a.total_orders for a in analytics)
        total_volume = sum(a.gross_volume for a in analytics)
        total_revenue = sum(a.platform_revenue for a in analytics)
        total_users = analytics.last().total_users if analytics else 0
        new_users = sum(a.new_users for a in analytics)

        serializer = PlatformAnalyticsSerializer(
            analytics, many=True
        )
        return api_response(
            'success',
            'Platform analytics retrieved successfully',
            data={
                'period': {
                    'from': str(start),
                    'to': str(today),
                },
                'summary': {
                    'total_orders': total_orders,
                    'total_volume': str(total_volume),
                    'platform_revenue': str(total_revenue),
                    'total_users': total_users,
                    'new_users': new_users,
                },
                'daily': serializer.data,
            }
        )

    def post(self, request):
        """Generate platform analytics for a date"""
        date_str = request.data.get('date')
        target_date = None
        if date_str:
            target_date = date.fromisoformat(date_str)

        from .utils import generate_platform_analytics
        analytics = generate_platform_analytics(target_date)

        serializer = PlatformAnalyticsSerializer(analytics)
        return api_response(
            'success',
            'Platform analytics generated successfully',
            data=serializer.data,
            http_status=status.HTTP_201_CREATED
        )


class CustomerAnalyticsView(APIView):
    """Customer spending analytics"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.orders.models import Order

        period = request.query_params.get('period', '30d')
        today = timezone.now().date()

        if period == '7d':
            start = today - timedelta(days=7)
        elif period == '30d':
            start = today - timedelta(days=30)
        else:
            start = today - timedelta(days=30)

        orders = Order.objects.filter(
            user=request.user,
            created_at__date__range=[start, today]
        )

        total_orders = orders.count()
        completed = orders.filter(status='delivered')
        total_spent = sum(o.total for o in completed)
        avg_order = (
            total_spent / completed.count()
            if completed.count() > 0 else 0
        )

        # Favorite businesses
        from collections import Counter
        business_counts = Counter(
            orders.filter(
                business__isnull=False
            ).values_list('business__name', flat=True)
        )
        favorite_businesses = [
            {'name': name, 'orders': count}
            for name, count in business_counts.most_common(5)
        ]

        # Favorite products
        from apps.orders.models import OrderItem
        product_counts = Counter(
            OrderItem.objects.filter(
                order__in=orders
            ).values_list('product_name', flat=True)
        )
        favorite_products = [
            {'name': name, 'orders': count}
            for name, count in product_counts.most_common(5)
        ]

        return api_response(
            'success',
            'Customer analytics retrieved successfully',
            data={
                'period': {
                    'from': str(start),
                    'to': str(today),
                },
                'summary': {
                    'total_orders': total_orders,
                    'completed_orders': completed.count(),
                    'total_spent': str(total_spent),
                    'avg_order_value': str(round(avg_order, 2)),
                },
                'favorite_businesses': favorite_businesses,
                'favorite_products': favorite_products,
            }
        )


class TrackEventView(APIView):
    """Track analytics events from frontend"""
    permission_classes = []

    def post(self, request):
        event_type = request.data.get('event_type')
        object_type = request.data.get('object_type')
        object_id = request.data.get('object_id')
        metadata = request.data.get('metadata', {})

        if not event_type:
            return api_response(
                'error', 'event_type is required',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        from .utils import track_event
        track_event(
            event_type=event_type,
            request=request,
            object_type=object_type,
            object_id=object_id,
            metadata=metadata,
        )

        return api_response(
            'success',
            'Event tracked successfully'
        )


class QuickStatsView(APIView):
    """
    Quick stats for vendor dashboard
    Today's numbers at a glance
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, business_id):
        from apps.marketplace.models import Business
        from apps.orders.models import Order

        try:
            business = Business.objects.get(pk=business_id)
        except Business.DoesNotExist:
            return api_response(
                'error', 'Business not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        if (business.owner != request.user and
                request.user.role != 'admin'):
            return api_response(
                'error', 'Access denied',
                http_status=status.HTTP_403_FORBIDDEN
            )

        today = timezone.now().date()
        now = timezone.now()

        # Today's orders
        today_orders = Order.objects.filter(
            business=business,
            created_at__date=today
        )

        # This month
        month_start = today.replace(day=1)
        month_orders = Order.objects.filter(
            business=business,
            created_at__date__gte=month_start
        )

        # Active orders (need attention)
        active_orders = Order.objects.filter(
            business=business,
            status__in=[
                'pending', 'confirmed', 'preparing', 'ready'
            ]
        )

        return api_response(
            'success',
            'Quick stats retrieved successfully',
            data={
                'today': {
                    'orders': today_orders.count(),
                    'revenue': str(sum(
                        o.subtotal for o in
                        today_orders.filter(status='delivered')
                    )),
                    'completed': today_orders.filter(
                        status='delivered'
                    ).count(),
                    'cancelled': today_orders.filter(
                        status='cancelled'
                    ).count(),
                },
                'this_month': {
                    'orders': month_orders.count(),
                    'revenue': str(sum(
                        o.subtotal for o in
                        month_orders.filter(status='delivered')
                    )),
                    'customers': month_orders.values(
                        'user'
                    ).distinct().count(),
                },
                'active_orders': {
                    'total': active_orders.count(),
                    'pending': active_orders.filter(
                        status='pending'
                    ).count(),
                    'preparing': active_orders.filter(
                        status='preparing'
                    ).count(),
                    'ready': active_orders.filter(
                        status='ready'
                    ).count(),
                },
                'business': {
                    'rating': str(business.rating),
                    'total_orders': business.total_orders,
                    'total_revenue': str(business.total_revenue),
                    'is_open': business.is_open_now,
                }
            }
        )

class SearchAnalyticsView(APIView):
    """Track and view search analytics"""
    permission_classes = []

    def get_permissions(self):
        if self.request.method == 'GET':
            return [IsAdmin()]
        return []

    def get(self, request):
        """Admin view search analytics"""
        searches = SearchAnalytics.objects.all()

        from_date = request.query_params.get('from_date')
        to_date = request.query_params.get('to_date')
        business_id = request.query_params.get('business')

        if from_date:
            searches = searches.filter(date__gte=from_date)
        if to_date:
            searches = searches.filter(date__lte=to_date)
        if business_id:
            searches = searches.filter(business__id=business_id)

        # Top queries
        from collections import Counter
        query_counts = Counter(
            searches.values_list('query', flat=True)
        )
        top_queries = [
            {
                'query': q,
                'count': c,
                'conversion_rate': round(
                    searches.filter(
                        query=q,
                        converted=True
                    ).count() / c * 100,
                    1
                )
            }
            for q, c in query_counts.most_common(20)
        ]

        # Zero results queries
        zero_results = searches.filter(results_count=0)
        zero_queries = Counter(
            zero_results.values_list('query', flat=True)
        ).most_common(10)

        return api_response(
            'success',
            'Search analytics retrieved successfully',
            data={
                'total_searches': searches.count(),
                'total_conversions': searches.filter(
                    converted=True
                ).count(),
                'avg_results': round(
                    sum(s.results_count for s in searches) /
                    searches.count()
                    if searches.count() > 0 else 0,
                    1
                ),
                'top_queries': top_queries,
                'zero_result_queries': [
                    {'query': q, 'count': c}
                    for q, c in zero_queries
                ],
            }
        )

    def post(self, request):
        """Track a search"""
        from .models import SearchAnalytics
        from django.utils import timezone

        query = request.data.get('query', '').strip()
        results_count = request.data.get('results_count', 0)
        business_id = request.data.get('business_id')

        if not query:
            return api_response(
                'error', 'Query is required',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        from apps.marketplace.models import Business
        business = Business.objects.filter(
            pk=business_id
        ).first() if business_id else None

        ip = request.META.get(
            'HTTP_X_FORWARDED_FOR',
            request.META.get('REMOTE_ADDR')
        )

        SearchAnalytics.objects.create(
            user=request.user if request.user.is_authenticated else None,
            query=query,
            results_count=results_count,
            business=business,
            ip_address=ip,
            date=timezone.now().date(),
        )

        return api_response(
            'success',
            'Search tracked successfully'
        )


class CategoryAnalyticsView(APIView):
    """Category performance analytics"""
    permission_classes = [IsAuthenticated]

    def get(self, request, business_id):
        from apps.marketplace.models import Business
        try:
            business = Business.objects.get(pk=business_id)
        except Business.DoesNotExist:
            return api_response(
                'error', 'Business not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        if (business.owner != request.user and
                request.user.role != 'admin'):
            return api_response(
                'error', 'Access denied',
                http_status=status.HTTP_403_FORBIDDEN
            )

        period = request.query_params.get('period', '30d')
        today = timezone.now().date()

        if period == '7d':
            start = today - timedelta(days=7)
        elif period == '30d':
            start = today - timedelta(days=30)
        else:
            start = today - timedelta(days=30)

        analytics = CategoryAnalytics.objects.filter(
            business=business,
            date__range=[start, today]
        ).order_by('-revenue')

        serializer = CategoryAnalyticsSerializer(
            analytics, many=True
        )
        return api_response(
            'success',
            'Category analytics retrieved successfully',
            data={
                'count': analytics.count(),
                'results': serializer.data
            }
        )


class DriverAnalyticsView(APIView):
    """Driver performance analytics"""
    permission_classes = [IsAuthenticated]

    def get(self, request, driver_id=None):
        from apps.drivers.models import DriverProfile

        if driver_id:
            # Specific driver
            try:
                driver = DriverProfile.objects.get(pk=driver_id)
            except DriverProfile.DoesNotExist:
                return api_response(
                    'error', 'Driver not found',
                    http_status=status.HTTP_404_NOT_FOUND
                )

            # Check permission
            if (driver.user != request.user and
                    request.user.role != 'admin'):
                return api_response(
                    'error', 'Access denied',
                    http_status=status.HTTP_403_FORBIDDEN
                )
        else:
            # Current user's driver profile
            try:
                driver = request.user.driver_profile
            except Exception:
                return api_response(
                    'error', 'Driver profile not found',
                    http_status=status.HTTP_404_NOT_FOUND
                )

        period = request.query_params.get('period', '30d')
        today = timezone.now().date()

        if period == '7d':
            start = today - timedelta(days=7)
        elif period == '30d':
            start = today - timedelta(days=30)
        else:
            start = today - timedelta(days=30)

        analytics = DriverAnalytics.objects.filter(
            driver=driver,
            date__range=[start, today]
        ).order_by('date')

        # Totals
        total_earnings = sum(
            a.total_earnings for a in analytics
        )
        total_deliveries = sum(
            a.total_deliveries for a in analytics
        )
        total_rides = sum(a.total_rides for a in analytics)
        avg_rating = (
            sum(
                a.avg_rating for a in analytics
                if a.avg_rating > 0
            ) / len([
                a for a in analytics if a.avg_rating > 0
            ])
            if any(a.avg_rating > 0 for a in analytics)
            else 0
        )

        serializer = DriverAnalyticsSerializer(
            analytics, many=True
        )
        return api_response(
            'success',
            'Driver analytics retrieved successfully',
            data={
                'period_summary': {
                    'total_earnings': str(total_earnings),
                    'total_deliveries': total_deliveries,
                    'total_rides': total_rides,
                    'avg_rating': round(avg_rating, 2),
                },
                'daily': serializer.data
            }
        )


class VendorPerformanceView(APIView):
    """Vendor performance scores"""
    permission_classes = [IsAuthenticated]

    def get(self, request, business_id):
        from apps.marketplace.models import Business
        try:
            business = Business.objects.get(pk=business_id)
        except Business.DoesNotExist:
            return api_response(
                'error', 'Business not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        if (business.owner != request.user and
                request.user.role != 'admin'):
            return api_response(
                'error', 'Access denied',
                http_status=status.HTTP_403_FORBIDDEN
            )

        period = request.query_params.get('period', 'weekly')
        performances = VendorPerformance.objects.filter(
            business=business,
            period=period
        ).order_by('-period_start')[:12]

        serializer = VendorPerformanceSerializer(
            performances, many=True
        )
        return api_response(
            'success',
            'Vendor performance retrieved successfully',
            data={
                'current_tier': performances.first(
                ).performance_tier if performances else 'bronze',
                'current_score': str(
                    performances.first().overall_score
                ) if performances else '0',
                'count': performances.count(),
                'results': serializer.data
            }
        )

    def post(self, request, business_id):
        """Generate performance score"""
        from apps.marketplace.models import Business
        from apps.orders.models import Order
        from django.utils import timezone
        from datetime import timedelta

        try:
            business = Business.objects.get(pk=business_id)
        except Business.DoesNotExist:
            return api_response(
                'error', 'Business not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        period = request.data.get('period', 'weekly')
        today = timezone.now().date()

        if period == 'weekly':
            start = today - timedelta(days=7)
        else:
            start = today - timedelta(days=30)

        orders = Order.objects.filter(
            business=business,
            created_at__date__range=[start, today]
        )

        total = orders.count()
        completed = orders.filter(status='delivered').count()
        cancelled = orders.filter(status='cancelled').count()

        # Calculate scores
        completion_score = (
            (completed / total * 100)
            if total > 0 else 0
        )
        cancellation_score = max(
            0,
            100 - (cancelled / total * 100 * 3)
            if total > 0 else 100
        )
        rating_score = float(business.rating) * 20
        # 5★ = 100

        # Revenue
        revenue = sum(
            o.subtotal for o in orders.filter(
                status='delivered'
            )
        )
        avg_rating = float(business.rating)

        performance, created = VendorPerformance.objects.get_or_create(
            business=business,
            period=period,
            period_start=start,
            defaults={
                'period_end': today,
                'order_completion_score': round(
                    completion_score, 2
                ),
                'rating_score': round(rating_score, 2),
                'response_time_score': 80,  # default
                'cancellation_score': round(
                    cancellation_score, 2
                ),
                'preparation_time_score': 80,  # default
                'total_orders': total,
                'completed_orders': completed,
                'cancelled_orders': cancelled,
                'avg_rating': avg_rating,
                'total_revenue': revenue,
            }
        )

        performance.calculate_score()

        serializer = VendorPerformanceSerializer(performance)
        return api_response(
            'success',
            'Performance score generated successfully',
            data=serializer.data,
            http_status=status.HTTP_201_CREATED
        )


class SubscriptionAnalyticsView(APIView):
    """Subscription metrics"""
    permission_classes = [IsAdmin]

    def get(self, request):
        analytics = SubscriptionAnalytics.objects.all()

        from_date = request.query_params.get('from_date')
        to_date = request.query_params.get('to_date')

        if from_date:
            analytics = analytics.filter(date__gte=from_date)
        if to_date:
            analytics = analytics.filter(date__lte=to_date)

        latest = analytics.first()

        serializer = SubscriptionAnalyticsSerializer(
            analytics, many=True
        )
        return api_response(
            'success',
            'Subscription analytics retrieved successfully',
            data={
                'current': {
                    'mrr': str(latest.mrr) if latest else '0',
                    'arr': str(latest.arr) if latest else '0',
                    'total_subscribers': latest.total_subscribers if latest else 0,
                    'churn_rate': str(
                        latest.churn_rate
                    ) if latest else '0',
                },
                'count': analytics.count(),
                'results': serializer.data
            }
        )

    def post(self, request):
        """Generate subscription analytics"""
        from apps.subscriptions.models import Subscription, Plan
        from django.utils import timezone

        today = timezone.now().date()

        # Count subscribers
        active_subs = Subscription.objects.filter(
            status='active'
        )
        total = active_subs.count()

        # MRR
        mrr = sum(
            s.plan.price_monthly
            for s in active_subs
            if hasattr(s, 'plan') and s.plan
        )

        # Plan breakdown
        plan_breakdown = {}
        for plan in Plan.objects.filter(is_active=True):
            plan_breakdown[plan.name.lower()] = active_subs.filter(
                plan=plan
            ).count()

        analytics, _ = SubscriptionAnalytics.objects.update_or_create(
            date=today,
            defaults={
                'total_subscribers': total,
                'mrr': mrr,
                'arr': mrr * 12,
                'plan_breakdown': plan_breakdown,
            }
        )

        serializer = SubscriptionAnalyticsSerializer(analytics)
        return api_response(
            'success',
            'Subscription analytics generated',
            data=serializer.data,
            http_status=status.HTTP_201_CREATED
        )


class PromotionAnalyticsView(APIView):
    """Manage and track promotions"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role == 'admin':
            promotions = PromotionAnalytics.objects.all()
        else:
            # Vendors see their own promotions
            promotions = PromotionAnalytics.objects.filter(
                business__owner=request.user
            )

        is_active = request.query_params.get('active')
        promo_type = request.query_params.get('type')

        if is_active:
            promotions = promotions.filter(is_active=True)
        if promo_type:
            promotions = promotions.filter(
                promotion_type=promo_type
            )

        serializer = PromotionAnalyticsSerializer(
            promotions, many=True
        )
        return api_response(
            'success',
            'Promotions retrieved successfully',
            data={
                'count': promotions.count(),
                'active': promotions.filter(
                    is_active=True
                ).count(),
                'total_discount_given': str(sum(
                    p.total_discount_given for p in promotions
                )),
                'total_revenue_generated': str(sum(
                    p.total_revenue_generated for p in promotions
                )),
                'results': serializer.data
            }
        )

    def post(self, request):
        """Create a promotion"""
        serializer = PromotionAnalyticsSerializer(
            data=request.data
        )
        if serializer.is_valid():
            promotion = serializer.save(
                created_by=request.user
            )
            return api_response(
                'success',
                'Promotion created successfully',
                data=PromotionAnalyticsSerializer(
                    promotion
                ).data,
                http_status=status.HTTP_201_CREATED
            )
        return api_response(
            'error', 'Creation failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class PromotionDetailView(APIView):
    """Get update delete promotion"""
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        try:
            return PromotionAnalytics.objects.get(pk=pk)
        except PromotionAnalytics.DoesNotExist:
            return None

    def get(self, request, pk):
        promotion = self.get_object(pk)
        if not promotion:
            return api_response(
                'error', 'Promotion not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = PromotionAnalyticsSerializer(promotion)
        return api_response(
            'success',
            'Promotion retrieved successfully',
            data=serializer.data
        )

    def patch(self, request, pk):
        promotion = self.get_object(pk)
        if not promotion:
            return api_response(
                'error', 'Promotion not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = PromotionAnalyticsSerializer(
            promotion, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success',
                'Promotion updated successfully',
                data=serializer.data
            )
        return api_response(
            'error', 'Update failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )

    def delete(self, request, pk):
        promotion = self.get_object(pk)
        if not promotion:
            return api_response(
                'error', 'Promotion not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        promotion.is_active = False
        promotion.save()
        return api_response(
            'success', 'Promotion deactivated successfully'
        )