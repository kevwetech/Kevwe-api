from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from apps.common.views import api_response
from apps.wallet.utils import get_or_create_wallet
from django.utils import timezone
from datetime import timedelta


class UserDashboardView(APIView):
    """
    User dashboard with wallet balance
    and spending analytics
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        wallet = get_or_create_wallet(user)

        # Date ranges
        now = timezone.now()
        this_month_start = now.replace(
            day=1, hour=0, minute=0, second=0
        )
        last_30_days = now - timedelta(days=30)

        # Wallet stats
        transactions = wallet.transactions.filter(
            status='success'
        )

        monthly_credits = sum(
            t.amount for t in transactions.filter(
                transaction_type='credit',
                created_at__gte=this_month_start
            )
        )
        monthly_debits = sum(
            t.amount for t in transactions.filter(
                transaction_type__in=['debit', 'withdrawal'],
                created_at__gte=this_month_start
            )
        )

        # Spending by category this month
        spending_by_category = {}
        for t in transactions.filter(
            transaction_type='debit',
            created_at__gte=this_month_start
        ):
            cat = t.description_type or 'other'
            spending_by_category[cat] = spending_by_category.get(
                cat, 0
            ) + float(t.amount)

        # Shipments stats
        from apps.shipments.models import Shipment
        shipments = Shipment.objects.filter(sender=user)
        total_shipment_spend = sum(
            s.price for s in shipments.filter(
                payment_status='paid'
            )
        )

        # Deliveries stats
        from apps.deliveries.models import DeliveryRequest
        deliveries = DeliveryRequest.objects.filter(customer=user)
        total_delivery_spend = sum(
            d.price for d in deliveries.filter(
                payment_status='paid'
            )
        )

        # Recent transactions
        recent_transactions = transactions.order_by(
            '-created_at'
        )[:5]
        from apps.wallet.serializers import WalletTransactionSerializer
        recent_tx_data = WalletTransactionSerializer(
            recent_transactions,
            many=True
        ).data

        # Orders stats
        from apps.orders.models import Order
        orders = Order.objects.filter(user=user)
        total_order_spend = sum(
            o.total for o in orders.filter(
                payment_status='paid'
            )
        )

        # Rides stats
        from apps.rides.models import Ride
        rides = Ride.objects.filter(rider=user)
        total_ride_spend = sum(
            r.actual_fare for r in rides.filter(
                status='completed',
                actual_fare__isnull=False
            )
        )

        # Subscription
        subscription_data = None
        try:
            sub = user.subscription
            subscription_data = {
                'plan': sub.plan.name,
                'status': sub.status,
                'days_remaining': sub.days_remaining,
                'end_date': sub.end_date,
            }
        except Exception:
            pass

        return api_response(
            'success',
            'Dashboard retrieved successfully',
            data={
                'wallet': {
                    'balance': str(wallet.balance),
                    'total_credited': str(wallet.total_credited),
                    'total_debited': str(wallet.total_debited),
                    'is_frozen': wallet.is_frozen,
                    'monthly_credits': str(monthly_credits),
                    'monthly_debits': str(monthly_debits),
                },
                'spending': {
                    'total_orders': str(total_order_spend),
                    'total_shipments': str(total_shipment_spend),
                    'total_deliveries': str(total_delivery_spend),
                    'total_rides': str(total_ride_spend),
                    'by_category': spending_by_category,
                },
                'stats': {
                    'total_orders': orders.count(),
                    'total_shipments': shipments.count(),
                    'total_deliveries': deliveries.count(),
                    'total_rides': rides.count(),
                    'active_shipments': shipments.filter(
                        status__in=['pending', 'assigned', 'in_transit']
                    ).count(),
                    'active_deliveries': deliveries.filter(
                        status__in=['pending', 'assigned', 'in_transit']
                    ).count(),
                },
                'subscription': subscription_data,
                'recent_transactions': recent_tx_data,
            }
        )