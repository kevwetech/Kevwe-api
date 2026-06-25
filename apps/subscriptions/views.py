from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from apps.common.views import api_response
from apps.common.permissions import IsAdmin
from apps.common.utils import generate_reference
from .models import (
    BusinessPlan,
    BusinessPlanFeature,
    BusinessSubscription,
    BusinessSubscriptionHistory,
    BusinessSubscriptionPayment,
)
from .serializers import (
    BusinessPlanSerializer,
    BusinessPlanFeatureSerializer,
    BusinessSubscriptionSerializer,
    BusinessSubscriptionHistorySerializer,
    BusinessSubscriptionPaymentSerializer,
    SubscribeSerializer,
    UpgradeDowngradeSerializer,
)


class BusinessPlanListView(APIView):
    """List all available business plans"""
    permission_classes = []

    def get(self, request):
        plans = BusinessPlan.objects.filter(
            is_active=True,
            is_public=True
        )

        # Filter by industry
        industry_id = request.query_params.get('industry')
        if industry_id:
            plans = plans.filter(
                supported_industries__id=industry_id
            ) | plans.filter(
                supported_industries__isnull=True
            )

        serializer = BusinessPlanSerializer(
            plans, many=True
        )
        return api_response(
            'success',
            'Business plans retrieved successfully',
            data={
                'count': plans.count(),
                'results': serializer.data
            }
        )


