from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.utils import timezone
from apps.common.views import api_response
from apps.common.permissions import IsAdmin
from .models import Plan, PlanFeature, Subscription, SubscriptionHistory
from .serializers import (
    PlanSerializer,
    SubscriptionSerializer,
    SubscriptionHistorySerializer,
    SubscribeSerializer,
    UpgradeSerializer,
)
from .utils import get_subscription_end_date


class PlanListView(APIView):
    """List all available plans"""
    permission_classes = []

    def get(self, request):
        plans = Plan.objects.filter(is_active=True)
        serializer = PlanSerializer(plans, many=True)
        return api_response(
            'success',
            'Plans retrieved successfully',
            data={
                'count': plans.count(),
                'results': serializer.data
            }
        )

    def post(self, request):
        """Admin create plan"""
        serializer = PlanSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success',
                'Plan created successfully',
                data=serializer.data,
                http_status=status.HTTP_201_CREATED
            )
        return api_response(
            'error',
            'Creation failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class PlanDetailView(APIView):
    """Get, update and delete a plan"""
    permission_classes = []

    def get_object(self, pk):
        try:
            return Plan.objects.get(pk=pk, is_active=True)
        except Plan.DoesNotExist:
            return None

    def get(self, request, pk):
        plan = self.get_object(pk)
        if not plan:
            return api_response(
                'error',
                'Plan not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = PlanSerializer(plan)
        return api_response(
            'success',
            'Plan retrieved successfully',
            data=serializer.data
        )

    def patch(self, request, pk):
        plan = self.get_object(pk)
        if not plan:
            return api_response(
                'error',
                'Plan not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = PlanSerializer(
            plan,
            data=request.data,
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success',
                'Plan updated successfully',
                data=serializer.data
            )
        return api_response(
            'error',
            'Update failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )

    def delete(self, request, pk):
        plan = self.get_object(pk)
        if not plan:
            return api_response(
                'error',
                'Plan not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        plan.is_active = False
        plan.save()
        return api_response(
            'success',
            'Plan deleted successfully'
        )


class AddPlanFeatureView(APIView):
    """Add features to a plan"""
    permission_classes = [IsAdmin]

    def post(self, request, pk):
        try:
            plan = Plan.objects.get(pk=pk)
        except Plan.DoesNotExist:
            return api_response(
                'error',
                'Plan not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        features = request.data.get('features', [])
        created = []

        for feature in features:
            pf = PlanFeature.objects.create(
                plan=plan,
                feature=feature.get('feature', ''),
                is_included=feature.get('is_included', True)
            )
            created.append({
                'id': pf.id,
                'feature': pf.feature,
                'is_included': pf.is_included
            })

        return api_response(
            'success',
            f'{len(created)} features added successfully',
            data=created,
            http_status=status.HTTP_201_CREATED
        )


class SubscribeView(APIView):
    """Subscribe to a plan"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = SubscribeSerializer(data=request.data)
        if serializer.is_valid():
            plan_id = serializer.validated_data['plan_id']
            payment_reference = serializer.validated_data.get(
                'payment_reference', ''
            )

            try:
                plan = Plan.objects.get(pk=plan_id, is_active=True)
            except Plan.DoesNotExist:
                return api_response(
                    'error',
                    'Plan not found',
                    http_status=status.HTTP_404_NOT_FOUND
                )

            # Check if already subscribed
            existing = Subscription.objects.filter(
                user=request.user,
                status__in=['active', 'trial']
            ).first()

            if existing:
                return api_response(
                    'error',
                    'You already have an active subscription. Please upgrade or cancel first.',
                    http_status=status.HTTP_400_BAD_REQUEST
                )

            now = timezone.now()

            # Handle trial
            if plan.trial_days > 0 and not payment_reference:
                end_date = get_subscription_end_date(
                    plan.billing_cycle,
                    trial_days=plan.trial_days
                )
                sub_status = 'trial'
                trial_end = end_date
                action = 'trial_started'
            else:
                end_date = get_subscription_end_date(
                    plan.billing_cycle
                )
                sub_status = 'active'
                trial_end = None
                action = 'subscribed'

            # Create subscription
            subscription = Subscription.objects.create(
                user=request.user,
                plan=plan,
                status=sub_status,
                start_date=now,
                end_date=end_date,
                trial_end_date=trial_end,
                payment_reference=payment_reference,
            )

            # Create history
            SubscriptionHistory.objects.create(
                user=request.user,
                plan=plan,
                action=action,
                amount=plan.price if sub_status == 'active' else 0,
                payment_reference=payment_reference,
            )

            # Send notification
            from apps.notifications.utils import send_notification
            send_notification(
                user=request.user,
                title='Subscription Activated',
                message=f'Your {plan.name} subscription is now active until {end_date.strftime("%B %d, %Y")}',
                notification_type='system',
                data={
                    'plan_id': plan.id,
                    'plan_name': plan.name,
                    'end_date': str(end_date),
                }
            )

            return api_response(
                'success',
                f'Successfully subscribed to {plan.name}',
                data=SubscriptionSerializer(subscription).data,
                http_status=status.HTTP_201_CREATED
            )

        return api_response(
            'error',
            'Subscription failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class MySubscriptionView(APIView):
    """Get current user subscription"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            subscription = request.user.subscription
            serializer = SubscriptionSerializer(subscription)
            return api_response(
                'success',
                'Subscription retrieved successfully',
                data=serializer.data
            )
        except Subscription.DoesNotExist:
            return api_response(
                'error',
                'No active subscription found',
                http_status=status.HTTP_404_NOT_FOUND
            )


class CancelSubscriptionView(APIView):
    """Cancel current subscription"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            subscription = request.user.subscription
        except Subscription.DoesNotExist:
            return api_response(
                'error',
                'No active subscription found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        if subscription.status == 'cancelled':
            return api_response(
                'error',
                'Subscription is already cancelled',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        subscription.status = 'cancelled'
        subscription.cancelled_at = timezone.now()
        subscription.auto_renew = False
        subscription.save()

        # Create history
        SubscriptionHistory.objects.create(
            user=request.user,
            plan=subscription.plan,
            action='cancelled',
            amount=0,
            notes='Cancelled by user'
        )

        # Send notification
        from apps.notifications.utils import send_notification
        send_notification(
            user=request.user,
            title='Subscription Cancelled',
            message=f'Your {subscription.plan.name} subscription has been cancelled. You can still use it until {subscription.end_date.strftime("%B %d, %Y")}',
            notification_type='system'
        )

        return api_response(
            'success',
            'Subscription cancelled successfully',
            data=SubscriptionSerializer(subscription).data
        )


class UpgradeSubscriptionView(APIView):
    """Upgrade or downgrade subscription"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = UpgradeSerializer(data=request.data)
        if serializer.is_valid():
            plan_id = serializer.validated_data['plan_id']
            payment_reference = serializer.validated_data.get(
                'payment_reference', ''
            )

            try:
                new_plan = Plan.objects.get(
                    pk=plan_id,
                    is_active=True
                )
            except Plan.DoesNotExist:
                return api_response(
                    'error',
                    'Plan not found',
                    http_status=status.HTTP_404_NOT_FOUND
                )

            try:
                subscription = request.user.subscription
            except Subscription.DoesNotExist:
                return api_response(
                    'error',
                    'No active subscription found',
                    http_status=status.HTTP_404_NOT_FOUND
                )

            old_plan = subscription.plan
            is_upgrade = new_plan.price > old_plan.price

            # Update subscription
            subscription.plan = new_plan
            subscription.end_date = get_subscription_end_date(
                new_plan.billing_cycle
            )
            subscription.status = 'active'
            subscription.payment_reference = payment_reference
            subscription.save()

            action = 'upgraded' if is_upgrade else 'downgraded'

            # Create history
            SubscriptionHistory.objects.create(
                user=request.user,
                plan=new_plan,
                action=action,
                amount=new_plan.price,
                payment_reference=payment_reference,
                notes=f'Changed from {old_plan.name} to {new_plan.name}'
            )

            # Send notification
            from apps.notifications.utils import send_notification
            send_notification(
                user=request.user,
                title=f'Subscription {action.capitalize()}d',
                message=f'Your subscription has been {action} to {new_plan.name}',
                notification_type='system'
            )

            return api_response(
                'success',
                f'Subscription {action} successfully',
                data=SubscriptionSerializer(subscription).data
            )

        return api_response(
            'error',
            'Upgrade failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class RenewSubscriptionView(APIView):
    """Renew subscription"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            subscription = request.user.subscription
        except Subscription.DoesNotExist:
            return api_response(
                'error',
                'No subscription found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        payment_reference = request.data.get('payment_reference', '')

        # Extend end date
        subscription.end_date = get_subscription_end_date(
            subscription.plan.billing_cycle
        )
        subscription.status = 'active'
        subscription.payment_reference = payment_reference
        subscription.save()

        # Create history
        SubscriptionHistory.objects.create(
            user=request.user,
            plan=subscription.plan,
            action='renewed',
            amount=subscription.plan.price,
            payment_reference=payment_reference,
        )

        # Send notification
        from apps.notifications.utils import send_notification
        send_notification(
            user=request.user,
            title='Subscription Renewed',
            message=f'Your {subscription.plan.name} subscription has been renewed until {subscription.end_date.strftime("%B %d, %Y")}',
            notification_type='system'
        )

        return api_response(
            'success',
            'Subscription renewed successfully',
            data=SubscriptionSerializer(subscription).data
        )


class SubscriptionHistoryView(APIView):
    """Get subscription history"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        history = SubscriptionHistory.objects.filter(
            user=request.user
        )
        serializer = SubscriptionHistorySerializer(
            history,
            many=True
        )
        return api_response(
            'success',
            'Subscription history retrieved successfully',
            data={
                'count': history.count(),
                'results': serializer.data
            }
        )


class AdminSubscriptionListView(APIView):
    """Admin - list all subscriptions"""
    permission_classes = [IsAdmin]

    def get(self, request):
        subscriptions = Subscription.objects.all()

        sub_status = request.query_params.get('status')
        if sub_status:
            subscriptions = subscriptions.filter(status=sub_status)

        plan_id = request.query_params.get('plan')
        if plan_id:
            subscriptions = subscriptions.filter(plan__id=plan_id)

        serializer = SubscriptionSerializer(
            subscriptions,
            many=True
        )

        # Stats
        active_count = subscriptions.filter(
            status__in=['active', 'trial']
        ).count()
        total_revenue = sum(
            h.amount for h in SubscriptionHistory.objects.filter(
                action__in=['subscribed', 'renewed', 'upgraded']
            )
        )

        return api_response(
            'success',
            'All subscriptions retrieved',
            data={
                'count': subscriptions.count(),
                'active_count': active_count,
                'total_revenue': str(total_revenue),
                'results': serializer.data
            }
        )
