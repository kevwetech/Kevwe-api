from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from apps.common.views import api_response
from apps.common.permissions import IsAdmin
from apps.products.models import Product, Category
from apps.orders.models import Order
from apps.bookings.models import Booking
from apps.reviews.models import Review
from django.db.models import Sum, Count, Avg, Q
from apps.deliveries.models import CompanyEarnings

User = get_user_model()


def get_period_range(period):
    """
    Returns (start, end) datetime range for a given period.
    Supports: today, this_week, this_month, this_year
    """
    now = timezone.now()
    today = now.date()

    if period == 'today':
        start = now.replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        end = now
    elif period == 'this_week':
        start = now - timedelta(days=now.weekday())
        start = start.replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        end = now
    elif period == 'this_month':
        start = now.replace(
            day=1, hour=0, minute=0,
            second=0, microsecond=0
        )
        end = now
    elif period == 'this_year':
        start = now.replace(
            month=1, day=1, hour=0,
            minute=0, second=0, microsecond=0
        )
        end = now
    else:
        # Default to this_month
        start = now.replace(
            day=1, hour=0, minute=0,
            second=0, microsecond=0
        )
        end = now

    return start, end


def get_previous_period(period):
    """Returns (start, end) for the previous equivalent period."""
    now = timezone.now()

    if period == 'today':
        yesterday = now - timedelta(days=1)
        start = yesterday.replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        end = yesterday.replace(
            hour=23, minute=59, second=59, microsecond=0
        )
    elif period == 'this_week':
        start = now - timedelta(days=now.weekday() + 7)
        start = start.replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        end = start + timedelta(days=6)
        end = end.replace(hour=23, minute=59, second=59)
    elif period == 'this_month':
        first_this_month = now.replace(day=1)
        last_month_end = first_this_month - timedelta(days=1)
        start = last_month_end.replace(day=1)
        start = start.replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        end = last_month_end.replace(
            hour=23, minute=59, second=59
        )
    elif period == 'this_year':
        start = now.replace(
            year=now.year - 1, month=1, day=1,
            hour=0, minute=0, second=0, microsecond=0
        )
        end = now.replace(
            year=now.year - 1, month=12, day=31,
            hour=23, minute=59, second=59
        )
    else:
        start = now.replace(
            day=1, hour=0, minute=0,
            second=0, microsecond=0
        ) - timedelta(days=1)
        start = start.replace(day=1)
        end = now.replace(day=1) - timedelta(seconds=1)

    return start, end


def calc_growth(current, previous):
    """Calculate percentage growth vs previous period."""
    if not previous or previous == 0:
        return 100.0 if current > 0 else 0.0
    return round(((current - previous) / previous) * 100, 1)


# ── Super Admin Dashboard ─────────────────────────────────

