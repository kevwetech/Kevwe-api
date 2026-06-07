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
from django.db.models import Sum
from apps.deliveries.models import CompanyEarnings

User = get_user_model()


class DashboardView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        today = timezone.now().date()
        this_month_start = today.replace(day=1)
        last_month_start = (this_month_start - timedelta(days=1)).replace(day=1)

        # ── Users ──────────────────────────────
        total_users = User.objects.count()
        new_users_today = User.objects.filter(
            created_at__date=today
        ).count()
        new_users_this_month = User.objects.filter(
            created_at__date__gte=this_month_start
        ).count()
        new_users_last_month = User.objects.filter(
            created_at__date__gte=last_month_start,
            created_at__date__lt=this_month_start
        ).count()

        # ── Products ───────────────────────────
        total_products = Product.objects.count()
        active_products = Product.objects.filter(
            is_active=True
        ).count()
        out_of_stock = Product.objects.filter(
            stock=0
        ).count()
        total_categories = Category.objects.count()

        # ── Orders ─────────────────────────────
        total_orders = Order.objects.count()
        pending_orders = Order.objects.filter(
            status='pending'
        ).count()
        confirmed_orders = Order.objects.filter(
            status='confirmed'
        ).count()
        delivered_orders = Order.objects.filter(
            status='delivered'
        ).count()
        cancelled_orders = Order.objects.filter(
            status='cancelled'
        ).count()
        orders_today = Order.objects.filter(
            created_at__date=today
        ).count()
        orders_this_month = Order.objects.filter(
            created_at__date__gte=this_month_start
        ).count()

        # ── Revenue ────────────────────────────
        total_revenue = Order.objects.filter(
            payment_status='paid',
        ).aggregate(total=Sum('total'))['total'] or 0

        revenue_today = Order.objects.filter(
            payment_status='paid',
            created_at__date=today
        ).aggregate(total=Sum('total'))['total'] or 0

        revenue_this_month = Order.objects.filter(
            payment_status='paid',
           created_at__date__gte=this_month_start
        ).aggregate(total=Sum('total'))['total'] or 0

        revenue_last_month = Order.objects.filter(
            payment_status='paid',
            created_at__date__gte=last_month_start,
            created_at__date__lt=this_month_start
        ).aggregate(total=Sum('total'))['total'] or 0

        # ── Bookings ───────────────────────────
        total_bookings = Booking.objects.count()
        pending_bookings = Booking.objects.filter(
            status='pending'
        ).count()
        confirmed_bookings = Booking.objects.filter(
            status='confirmed'
        ).count()
        cancelled_bookings = Booking.objects.filter(
            status='cancelled'
        ).count()
        bookings_today = Booking.objects.filter(
            created_at__date=today
        ).count()

        # ── Booking Revenue ────────────────────
        booking_revenue = Booking.objects.filter(
            payment_status='paid'
        ).aggregate(total=Sum('total'))['total'] or 0

        booking_revenue_this_month = Booking.objects.filter(
            payment_status='paid',
            created_at__date__gte=this_month_start
        ).aggregate(total=Sum('total'))['total'] or 0

        booking_revenue_last_month = Booking.objects.filter(
            payment_status='paid',
            created_at__date__gte=last_month_start,
            created_at__date__lt=this_month_start
        ).aggregate(total=Sum('total'))['total'] or 0
        
        booking_revenue_this_year = Booking.objects.filter(
            payment_status='paid',
            created_at__year=today.year
        ).aggregate(total=Sum('total'))['total'] or 0

        # ── Delivery Revenue (CompanyEarnings) ─────
        delivery_revenue_total = CompanyEarnings.objects.aggregate(
            total=Sum('amount')
        )['total'] or 0

        delivery_revenue_this_month = CompanyEarnings.objects.filter(
            created_at__date__gte=this_month_start
        ).aggregate(total=Sum('amount'))['total'] or 0

        delivery_revenue_last_month = CompanyEarnings.objects.filter(
            created_at__date__gte=last_month_start,
            created_at__date__lt=this_month_start
        ).aggregate(total=Sum('amount'))['total'] or 0

        delivery_revenue_this_year = CompanyEarnings.objects.filter(
            created_at__year=today.year
        ).aggregate(total=Sum('amount'))['total'] or 0



        # ── Reviews ────────────────────────────
        total_reviews = Review.objects.count()
        avg_rating = 0
        if total_reviews > 0:
            avg_rating = sum(
                r.rating for r in Review.objects.all()
            ) / total_reviews

        # ── Recent Orders ──────────────────────
        recent_orders = Order.objects.order_by(
            '-created_at'
        )[:5]
        recent_orders_data = [
            {
                'id': order.id,
                'reference': order.reference,
                'status': order.status,
                'payment_status': order.payment_status,
                'total': str(order.total),
                'created_at': order.created_at,
            }
            for order in recent_orders
        ]

        # ── Recent Bookings ────────────────────
        recent_bookings = Booking.objects.order_by(
            '-created_at'
        )[:5]
        recent_bookings_data = [
            {
                'id': booking.id,
                'reference': booking.reference,
                'guest_name': booking.guest_name,
                'item_name': booking.item.name,
                'status': booking.status,
                'total': str(booking.total),
                'check_in': booking.check_in,
                'check_out': booking.check_out,
            }
            for booking in recent_bookings
        ]

        # ── Recent Users ───────────────────────
        recent_users = User.objects.order_by('-created_at')[:5]
        recent_users_data = [
            {
                'id': user.id,
                'full_name': user.full_name,
                'email': user.email,
                'role': user.role,
                'is_verified': user.is_verified,
                'created_at': user.created_at,
            }
            for user in recent_users
        ]

        # ── Top Products ───────────────────────
        from apps.orders.models import OrderItem
        from django.db.models import Sum, Count

        top_products = Product.objects.annotate(
            total_sold=Sum('order_items__quantity'),
            order_count=Count('order_items')
        ).order_by('-total_sold')[:5]

        top_products_data = [
            {
                'id': product.id,
                'name': product.name,
                'price': str(product.price),
                'stock': product.stock,
                'total_sold': product.total_sold or 0,
                'order_count': product.order_count or 0,
            }
            for product in top_products
        ]

        return api_response(
            'success',
            'Dashboard data retrieved successfully',
            data={
                'users': {
                    'total': total_users,
                    'new_today': new_users_today,
                    'new_this_month': new_users_this_month,
                    'new_last_month': new_users_last_month,
                },
                'products': {
                    'total': total_products,
                    'active': active_products,
                    'out_of_stock': out_of_stock,
                    'categories': total_categories,
                },
                'orders': {
                    'total': total_orders,
                    'today': orders_today,
                    'this_month': orders_this_month,
                    'pending': pending_orders,
                    'confirmed': confirmed_orders,
                    'delivered': delivered_orders,
                    'cancelled': cancelled_orders,
                },
                'revenue': {
                    'orders': {
                        'total': str(total_revenue),
                        'today': str(revenue_today),
                        'this_month': str(revenue_this_month),
                        'last_month': str(revenue_last_month),
                    },
                    'deliveries': {
                        'total': str(delivery_revenue_total),
                        'this_month': str(delivery_revenue_this_month),
                        'last_month': str(delivery_revenue_last_month),
                        'this_year': str(delivery_revenue_this_year),
                    }
                },
                'bookings': {
                    'total': total_bookings,
                    'today': bookings_today,
                    'pending': pending_bookings,
                    'confirmed': confirmed_bookings,
                    'cancelled': cancelled_bookings,
                    'revenue': {
                        'total': str(booking_revenue),
                        'this_month': str(booking_revenue_this_month),
                        'last_month': str(booking_revenue_last_month),
                        'this_year': str(booking_revenue_this_year),
                    }
                },
                'reviews': {
                    'total': total_reviews,
                    'average_rating': round(avg_rating, 1),
                },
                
                'recent_orders': recent_orders_data,
                'recent_bookings': recent_bookings_data,
                'recent_users': recent_users_data,
                'top_products': top_products_data,
            }
        )