class BusinessPlanDetailView(APIView):
    """Get single plan details"""
    permission_classes = []

    def get(self, request, pk):
        try:
            plan = BusinessPlan.objects.get(
                pk=pk, is_active=True
            )
        except BusinessPlan.DoesNotExist:
            return api_response(
                'error', 'Plan not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = BusinessPlanSerializer(plan)
        return api_response(
            'success',
            'Plan retrieved successfully',
            data=serializer.data
        )


class AdminBusinessPlanView(APIView):
    """Admin CRUD for business plans"""
    permission_classes = [IsAdmin]

    def post(self, request):
        serializer = BusinessPlanSerializer(
            data=request.data
        )
        if serializer.is_valid():
            plan = serializer.save()
            return api_response(
                'success',
                'Plan created successfully',
                data=BusinessPlanSerializer(plan).data,
                http_status=status.HTTP_201_CREATED
            )
        return api_response(
            'error', 'Creation failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )

    def patch(self, request, pk):
        try:
            plan = BusinessPlan.objects.get(pk=pk)
        except BusinessPlan.DoesNotExist:
            return api_response(
                'error', 'Plan not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = BusinessPlanSerializer(
            plan, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success',
                'Plan updated successfully',
                data=serializer.data
            )
        return api_response(
            'error', 'Update failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )

    def delete(self, request, pk):
        try:
            plan = BusinessPlan.objects.get(pk=pk)
        except BusinessPlan.DoesNotExist:
            return api_response(
                'error', 'Plan not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        plan.is_active = False
        plan.save()
        return api_response(
            'success', 'Plan deactivated successfully'
        )


class BusinessPlanFeatureView(APIView):
    """Manage plan features"""
    permission_classes = [IsAdmin]

    def get(self, request, plan_id):
        try:
            plan = BusinessPlan.objects.get(pk=plan_id)
        except BusinessPlan.DoesNotExist:
            return api_response(
                'error', 'Plan not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        features = plan.plan_features.all()
        serializer = BusinessPlanFeatureSerializer(
            features, many=True
        )
        return api_response(
            'success',
            'Plan features retrieved successfully',
            data={
                'count': features.count(),
                'results': serializer.data
            }
        )

    def post(self, request, plan_id):
        try:
            plan = BusinessPlan.objects.get(pk=plan_id)
        except BusinessPlan.DoesNotExist:
            return api_response(
                'error', 'Plan not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = BusinessPlanFeatureSerializer(
            data=request.data
        )
        if serializer.is_valid():
            serializer.save(plan=plan)
            return api_response(
                'success',
                'Feature added successfully',
                data=serializer.data,
                http_status=status.HTTP_201_CREATED
            )
        return api_response(
            'error', 'Failed to add feature',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )

    def delete(self, request, plan_id, feature_id):
        try:
            feature = BusinessPlanFeature.objects.get(
                pk=feature_id, plan__id=plan_id
            )
            feature.delete()
            return api_response(
                'success', 'Feature removed successfully'
            )
        except BusinessPlanFeature.DoesNotExist:
            return api_response(
                'error', 'Feature not found',
                http_status=status.HTTP_404_NOT_FOUND
            )


class BusinessSubscriptionView(APIView):
    """Get business subscription status"""
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

        try:
            sub = business.subscription
            serializer = BusinessSubscriptionSerializer(sub)
            limits = sub.check_limits()

            return api_response(
                'success',
                'Subscription retrieved successfully',
                data={
                    **serializer.data,
                    'limits': limits,
                }
            )
        except BusinessSubscription.DoesNotExist:
            return api_response(
                'success',
                'No active subscription',
                data={
                    'subscription': None,
                    'message': (
                        'Subscribe to a plan to unlock features'
                    ),
                    'plans_url': (
                        '/api/v1/subscriptions/business/plans/'
                    ),
                }
            )


class SubscribeView(APIView):
    """Subscribe a business to a plan"""
    permission_classes = [IsAuthenticated]

    def post(self, request, business_id):
        from apps.marketplace.models import Business
        try:
            business = Business.objects.get(pk=business_id)
        except Business.DoesNotExist:
            return api_response(
                'error', 'Business not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        if business.owner != request.user:
            return api_response(
                'error', 'Only business owner can subscribe',
                http_status=status.HTTP_403_FORBIDDEN
            )

        serializer = SubscribeSerializer(data=request.data)
        if not serializer.is_valid():
            return api_response(
                'error', 'Subscription failed',
                errors=serializer.errors,
                http_status=status.HTTP_400_BAD_REQUEST
            )

        data = serializer.validated_data

        try:
            plan = BusinessPlan.objects.get(
                pk=data['plan_id'],
                is_active=True
            )
        except BusinessPlan.DoesNotExist:
            return api_response(
                'error', 'Plan not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        # Check industry support
        if (business.industry and
                not plan.is_available_for_industry(
                    business.industry
                )):
            return api_response(
                'error',
                f'{plan.name} plan is not available for '
                f'{business.industry.name} businesses.',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        # Check existing active subscription
        existing = BusinessSubscription.objects.filter(
            business=business,
            status__in=['active', 'trial']
        ).first()

        if existing and existing.is_active:
            return api_response(
                'error',
                f'Already subscribed to {existing.plan.name}.'
                f' Use upgrade/downgrade instead.',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        billing_cycle  = data.get('billing_cycle', 'monthly')
        payment_method = data.get('payment_method', 'wallet')
        now            = timezone.now()

        # Calculate amount
        amount = (
            plan.monthly_price
            if billing_cycle == 'monthly'
            else plan.yearly_price
        )

        # Calculate end date
        if billing_cycle == 'monthly':
            end_date = now + timedelta(days=30)
        elif billing_cycle == 'yearly':
            end_date = now + timedelta(days=365)
        else:
            end_date = now + timedelta(days=36500)

        # Trial period check
        trial_end  = None
        sub_status = 'active'
        had_trial  = BusinessSubscriptionHistory.objects.filter(
            business=business,
            action='trial_started'
        ).exists()

        if plan.trial_days > 0 and not had_trial:
            trial_end  = now + timedelta(days=plan.trial_days)
            end_date   = trial_end + (
                timedelta(days=30)
                if billing_cycle == 'monthly'
                else timedelta(days=365)
            )
            sub_status = 'trial'
            amount     = Decimal('0')

        # Handle payment
        payment_reference = None
        if amount > 0:
            if payment_method == 'wallet':
                from apps.wallet.utils import get_or_create_wallet
                wallet = get_or_create_wallet(request.user)

                if wallet.balance < amount:
                    return api_response(
                        'error',
                        f'Insufficient wallet balance. '
                        f'Need ₦{amount}',
                        data={
                            'wallet_balance': str(wallet.balance),
                            'required': str(amount),
                        },
                        http_status=status.HTTP_402_PAYMENT_REQUIRED
                    )

                ref = generate_reference('SUB')
                wallet.debit(
                    amount=amount,
                    description=(
                        f'{plan.name} subscription - '
                        f'{billing_cycle}'
                    ),
                    reference=ref
                )
                payment_reference = ref

        # Create or update subscription
        sub, created = BusinessSubscription.objects.update_or_create(
            business=business,
            defaults={
                'plan': plan,
                'billing_cycle': billing_cycle,
                'status': sub_status,
                'start_date': now,
                'end_date': end_date,
                'trial_end_date': trial_end,
                'grace_period_end': None,
                'next_billing_date': end_date,
                'last_renewed_at': now,
                'amount_paid': amount,
                'payment_reference': payment_reference,
                'auto_renew': True,
                'suspension_reason': None,
                'suspended_at': None,
                'suspended_by': None,
                'cancelled_at': None,
            }
        )

        # Sync usage counters
        sub.sync_usage_counters()

        # Record history
        action = (
            'trial_started'
            if sub_status == 'trial'
            else 'subscribed'
        )
        BusinessSubscriptionHistory.objects.create(
            business=business,
            plan=plan,
            action=action,
            billing_cycle=billing_cycle,
            amount=amount,
            payment_reference=payment_reference,
        )

        # Record payment
        BusinessSubscriptionPayment.objects.create(
            subscription=sub,
            business=business,
            plan=plan,
            payment_type='new',
            gateway=payment_method,
            billing_cycle=billing_cycle,
            amount=amount,
            net_amount=amount,
            reference=payment_reference or generate_reference(
                'SPAY'
            ),
            period_start=now,
            period_end=end_date,
            status='success',
            paid_at=now,
        )

        # Notify vendor
        from apps.notifications.utils import send_notification
        send_notification(
            user=request.user,
            title=f'Subscribed to {plan.name}! 🎉',
            message=(
                f'Your {plan.name} '
                f'{"trial" if sub_status == "trial" else billing_cycle} '
                f'subscription is now active.'
                + (
                    f' Trial ends {trial_end.date()}'
                    if trial_end else ''
                )
            ),
            notification_type='system',
        )

        return api_response(
            'success',
            f'Successfully subscribed to {plan.name}!',
            data=BusinessSubscriptionSerializer(sub).data,
            http_status=status.HTTP_201_CREATED
        )


class UpgradeDowngradeView(APIView):
    """Upgrade or downgrade subscription plan"""
    permission_classes = [IsAuthenticated]

    def post(self, request, business_id):
        from apps.marketplace.models import Business
        try:
            business = Business.objects.get(pk=business_id)
        except Business.DoesNotExist:
            return api_response(
                'error', 'Business not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        if business.owner != request.user:
            return api_response(
                'error', 'Access denied',
                http_status=status.HTTP_403_FORBIDDEN
            )

        try:
            current_sub = business.subscription
        except BusinessSubscription.DoesNotExist:
            return api_response(
                'error',
                'No active subscription to upgrade/downgrade',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        serializer = UpgradeDowngradeSerializer(
            data=request.data
        )
        if not serializer.is_valid():
            return api_response(
                'error', 'Failed',
                errors=serializer.errors,
                http_status=status.HTTP_400_BAD_REQUEST
            )

        data = serializer.validated_data

        try:
            new_plan = BusinessPlan.objects.get(
                pk=data['new_plan_id'],
                is_active=True
            )
        except BusinessPlan.DoesNotExist:
            return api_response(
                'error', 'Plan not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        if new_plan == current_sub.plan:
            return api_response(
                'error',
                'Already on this plan',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        old_plan       = current_sub.plan
        billing_cycle  = data.get('billing_cycle', 'monthly')
        payment_method = data.get('payment_method', 'wallet')
        is_upgrade     = (
            new_plan.monthly_price > old_plan.monthly_price
        )
        now            = timezone.now()

        # Calculate amount
        amount = (
            new_plan.monthly_price
            if billing_cycle == 'monthly'
            else new_plan.yearly_price
        )

        # Handle payment for upgrades
        payment_reference = None
        if amount > 0 and is_upgrade:
            if payment_method == 'wallet':
                from apps.wallet.utils import get_or_create_wallet
                wallet = get_or_create_wallet(request.user)

                if wallet.balance < amount:
                    return api_response(
                        'error',
                        f'Insufficient balance. Need ₦{amount}',
                        http_status=status.HTTP_402_PAYMENT_REQUIRED
                    )

                ref = generate_reference('SUB')
                wallet.debit(
                    amount=amount,
                    description=f'Upgrade to {new_plan.name}',
                    reference=ref
                )
                payment_reference = ref

        # Calculate new end date
        if billing_cycle == 'monthly':
            end_date = now + timedelta(days=30)
        else:
            end_date = now + timedelta(days=365)

        # Update subscription
        current_sub.plan              = new_plan
        current_sub.billing_cycle     = billing_cycle
        current_sub.status            = 'active'
        current_sub.end_date          = end_date
        current_sub.grace_period_end  = None
        current_sub.next_billing_date = end_date
        current_sub.last_renewed_at   = now
        current_sub.amount_paid       = amount
        current_sub.payment_reference = payment_reference
        current_sub.suspension_reason = None
        current_sub.suspended_at      = None
        current_sub.suspended_by      = None
        current_sub.save()

        # Sync usage counters
        current_sub.sync_usage_counters()

        # Record history
        action = 'upgraded' if is_upgrade else 'downgraded'
        BusinessSubscriptionHistory.objects.create(
            business=business,
            plan=new_plan,
            previous_plan=old_plan,
            action=action,
            billing_cycle=billing_cycle,
            amount=amount,
            payment_reference=payment_reference,
        )

        # Record payment
        if amount > 0:
            BusinessSubscriptionPayment.objects.create(
                subscription=current_sub,
                business=business,
                plan=new_plan,
                payment_type='upgrade' if is_upgrade else 'downgrade',
                gateway=payment_method,
                billing_cycle=billing_cycle,
                amount=amount,
                net_amount=amount,
                reference=payment_reference or generate_reference(
                    'SPAY'
                ),
                period_start=now,
                period_end=end_date,
                status='success',
                paid_at=now,
            )

        # Notify
        from apps.notifications.utils import send_notification
        action_text = 'upgraded to' if is_upgrade else 'downgraded to'
        send_notification(
            user=request.user,
            title=f'Plan {action_text.title()} {new_plan.name}!',
            message=(
                f'Your subscription has been '
                f'{action_text} {new_plan.name}.'
            ),
            notification_type='system',
        )

        return api_response(
            'success',
            f'Successfully {action_text} {new_plan.name}!',
            data=BusinessSubscriptionSerializer(
                current_sub
            ).data
        )


class CancelSubscriptionView(APIView):
    """Cancel business subscription"""
    permission_classes = [IsAuthenticated]

    def post(self, request, business_id):
        from apps.marketplace.models import Business
        try:
            business = Business.objects.get(pk=business_id)
        except Business.DoesNotExist:
            return api_response(
                'error', 'Business not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        if business.owner != request.user:
            return api_response(
                'error', 'Access denied',
                http_status=status.HTTP_403_FORBIDDEN
            )

        try:
            sub = business.subscription
        except BusinessSubscription.DoesNotExist:
            return api_response(
                'error', 'No active subscription',
                http_status=status.HTTP_404_NOT_FOUND
            )

        if sub.status == 'cancelled':
            return api_response(
                'error',
                'Subscription already cancelled',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        reason = request.data.get('reason', '')

        sub.status       = 'cancelled'
        sub.cancelled_at = timezone.now()
        sub.auto_renew   = False
        sub.save()

        BusinessSubscriptionHistory.objects.create(
            business=business,
            plan=sub.plan,
            action='cancelled',
            notes=reason,
        )

        from apps.notifications.utils import send_notification
        send_notification(
            user=request.user,
            title='Subscription Cancelled',
            message=(
                f'Your {sub.plan.name} subscription has been '
                f'cancelled. Access continues until '
                f'{sub.end_date.date()}.'
            ),
            notification_type='system',
        )

        return api_response(
            'success',
            f'Subscription cancelled. Access continues until '
            f'{sub.end_date.date()}.',
            data=BusinessSubscriptionSerializer(sub).data
        )


class SubscriptionHistoryView(APIView):
    """Get subscription history for a business"""
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

        history = BusinessSubscriptionHistory.objects.filter(
            business=business
        )
        serializer = BusinessSubscriptionHistorySerializer(
            history, many=True
        )
        return api_response(
            'success',
            'Subscription history retrieved successfully',
            data={
                'count': history.count(),
                'results': serializer.data
            }
        )


class SubscriptionPaymentHistoryView(APIView):
    """Get payment history for a business subscription"""
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

        payments = BusinessSubscriptionPayment.objects.filter(
            business=business
        )
        total_paid = sum(
            p.amount for p in payments
            if p.status == 'success'
        )

        serializer = BusinessSubscriptionPaymentSerializer(
            payments, many=True
        )
        return api_response(
            'success',
            'Payment history retrieved successfully',
            data={
                'count': payments.count(),
                'total_paid': str(total_paid),
                'results': serializer.data
            }
        )


class AdminBusinessSubscriptionListView(APIView):
    """Admin view all business subscriptions"""
    permission_classes = [IsAdmin]

    def get(self, request):
        subs = BusinessSubscription.objects.all()

        sub_status  = request.query_params.get('status')
        plan_id     = request.query_params.get('plan')
        business_id = request.query_params.get('business')

        if sub_status:
            subs = subs.filter(status=sub_status)
        if plan_id:
            subs = subs.filter(plan__id=plan_id)
        if business_id:
            subs = subs.filter(business__id=business_id)

        serializer = BusinessSubscriptionSerializer(
            subs, many=True
        )
        return api_response(
            'success',
            'All business subscriptions retrieved',
            data={
                'count':       subs.count(),
                'active':      subs.filter(status='active').count(),
                'trial':       subs.filter(status='trial').count(),
                'grace':       subs.filter(status='grace_period').count(),
                'expired':     subs.filter(status='expired').count(),
                'cancelled':   subs.filter(status='cancelled').count(),
                'suspended':   subs.filter(status='suspended').count(),
                'results':     serializer.data
            }
        )


class AdminSuspendSubscriptionView(APIView):
    """Admin suspends a business subscription"""
    permission_classes = [IsAdmin]

    def post(self, request, business_id):
        from apps.marketplace.models import Business
        try:
            business = Business.objects.get(pk=business_id)
            sub = business.subscription
        except (Business.DoesNotExist,
                BusinessSubscription.DoesNotExist):
            return api_response(
                'error', 'Not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        if sub.status == 'suspended':
            return api_response(
                'error',
                'Subscription already suspended',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        reason = request.data.get('reason', '')
        sub.suspend(request.user, reason)

        BusinessSubscriptionHistory.objects.create(
            business=business,
            plan=sub.plan,
            action='suspended',
            notes=reason,
        )

        return api_response(
            'success',
            'Subscription suspended successfully',
            data=BusinessSubscriptionSerializer(sub).data
        )


class AdminReactivateSubscriptionView(APIView):
    """Admin reactivates a suspended subscription"""
    permission_classes = [IsAdmin]

    def post(self, request, business_id):
        from apps.marketplace.models import Business
        try:
            business = Business.objects.get(pk=business_id)
            sub = business.subscription
        except (Business.DoesNotExist,
                BusinessSubscription.DoesNotExist):
            return api_response(
                'error', 'Not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        if sub.status != 'suspended':
            return api_response(
                'error',
                'Subscription is not suspended',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        sub.reactivate()

        BusinessSubscriptionHistory.objects.create(
            business=business,
            plan=sub.plan,
            action='reactivated',
        )

        return api_response(
            'success',
            'Subscription reactivated successfully',
            data=BusinessSubscriptionSerializer(sub).data
        )

class AdminUpdateSubscriptionLimitsView(APIView):
    """
    Admin updates plan limits globally
    OR sets custom overrides per business
    """
    permission_classes = [IsAdmin]

    def patch(self, request, business_id):
        """Update custom limits for a specific business"""
        from apps.marketplace.models import Business
        try:
            business = Business.objects.get(pk=business_id)
            sub = business.subscription
        except (Business.DoesNotExist,
                BusinessSubscription.DoesNotExist):
            return api_response(
                'error', 'Not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        # Update custom overrides
        # Pass null to reset to plan default
        allowed_fields = [
            'custom_max_products',
            'custom_max_staff',
            'custom_max_monthly_orders',
            'custom_max_monthly_bookings',
            'custom_max_bookable_items',
            'commission_rate_override',
        ]

        updated = {}
        for field in allowed_fields:
            if field in request.data:
                value = request.data[field]
                # null resets to plan default
                setattr(sub, field, value)
                updated[field] = value

        if not updated:
            return api_response(
                'error',
                'No valid fields provided. '
                'Use: custom_max_products, custom_max_staff, '
                'custom_max_monthly_orders, '
                'custom_max_monthly_bookings, '
                'custom_max_bookable_items, '
                'commission_rate_override',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        sub.save()

        # Notify vendor
        from apps.notifications.utils import send_notification
        send_notification(
            user=business.owner,
            title='Account Limits Updated ✅',
            message=(
                f'Your account limits have been updated by admin.'
            ),
            notification_type='system',
        )

        serializer = BusinessSubscriptionSerializer(sub)
        return api_response(
            'success',
            f'Custom limits updated for {business.name}',
            data={
                **serializer.data,
                'updated_fields': updated,
                'effective_limits': sub.effective_limits,
            }
        )


class AdminUpdatePlanLimitsView(APIView):
    """
    Admin updates plan limits globally
    Affects ALL businesses on this plan
    """
    permission_classes = [IsAdmin]

    def patch(self, request, plan_id):
        try:
            plan = BusinessPlan.objects.get(pk=plan_id)
        except BusinessPlan.DoesNotExist:
            return api_response(
                'error', 'Plan not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        allowed_fields= [
            'max_products', 'max_staff',
            'max_monthly_orders', 'max_monthly_bookings',
            'max_bookable_items',
            'allows_exclusive_bookings',
            'allows_slot_bookings',
            'commission_rate',
            'is_public',
            'trial_days',
            'grace_period_days',
        ]

        updated = {}
        for field in allowed_fields:
            if field in request.data:
                setattr(plan, field, request.data[field])
                updated[field] = request.data[field]

        if not updated:
            return api_response(
                'error',
                'No valid fields provided.',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        plan.save()

        # How many businesses affected
        affected = BusinessSubscription.objects.filter(
            plan=plan,
            status__in=['active', 'trial']
        ).count()

        return api_response(
            'success',
            f'Plan limits updated. '
            f'{affected} active businesses affected.',
            data={
                'plan': BusinessPlanSerializer(plan).data,
                'updated_fields': updated,
                'affected_businesses': affected,
            }
        )