class DashboardView(APIView):
    """
    GET - Full super admin dashboard
    GET /api/v1/dashboard/?period=today|this_week|this_month|this_year
    """
    permission_classes = [IsAdmin]

    def get(self, request):
        period = request.query_params.get(
            'period', 'this_month'
        )
        start, end = get_period_range(period)
        prev_start, prev_end = get_previous_period(period)
        today = timezone.now().date()

        # ── Users ────────────────────────────────────────
        total_users = User.objects.count()
        new_users = User.objects.filter(
            created_at__gte=start, created_at__lte=end
        ).count()
        prev_new_users = User.objects.filter(
            created_at__gte=prev_start,
            created_at__lte=prev_end
        ).count()
        active_users = User.objects.filter(
            is_active=True
        ).count()
        verified_users = User.objects.filter(
            is_verified=True
        ).count()

        # ── Businesses ───────────────────────────────────
        from apps.marketplace.models import Business
        total_businesses = Business.objects.count()
        verified_businesses = Business.objects.filter(
            is_verified=True
        ).count()
        new_businesses = Business.objects.filter(
            created_at__gte=start,
            created_at__lte=end
        ).count()

        # ── Orders ───────────────────────────────────────
        total_orders = Order.objects.count()
        period_orders = Order.objects.filter(
            created_at__gte=start,
            created_at__lte=end
        )
        prev_orders = Order.objects.filter(
            created_at__gte=prev_start,
            created_at__lte=prev_end
        ).count()
        orders_count = period_orders.count()

        # ── Revenue ───────────────────────────────────────
        total_revenue = Order.objects.filter(
            payment_status='paid'
        ).aggregate(t=Sum('total'))['t'] or 0

        period_revenue = Order.objects.filter(
            payment_status='paid',
            created_at__gte=start,
            created_at__lte=end
        ).aggregate(t=Sum('total'))['t'] or 0

        prev_revenue = Order.objects.filter(
            payment_status='paid',
            created_at__gte=prev_start,
            created_at__lte=prev_end
        ).aggregate(t=Sum('total'))['t'] or 0

        # ── Bookings ──────────────────────────────────────
        total_bookings = Booking.objects.count()
        period_bookings = Booking.objects.filter(
            created_at__gte=start,
            created_at__lte=end
        ).count()
        prev_bookings = Booking.objects.filter(
            created_at__gte=prev_start,
            created_at__lte=prev_end
        ).count()

        booking_revenue = Booking.objects.filter(
            payment_status='paid'
        ).aggregate(t=Sum('total'))['t'] or 0

        period_booking_revenue = Booking.objects.filter(
            payment_status='paid',
            created_at__gte=start,
            created_at__lte=end
        ).aggregate(t=Sum('total'))['t'] or 0

        prev_booking_revenue = Booking.objects.filter(
            payment_status='paid',
            created_at__gte=prev_start,
            created_at__lte=prev_end
        ).aggregate(t=Sum('total'))['t'] or 0

        # ── Deliveries ────────────────────────────────────
        delivery_revenue = CompanyEarnings.objects.filter(
            created_at__gte=start,
            created_at__lte=end
        ).aggregate(t=Sum('amount'))['t'] or 0

        # ── Platform total revenue ────────────────────────
        total_platform_revenue = (
            float(period_revenue)
            + float(period_booking_revenue)
            + float(delivery_revenue)
        )

        # ── Services ──────────────────────────────────────
        try:
            from apps.services.models import (
                ServiceRequest, ServiceProvider
            )
            period_service_requests = (
                ServiceRequest.objects.filter(
                    created_at__gte=start,
                    created_at__lte=end
                ).count()
            )
            service_revenue = (
                ServiceRequest.objects.filter(
                    status='completed',
                    created_at__gte=start,
                    created_at__lte=end
                ).aggregate(
                    t=Sum('platform_commission')
                )['t'] or 0
            )
            total_providers = ServiceProvider.objects.count()
            verified_providers = ServiceProvider.objects.filter(
                status='verified'
            ).count()
        except Exception:
            period_service_requests = 0
            service_revenue = 0
            total_providers = 0
            verified_providers = 0

        # ── KYC ───────────────────────────────────────────
        try:
            from apps.kyc.models import KYCProfile
            pending_kyc = KYCProfile.objects.filter(
                status='pending'
            ).count()
            approved_kyc = KYCProfile.objects.filter(
                status__in=['approved', 'auto_approved']
            ).count()
        except Exception:
            pending_kyc = 0
            approved_kyc = 0

        # ── Fraud ─────────────────────────────────────────
        try:
            from apps.fraud.models import FraudAlert
            open_alerts = FraudAlert.objects.filter(
                status='open'
            ).count()
            critical_alerts = FraudAlert.objects.filter(
                status='open',
                risk_level='critical'
            ).count()
        except Exception:
            open_alerts = 0
            critical_alerts = 0

        # ── Wallet ────────────────────────────────────────
        try:
            from apps.wallet.models import (
                VendorWallet, WithdrawalRequest
            )
            total_vendor_pending = VendorWallet.objects.aggregate(
                t=Sum('pending_balance')
            )['t'] or 0
            total_vendor_available = VendorWallet.objects.aggregate(
                t=Sum('available_balance')
            )['t'] or 0
            pending_withdrawals = WithdrawalRequest.objects.filter(
                status='pending'
            ).count()
        except Exception:
            total_vendor_pending = 0
            total_vendor_available = 0
            pending_withdrawals = 0

        # ── Reviews ───────────────────────────────────────
        total_reviews = Review.objects.count()
        avg_rating = Review.objects.aggregate(
            avg=Avg('rating')
        )['avg'] or 0

        # ── Staff ─────────────────────────────────────────
        try:
            from apps.staff.models import BusinessMember
            total_staff = BusinessMember.objects.filter(
                status='active'
            ).count()
        except Exception:
            total_staff = 0

        # ── Recent activity ───────────────────────────────
        recent_orders = Order.objects.order_by(
            '-created_at'
        ).values(
            'id', 'order_number', 'status',
            'payment_status', 'total', 'created_at'
        )[:5]

        recent_bookings = Booking.objects.order_by(
            '-created_at'
        ).values(
            'id', 'booking_number', 'guest_name',
            'status', 'total', 'check_in', 'created_at'
        )[:5]

        recent_users = User.objects.order_by(
            '-created_at'
        ).values(
            'id', 'full_name', 'email',
            'is_verified', 'created_at'
        )[:5]

        # ── Top businesses ────────────────────────────────
        top_businesses = Business.objects.annotate(
            order_count=Count('orders'),
            booking_count=Count('bookings'),
        ).order_by('-order_count')[:5].values(
            'id', 'name', 'order_count', 'booking_count'
        )

        return api_response(
            'success',
            'Super admin dashboard retrieved',
            data={
                'period': period,
                'period_range': {
                    'start': start,
                    'end': end,
                },
                'users': {
                    'total': total_users,
                    'active': active_users,
                    'verified': verified_users,
                    'new_this_period': new_users,
                    'growth': calc_growth(
                        new_users, prev_new_users
                    ),
                },
                'businesses': {
                    'total': total_businesses,
                    'verified': verified_businesses,
                    'new_this_period': new_businesses,
                },
                'orders': {
                    'total': total_orders,
                    'this_period': orders_count,
                    'growth': calc_growth(
                        orders_count, prev_orders
                    ),
                    'pending': Order.objects.filter(
                        status='pending'
                    ).count(),
                    'delivered': Order.objects.filter(
                        status='delivered'
                    ).count(),
                    'cancelled': Order.objects.filter(
                        status='cancelled'
                    ).count(),
                },
                'bookings': {
                    'total': total_bookings,
                    'this_period': period_bookings,
                    'growth': calc_growth(
                        period_bookings, prev_bookings
                    ),
                    'pending': Booking.objects.filter(
                        status='pending'
                    ).count(),
                    'checked_in': Booking.objects.filter(
                        status='checked_in'
                    ).count(),
                    'cancelled': Booking.objects.filter(
                        status='cancelled'
                    ).count(),
                },
                'services': {
                    'requests_this_period': (
                        period_service_requests
                    ),
                    'total_providers': total_providers,
                    'verified_providers': verified_providers,
                    'commission_this_period': str(
                        service_revenue
                    ),
                },
                'revenue': {
                    'platform_total_this_period': str(
                        round(total_platform_revenue, 2)
                    ),
                    'orders': {
                        'total': str(total_revenue),
                        'this_period': str(period_revenue),
                        'growth': calc_growth(
                            float(period_revenue),
                            float(prev_revenue)
                        ),
                    },
                    'bookings': {
                        'total': str(booking_revenue),
                        'this_period': str(
                            period_booking_revenue
                        ),
                        'growth': calc_growth(
                            float(period_booking_revenue),
                            float(prev_booking_revenue)
                        ),
                    },
                    'deliveries': {
                        'this_period': str(delivery_revenue),
                    },
                    'services': {
                        'this_period': str(service_revenue),
                    },
                },
                'wallet': {
                    'total_vendor_pending': str(
                        total_vendor_pending
                    ),
                    'total_vendor_available': str(
                        total_vendor_available
                    ),
                    'pending_withdrawal_requests': (
                        pending_withdrawals
                    ),
                },
                'kyc': {
                    'pending': pending_kyc,
                    'approved': approved_kyc,
                },
                'fraud': {
                    'open_alerts': open_alerts,
                    'critical_alerts': critical_alerts,
                },
                'reviews': {
                    'total': total_reviews,
                    'average_rating': round(avg_rating, 1),
                },
                'staff': {
                    'total_active': total_staff,
                },
                'recent_orders': list(recent_orders),
                'recent_bookings': list(recent_bookings),
                'recent_users': list(recent_users),
                'top_businesses': list(top_businesses),
            }
        )