class AdminUserListView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        users = User.objects.all()

        # Filter by role
        role = request.query_params.get('role')
        if role:
            users = users.filter(role=role)

        # Filter by verified
        is_verified = request.query_params.get('is_verified')
        if is_verified:
            users = users.filter(
                is_verified=is_verified == 'true'
            )

        # Search
        search = request.query_params.get('search')
        if search:
            users = users.filter(
                email__icontains=search
            ) | users.filter(
                full_name__icontains=search
            )

        users_data = [
            {
                'id': user.id,
                'full_name': user.full_name,
                'email': user.email,
                'phone': user.phone,
                'role': user.role,
                'is_verified': user.is_verified,
                'is_active': user.is_active,
                'created_at': user.created_at,
            }
            for user in users
        ]

        return api_response(
            'success',
            'Users retrieved successfully',
            data={
                'count': users.count(),
                'results': users_data
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
                'error',
                'User not found',
                http_status=404
            )

        return api_response(
            'success',
            'User retrieved successfully',
            data={
                'id': user.id,
                'full_name': user.full_name,
                'email': user.email,
                'phone': user.phone,
                'role': user.role,
                'is_verified': user.is_verified,
                'is_active': user.is_active,
                'created_at': user.created_at,
            }
        )

    def patch(self, request, pk):
        user = self.get_object(pk)
        if not user:
            return api_response(
                'error',
                'User not found',
                http_status=404
            )

        # Update role
        role = request.data.get('role')
        if role:
            user.role = role

        # Update active status
        is_active = request.data.get('is_active')
        if is_active is not None:
            user.is_active = is_active

        # Update verified status
        is_verified = request.data.get('is_verified')
        if is_verified is not None:
            user.is_verified = is_verified

        user.save()

        return api_response(
            'success',
            'User updated successfully',
            data={
                'id': user.id,
                'full_name': user.full_name,
                'email': user.email,
                'role': user.role,
                'is_verified': user.is_verified,
                'is_active': user.is_active,
            }
        )

    def delete(self, request, pk):
        user = self.get_object(pk)
        if not user:
            return api_response(
                'error',
                'User not found',
                http_status=404
            )
        user.delete()
        return api_response(
            'success',
            'User deleted successfully'
        )