# ── Admin section endpoints ───────────────────────────────

class AdminRevenueView(APIView):
    """
    GET - Revenue breakdown by period (admin)
    GET /api/v1/dashboard/admin/revenue/?period=this_month
    """
    permission_classes = [IsAdmin]

    def get(self, request):
        period = request.query_params.get(
            'period', 'this_month'
        )
        start, end = get_period_range(period)

        # Daily breakdown
        from django.db.models.functions import TruncDate
        order_daily = Order.objects.filter(
            payment_status='paid',
            created_at__gte=start,
            created_at__lte=end
        ).annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(
            revenue=Sum('total'),
            count=Count('id')
        ).order_by('date')

        booking_daily = Booking.objects.filter(
            payment_status='paid',
            created_at__gte=start,
            created_at__lte=end
        ).annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(
            revenue=Sum('total'),
            count=Count('id')
        ).order_by('date')

        return api_response(
            'success', 'Revenue data retrieved',
            data={
                'period': period,
                'orders': list(order_daily),
                'bookings': list(booking_daily),
            }
        )


class AdminUserListView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        users = User.objects.all()
        search = request.query_params.get('search')
        role = request.query_params.get('role')
        is_verified = request.query_params.get('is_verified')

        if search:
            users = users.filter(
                Q(email__icontains=search) |
                Q(full_name__icontains=search) |
                Q(phone__icontains=search)
            )
        if role:
            users = users.filter(role=role)
        if is_verified:
            users = users.filter(
                is_verified=is_verified == 'true'
            )

        return api_response(
            'success', 'Users retrieved',
            data={
                'count': users.count(),
                'results': [
                    {
                        'id': u.id,
                        'full_name': u.full_name,
                        'email': u.email,
                        'phone': u.phone,
                        'role': u.role,
                        'is_verified': u.is_verified,
                        'is_active': u.is_active,
                        'created_at': u.created_at,
                    }
                    for u in users[:50]
                ]
            }
        )


class AdminUserDetailView(APIView):
    permission_classes = [IsAdmin]

    def get_object(self, pk):
        try:
            return User.objects.get(pk=pk)
        except User.DoesNotExist:
            return None

    def get(self, request, pk):
        user = self.get_object(pk)
        if not user:
            return api_response(
                'error', 'User not found',
                http_status=404
            )

        orders = Order.objects.filter(user=user)
        bookings = Booking.objects.filter(user=user)

        return api_response(
            'success', 'User detail retrieved',
            data={
                'id': user.id,
                'full_name': user.full_name,
                'email': user.email,
                'phone': user.phone,
                'role': user.role,
                'is_verified': user.is_verified,
                'is_active': user.is_active,
                'created_at': user.created_at,
                'stats': {
                    'total_orders': orders.count(),
                    'total_bookings': bookings.count(),
                    'total_spent': str(
                        orders.filter(
                            payment_status='paid'
                        ).aggregate(
                            t=Sum('total')
                        )['t'] or 0
                    ),
                }
            }
        )

    def patch(self, request, pk):
        user = self.get_object(pk)
        if not user:
            return api_response(
                'error', 'User not found',
                http_status=404
            )
        if 'is_active' in request.data:
            user.is_active = request.data['is_active']
        if 'is_verified' in request.data:
            user.is_verified = request.data['is_verified']
        user.save()
        return api_response(
            'success', 'User updated',
            data={'id': user.id, 'is_active': user.is_active}
        )

    def delete(self, request, pk):
        user = self.get_object(pk)
        if not user:
            return api_response(
                'error', 'User not found',
                http_status=404
            )
        user.is_active = False
        user.save()
        return api_response('success', 'User deactivated')


# ── Business Owner Dashboard ──────────────────────────────

class BusinessDashboardView(APIView):
    """
    GET - Unified business owner dashboard
    GET /api/v1/dashboard/business/<business_id>/?period=this_month
    Returns all sections in one call.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, business_id):
        from apps.marketplace.models import Business

        try:
            business = Business.objects.get(
                pk=business_id, owner=request.user
            )
        except Business.DoesNotExist:
            return api_response(
                'error', 'Business not found',
                http_status=403
            )

        period = request.query_params.get(
            'period', 'this_month'
        )
        start, end = get_period_range(period)
        prev_start, prev_end = get_previous_period(period)

        # ── Orders ────────────────────────────────────────
        orders = Order.objects.filter(business=business)
        period_orders = orders.filter(
            created_at__gte=start, created_at__lte=end
        )
        prev_period_orders = orders.filter(
            created_at__gte=prev_start,
            created_at__lte=prev_end
        )
        order_revenue = period_orders.filter(
            payment_status='paid'
        ).aggregate(t=Sum('total'))['t'] or 0
        prev_order_revenue = prev_period_orders.filter(
            payment_status='paid'
        ).aggregate(t=Sum('total'))['t'] or 0

        # ── Bookings ──────────────────────────────────────
        bookings = Booking.objects.filter(business=business)
        period_bookings = bookings.filter(
            created_at__gte=start, created_at__lte=end
        )
        prev_period_bookings = bookings.filter(
            created_at__gte=prev_start,
            created_at__lte=prev_end
        )
        booking_revenue = period_bookings.filter(
            payment_status='paid'
        ).aggregate(t=Sum('total'))['t'] or 0
        prev_booking_revenue = prev_period_bookings.filter(
            payment_status='paid'
        ).aggregate(t=Sum('total'))['t'] or 0

        # ── Combined revenue ──────────────────────────────
        total_revenue = (
            float(order_revenue) + float(booking_revenue)
        )
        prev_total_revenue = (
            float(prev_order_revenue)
            + float(prev_booking_revenue)
        )

        # ── Wallet ────────────────────────────────────────
        try:
            from apps.wallet.models import VendorWallet
            wallet = VendorWallet.objects.filter(
                business=business
            ).first()
            available_balance = (
                float(wallet.available_balance) if wallet else 0
            )
            pending_balance = (
                float(wallet.pending_balance) if wallet else 0
            )
        except Exception:
            available_balance = 0
            pending_balance = 0

        # ── Reviews ───────────────────────────────────────
        from django.contrib.contenttypes.models import ContentType
        biz_ct = ContentType.objects.get_for_model(business)
        reviews = Review.objects.filter(
            objects_type=biz_ct,
            objects_id=business.id
        )
        avg_rating = reviews.aggregate(
            avg=Avg('rating')
        )['avg'] or 0

        # ── Customers ─────────────────────────────────────
        order_customers = orders.values(
            'user'
        ).distinct().count()
        booking_customers = bookings.values(
            'user'
        ).distinct().count()

        # ── Staff ─────────────────────────────────────────
        try:
            from apps.staff.models import BusinessMember
            total_staff = BusinessMember.objects.filter(
                business=business, status='active'
            ).count()
        except Exception:
            total_staff = 0

        # ── Services ──────────────────────────────────────
        try:
            from apps.services.models import ServiceRequest
            service_requests = ServiceRequest.objects.filter(
                provider__business=business
            )
            period_service_revenue = service_requests.filter(
                status='completed',
                created_at__gte=start,
                created_at__lte=end
            ).aggregate(
                t=Sum('provider_earnings')
            )['t'] or 0
        except Exception:
            service_requests = None
            period_service_revenue = 0

        # ── Recent activity ───────────────────────────────
        recent_orders = orders.order_by(
            '-created_at'
        ).values(
            'id', 'order_number', 'status',
            'payment_status', 'total', 'created_at'
        )[:5]

        recent_bookings = bookings.order_by(
            '-created_at'
        ).values(
            'id', 'booking_number', 'guest_name',
            'status', 'total', 'check_in', 'created_at'
        )[:5]

        # ── KYC status ────────────────────────────────────
        try:
            from apps.kyc.models import BusinessKYC
            biz_kyc = BusinessKYC.objects.filter(
                business=business
            ).first()
            kyc_status = biz_kyc.status if biz_kyc else 'not_started'
        except Exception:
            kyc_status = 'not_started'

        return api_response(
            'success',
            'Business dashboard retrieved',
            data={
                'business': {
                    'id': business.id,
                    'name': business.name,
                    'is_verified': business.is_verified,
                    'kyc_status': kyc_status,
                },
                'period': period,
                'period_range': {
                    'start': start,
                    'end': end,
                },
                'revenue': {
                    'total_this_period': str(
                        round(total_revenue, 2)
                    ),
                    'growth': calc_growth(
                        total_revenue, prev_total_revenue
                    ),
                    'orders': str(order_revenue),
                    'bookings': str(booking_revenue),
                    'services': str(period_service_revenue),
                },
                'orders': {
                    'total': orders.count(),
                    'this_period': period_orders.count(),
                    'growth': calc_growth(
                        period_orders.count(),
                        prev_period_orders.count()
                    ),
                    'pending': orders.filter(
                        status='pending'
                    ).count(),
                    'delivered': orders.filter(
                        status='delivered'
                    ).count(),
                    'cancelled': orders.filter(
                        status='cancelled'
                    ).count(),
                },
                'bookings': {
                    'total': bookings.count(),
                    'this_period': period_bookings.count(),
                    'growth': calc_growth(
                        period_bookings.count(),
                        prev_period_bookings.count()
                    ),
                    'pending': bookings.filter(
                        status='pending'
                    ).count(),
                    'checked_in': bookings.filter(
                        status='checked_in'
                    ).count(),
                    'cancelled': bookings.filter(
                        status='cancelled'
                    ).count(),
                    'upcoming': bookings.filter(
                        check_in__gte=timezone.now().date(),
                        status__in=['pending', 'confirmed']
                    ).count(),
                },
                'wallet': {
                    'available_balance': str(
                        available_balance
                    ),
                    'pending_balance': str(pending_balance),
                },
                'customers': {
                    'from_orders': order_customers,
                    'from_bookings': booking_customers,
                },
                'reviews': {
                    'total': reviews.count(),
                    'average_rating': round(avg_rating, 1),
                },
                'staff': {
                    'total_active': total_staff,
                },
                'recent_orders': list(recent_orders),
                'recent_bookings': list(recent_bookings),
            }
        )


# ── Business section endpoints ────────────────────────────

class BusinessOrdersSectionView(APIView):
    """
    GET - Orders section for business dashboard
    GET /api/v1/dashboard/business/<business_id>/orders/?period=this_month
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, business_id):
        from apps.marketplace.models import Business
        from django.db.models.functions import TruncDate

        try:
            business = Business.objects.get(
                pk=business_id, owner=request.user
            )
        except Business.DoesNotExist:
            return api_response(
                'error', 'Business not found',
                http_status=403
            )

        period = request.query_params.get(
            'period', 'this_month'
        )
        start, end = get_period_range(period)

        orders = Order.objects.filter(
            business=business,
            created_at__gte=start,
            created_at__lte=end
        )

        # Daily breakdown
        daily = orders.filter(
            payment_status='paid'
        ).annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(
            revenue=Sum('total'),
            count=Count('id')
        ).order_by('date')

        # By status
        by_status = orders.values('status').annotate(
            count=Count('id')
        )

        return api_response(
            'success', 'Orders section retrieved',
            data={
                'period': period,
                'total': orders.count(),
                'revenue': str(
                    orders.filter(
                        payment_status='paid'
                    ).aggregate(t=Sum('total'))['t'] or 0
                ),
                'by_status': list(by_status),
                'daily_breakdown': list(daily),
                'recent': list(
                    orders.order_by('-created_at').values(
                        'id', 'order_number', 'status',
                        'total', 'created_at'
                    )[:10]
                ),
            }
        )


class BusinessBookingsSectionView(APIView):
    """
    GET - Bookings section for business dashboard
    GET /api/v1/dashboard/business/<business_id>/bookings/?period=this_month
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, business_id):
        from apps.marketplace.models import Business
        from django.db.models.functions import TruncDate

        try:
            business = Business.objects.get(
                pk=business_id, owner=request.user
            )
        except Business.DoesNotExist:
            return api_response(
                'error', 'Business not found',
                http_status=403
            )

        period = request.query_params.get(
            'period', 'this_month'
        )
        start, end = get_period_range(period)

        bookings = Booking.objects.filter(
            business=business,
            created_at__gte=start,
            created_at__lte=end
        )

        today = timezone.now().date()
        upcoming = Booking.objects.filter(
            business=business,
            check_in__gte=today,
            status__in=['pending', 'confirmed']
        ).order_by('check_in').values(
            'id', 'booking_number', 'guest_name',
            'check_in', 'check_out', 'status', 'total'
        )[:10]

        daily = bookings.filter(
            payment_status='paid'
        ).annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(
            revenue=Sum('total'),
            count=Count('id')
        ).order_by('date')

        return api_response(
            'success', 'Bookings section retrieved',
            data={
                'period': period,
                'total': bookings.count(),
                'revenue': str(
                    bookings.filter(
                        payment_status='paid'
                    ).aggregate(t=Sum('total'))['t'] or 0
                ),
                'pending': bookings.filter(
                    status='pending'
                ).count(),
                'confirmed': bookings.filter(
                    status='confirmed'
                ).count(),
                'checked_in': bookings.filter(
                    status='checked_in'
                ).count(),
                'cancelled': bookings.filter(
                    status='cancelled'
                ).count(),
                'daily_breakdown': list(daily),
                'upcoming': list(upcoming),
            }
        )


class BusinessRevenueSectionView(APIView):
    """
    GET - Revenue analytics section for business dashboard
    GET /api/v1/dashboard/business/<business_id>/revenue/?period=this_month
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, business_id):
        from apps.marketplace.models import Business
        from django.db.models.functions import TruncDate, TruncMonth

        try:
            business = Business.objects.get(
                pk=business_id, owner=request.user
            )
        except Business.DoesNotExist:
            return api_response(
                'error', 'Business not found',
                http_status=403
            )

        period = request.query_params.get(
            'period', 'this_month'
        )
        start, end = get_period_range(period)
        prev_start, prev_end = get_previous_period(period)

        # Order revenue
        order_rev = Order.objects.filter(
            business=business,
            payment_status='paid',
            created_at__gte=start,
            created_at__lte=end
        ).aggregate(t=Sum('total'))['t'] or 0

        prev_order_rev = Order.objects.filter(
            business=business,
            payment_status='paid',
            created_at__gte=prev_start,
            created_at__lte=prev_end
        ).aggregate(t=Sum('total'))['t'] or 0

        # Booking revenue
        booking_rev = Booking.objects.filter(
            business=business,
            payment_status='paid',
            created_at__gte=start,
            created_at__lte=end
        ).aggregate(t=Sum('total'))['t'] or 0

        prev_booking_rev = Booking.objects.filter(
            business=business,
            payment_status='paid',
            created_at__gte=prev_start,
            created_at__lte=prev_end
        ).aggregate(t=Sum('total'))['t'] or 0

        # Commission paid to platform
        order_commission = Order.objects.filter(
            business=business,
            payment_status='paid',
            created_at__gte=start,
            created_at__lte=end
        ).aggregate(
            t=Sum('platform_commission')
        )['t'] or 0

        # Daily revenue chart
        daily = Order.objects.filter(
            business=business,
            payment_status='paid',
            created_at__gte=start,
            created_at__lte=end
        ).annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(
            revenue=Sum('total')
        ).order_by('date')

        total = float(order_rev) + float(booking_rev)
        prev_total = (
            float(prev_order_rev) + float(prev_booking_rev)
        )

        return api_response(
            'success', 'Revenue section retrieved',
            data={
                'period': period,
                'total_revenue': str(round(total, 2)),
                'growth': calc_growth(total, prev_total),
                'breakdown': {
                    'orders': str(order_rev),
                    'bookings': str(booking_rev),
                    'commission_paid': str(order_commission),
                    'net_earnings': str(
                        round(
                            total - float(order_commission),
                            2
                        )
                    ),
                },
                'vs_previous_period': {
                    'previous_total': str(
                        round(prev_total, 2)
                    ),
                    'growth_percent': calc_growth(
                        total, prev_total
                    ),
                },
                'daily_chart': list(daily),
            }
        )


class BusinessCustomersSectionView(APIView):
    """
    GET - Customers section for business dashboard
    GET /api/v1/dashboard/business/<business_id>/customers/?period=this_month
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, business_id):
        from apps.marketplace.models import Business

        try:
            business = Business.objects.get(
                pk=business_id, owner=request.user
            )
        except Business.DoesNotExist:
            return api_response(
                'error', 'Business not found',
                http_status=403
            )

        period = request.query_params.get(
            'period', 'this_month'
        )
        start, end = get_period_range(period)

        # Unique customers this period
        new_customers = Order.objects.filter(
            business=business,
            created_at__gte=start,
            created_at__lte=end
        ).values('user').distinct().count()

        # Top customers by spend
        top_customers = Order.objects.filter(
            business=business,
            payment_status='paid'
        ).values(
            'user__id', 'user__full_name', 'user__email'
        ).annotate(
            total_spent=Sum('total'),
            order_count=Count('id')
        ).order_by('-total_spent')[:10]

        # Returning customers
        returning = Order.objects.filter(
            business=business
        ).values('user').annotate(
            count=Count('id')
        ).filter(count__gt=1).count()

        return api_response(
            'success', 'Customers section retrieved',
            data={
                'period': period,
                'new_this_period': new_customers,
                'returning_customers': returning,
                'top_customers': list(top_customers),
            }
        )


class BusinessStaffSectionView(APIView):
    """
    GET - Staff section for business dashboard
    GET /api/v1/dashboard/business/<business_id>/staff-summary/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, business_id):
        from apps.marketplace.models import Business

        try:
            business = Business.objects.get(
                pk=business_id, owner=request.user
            )
        except Business.DoesNotExist:
            return api_response(
                'error', 'Business not found',
                http_status=403
            )

        try:
            from apps.staff.models import (
                BusinessMember, StaffLeave,
                StaffAttendance, StaffInvitation
            )

            members = BusinessMember.objects.filter(
                business=business, status='active'
            )
            today = timezone.now().date()

            clocked_in_today = StaffAttendance.objects.filter(
                member__business=business,
                date=today,
                clock_out__isnull=True
            ).count()

            pending_leaves = StaffLeave.objects.filter(
                member__business=business,
                status='pending'
            ).count()

            pending_invitations = StaffInvitation.objects.filter(
                business=business,
                status='pending'
            ).count()

            return api_response(
                'success', 'Staff section retrieved',
                data={
                    'total_active': members.count(),
                    'clocked_in_today': clocked_in_today,
                    'pending_leave_requests': pending_leaves,
                    'pending_invitations': pending_invitations,
                    'by_role': list(
                        members.values(
                            'role__name'
                        ).annotate(
                            count=Count('id')
                        )
                    ),
                }
            )
        except Exception as e:
            return api_response(
                'success', 'Staff section retrieved',
                data={
                    'total_active': 0,
                    'error': str(e)
                }
            )


class BusinessWalletSectionView(APIView):
    """
    GET - Wallet section for business dashboard
    GET /api/v1/dashboard/business/<business_id>/wallet-summary/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, business_id):
        from apps.marketplace.models import Business

        try:
            business = Business.objects.get(
                pk=business_id, owner=request.user
            )
        except Business.DoesNotExist:
            return api_response(
                'error', 'Business not found',
                http_status=403
            )

        try:
            from apps.wallet.models import (
                VendorWallet, WithdrawalRequest,
                VendorTransaction
            )

            wallet = VendorWallet.objects.filter(
                business=business
            ).first()

            if not wallet:
                return api_response(
                    'success', 'Wallet section retrieved',
                    data={
                        'available_balance': '0.00',
                        'pending_balance': '0.00',
                        'total_earned': '0.00',
                        'total_withdrawn': '0.00',
                    }
                )

            recent_transactions = VendorTransaction.objects.filter(
                wallet=wallet
            ).order_by('-created_at').values(
                'id', 'transaction_type', 'amount',
                'description', 'created_at'
            )[:10]

            pending_withdrawals = WithdrawalRequest.objects.filter(
                wallet=wallet, status='pending'
            ).count()

            return api_response(
                'success', 'Wallet section retrieved',
                data={
                    'available_balance': str(
                        wallet.available_balance
                    ),
                    'pending_balance': str(
                        wallet.pending_balance
                    ),
                    'total_earned': str(wallet.total_earned),
                    'total_withdrawn': str(
                        wallet.total_withdrawn
                    ),
                    'pending_withdrawal_requests': (
                        pending_withdrawals
                    ),
                    'recent_transactions': list(
                        recent_transactions
                    ),
                }
            )
        except Exception as e:
            return api_response(
                'error', str(e), http_status=500
            )


class BusinessReviewsSectionView(APIView):
    """
    GET - Reviews section for business dashboard
    GET /api/v1/dashboard/business/<business_id>/reviews-summary/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, business_id):
        from apps.marketplace.models import Business

        try:
            business = Business.objects.get(
                pk=business_id, owner=request.user
            )
        except Business.DoesNotExist:
            return api_response(
                'error', 'Business not found',
                http_status=403
            )

        from django.contrib.contenttypes.models import ContentType
        biz_ct = ContentType.objects.get_for_model(business)
        reviews = Review.objects.filter(
            objects_type=biz_ct,
            objects_id=business.id
        )
        avg = reviews.aggregate(avg=Avg('rating'))['avg'] or 0
        # Rating distribution
        distribution = {}
        for i in range(1, 6):
            distribution[str(i)] = reviews.filter(
                rating=i
            ).count()

        recent = reviews.order_by('-created_at').values(
            'id', 'rating', 'comment',
            'user__full_name', 'created_at'
        )[:5]

        return api_response(
            'success', 'Reviews section retrieved',
            data={
                'total': reviews.count(),
                'average_rating': round(avg, 1),
                'distribution': distribution,
                'recent': list(recent),
            }
        )


# ── User dashboard (existing, kept) ──────────────────────
from .user_views import UserDashboardView