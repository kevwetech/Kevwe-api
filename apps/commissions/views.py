from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from apps.common.views import api_response
from apps.common.permissions import IsAdmin
from apps.common.utils import generate_reference
from .models import (
    CommissionRule,
    Commission,
    CommissionPayout,
    CommissionDispute,
    CommissionAdjustment,
)
from .serializers import (
    CommissionRuleSerializer,
    CommissionSerializer,
    CommissionPayoutSerializer,
    CommissionDisputeSerializer,
    CommissionAdjustmentSerializer,
)


class CommissionRuleListCreateView(APIView):
    """Manage commission rules"""
    permission_classes = [IsAdmin]

    def get(self, request):
        rules = CommissionRule.objects.filter(is_active=True)

        rule_type = request.query_params.get('type')
        industry_id = request.query_params.get('industry')
        business_id = request.query_params.get('business')

        if rule_type:
            rules = rules.filter(rule_type=rule_type)
        if industry_id:
            rules = rules.filter(industry__id=industry_id)
        if business_id:
            rules = rules.filter(business__id=business_id)

        serializer = CommissionRuleSerializer(rules, many=True)
        return api_response(
            'success',
            'Commission rules retrieved successfully',
            data={
                'count': rules.count(),
                'results': serializer.data
            }
        )

    def post(self, request):
        serializer = CommissionRuleSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            return api_response(
                'success',
                'Commission rule created successfully',
                data=serializer.data,
                http_status=status.HTTP_201_CREATED
            )
        return api_response(
            'error',
            'Creation failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class CommissionRuleDetailView(APIView):
    permission_classes = [IsAdmin]

    def get_object(self, pk):
        try:
            return CommissionRule.objects.get(pk=pk)
        except CommissionRule.DoesNotExist:
            return None

    def get(self, request, pk):
        rule = self.get_object(pk)
        if not rule:
            return api_response(
                'error', 'Rule not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = CommissionRuleSerializer(rule)
        return api_response(
            'success',
            'Commission rule retrieved successfully',
            data=serializer.data
        )

    def patch(self, request, pk):
        rule = self.get_object(pk)
        if not rule:
            return api_response(
                'error', 'Rule not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = CommissionRuleSerializer(
            rule, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success',
                'Commission rule updated successfully',
                data=serializer.data
            )
        return api_response(
            'error', 'Update failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )

    def delete(self, request, pk):
        rule = self.get_object(pk)
        if not rule:
            return api_response(
                'error', 'Rule not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        rule.is_active = False
        rule.save()
        return api_response(
            'success', 'Commission rule deleted successfully'
        )


class SimulateCommissionView(APIView):
    """
    Simulate commission calculation
    without creating a record
    """
    permission_classes = [IsAdmin]

    def post(self, request):
        amount = request.data.get('amount')
        business_id = request.data.get('business_id')
        rule_id = request.data.get('rule_id')

        if not amount:
            return api_response(
                'error', 'Amount is required',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        if rule_id:
            rule = CommissionRule.objects.filter(
                pk=rule_id
            ).first()
        elif business_id:
            from apps.marketplace.models import Business
            business = Business.objects.filter(
                pk=business_id
            ).first()
            if not business:
                return api_response(
                    'error', 'Business not found',
                    http_status=status.HTTP_404_NOT_FOUND
                )
            from .utils import get_commission_rule
            rule = get_commission_rule(business)
        else:
            rule = CommissionRule.objects.filter(
                rule_type='global',
                is_active=True
            ).first()

        if not rule:
            return api_response(
                'error', 'No commission rule found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        splits = rule.calculate(amount)
        return api_response(
            'success',
            'Commission simulated successfully',
            data={
                'rule': CommissionRuleSerializer(rule).data,
                'calculation': splits,
            }
        )


class CommissionListView(APIView):
    """List commissions"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role == 'admin':
            commissions = Commission.objects.all()
        else:
            # Vendors see their own commissions
            commissions = Commission.objects.filter(
                vendor=request.user
            )

        commission_status = request.query_params.get('status')
        business_id = request.query_params.get('business')
        from_date = request.query_params.get('from_date')
        to_date = request.query_params.get('to_date')

        if commission_status:
            commissions = commissions.filter(
                status=commission_status
            )
        if business_id:
            commissions = commissions.filter(
                business__id=business_id
            )
        if from_date:
            commissions = commissions.filter(
                created_at__date__gte=from_date
            )
        if to_date:
            commissions = commissions.filter(
                created_at__date__lte=to_date
            )

        # Summary
        total_gross = sum(
            c.gross_amount for c in commissions
        )
        total_platform = sum(
            c.platform_commission for c in commissions
        )
        total_vendor = sum(
            c.vendor_earnings for c in commissions
        )
        total_driver = sum(
            c.driver_earnings for c in commissions
        )

        serializer = CommissionSerializer(
            commissions, many=True
        )
        return api_response(
            'success',
            'Commissions retrieved successfully',
            data={
                'summary': {
                    'total_transactions': commissions.count(),
                    'total_gross': str(total_gross),
                    'total_platform': str(total_platform),
                    'total_vendor': str(total_vendor),
                    'total_driver': str(total_driver),
                },
                'count': commissions.count(),
                'results': serializer.data
            }
        )


class CommissionDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            if request.user.role == 'admin':
                commission = Commission.objects.get(pk=pk)
            else:
                commission = Commission.objects.get(
                    pk=pk, vendor=request.user
                )
        except Commission.DoesNotExist:
            return api_response(
                'error', 'Commission not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = CommissionSerializer(commission)
        return api_response(
            'success',
            'Commission retrieved successfully',
            data=serializer.data
        )


class BusinessCommissionView(APIView):
    """Get commissions for a specific business"""
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

        commissions = Commission.objects.filter(
            business=business
        )

        # Date filters
        from_date = request.query_params.get('from_date')
        to_date = request.query_params.get('to_date')
        if from_date:
            commissions = commissions.filter(
                created_at__date__gte=from_date
            )
        if to_date:
            commissions = commissions.filter(
                created_at__date__lte=to_date
            )

        total_gross = sum(c.gross_amount for c in commissions)
        total_earned = sum(c.vendor_earnings for c in commissions)
        total_platform = sum(
            c.platform_commission for c in commissions
        )

        serializer = CommissionSerializer(commissions, many=True)
        return api_response(
            'success',
            'Business commissions retrieved successfully',
            data={
                'summary': {
                    'total_orders': commissions.count(),
                    'total_gross_sales': str(total_gross),
                    'total_earned': str(total_earned),
                    'total_platform_commission': str(total_platform),
                    'effective_rate': str(
                        round(
                            (float(total_platform) /
                             float(total_gross) * 100)
                            if total_gross > 0 else 0,
                            2
                        )
                    ) + '%',
                },
                'count': commissions.count(),
                'results': serializer.data
            }
        )


class CommissionPayoutListView(APIView):
    """Manage payouts"""
    permission_classes = [IsAdmin]

    def get(self, request):
        payouts = CommissionPayout.objects.all()

        payout_status = request.query_params.get('status')
        payout_type = request.query_params.get('type')

        if payout_status:
            payouts = payouts.filter(status=payout_status)
        if payout_type:
            payouts = payouts.filter(payout_type=payout_type)

        serializer = CommissionPayoutSerializer(
            payouts, many=True
        )
        return api_response(
            'success',
            'Payouts retrieved successfully',
            data={
                'count': payouts.count(),
                'pending': payouts.filter(
                    status='pending'
                ).count(),
                'completed': payouts.filter(
                    status='completed'
                ).count(),
                'results': serializer.data
            }
        )

    def post(self, request):
        """Create payout for vendor or driver"""
        payout_type = request.data.get('payout_type')
        business_id = request.data.get('business_id')
        commission_ids = request.data.get('commission_ids', [])
        bank_name = request.data.get('bank_name', '')
        account_number = request.data.get('account_number', '')
        account_name = request.data.get('account_name', '')
        notes = request.data.get('notes', '')

        if not payout_type:
            return api_response(
                'error', 'payout_type is required',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        # Get commissions
        commissions = Commission.objects.filter(
            pk__in=commission_ids,
            status='confirmed'
        )

        if not commissions.exists():
            return api_response(
                'error', 'No confirmed commissions found',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        # Calculate total
        if payout_type == 'vendor':
            total = sum(c.vendor_earnings for c in commissions)
        else:
            total = sum(c.driver_earnings for c in commissions)

        # Fee (e.g bank transfer fee)
        fee = 50  # flat ₦50 transfer fee
        net = total - fee

        from apps.marketplace.models import Business
        business = Business.objects.filter(
            pk=business_id
        ).first()

        payout = CommissionPayout.objects.create(
            payout_type=payout_type,
            vendor=business.owner if business else None,
            business=business,
            total_amount=total,
            fee=fee,
            net_amount=net,
            bank_name=bank_name,
            account_number=account_number,
            account_name=account_name,
            reference=generate_reference('PAY'),
            notes=notes,
            processed_by=request.user,
        )
        payout.commissions.set(commissions)

        # Mark commissions as paid
        if payout_type == 'vendor':
            commissions.update(
                vendor_paid_at=timezone.now(),
                status='paid'
            )
        else:
            commissions.update(
                driver_paid_at=timezone.now(),
                status='paid'
            )

        return api_response(
            'success',
            'Payout created successfully',
            data=CommissionPayoutSerializer(payout).data,
            http_status=status.HTTP_201_CREATED
        )


class CommissionPayoutDetailView(APIView):
    permission_classes = [IsAdmin]

    def patch(self, request, pk):
        """Update payout status"""
        try:
            payout = CommissionPayout.objects.get(pk=pk)
        except CommissionPayout.DoesNotExist:
            return api_response(
                'error', 'Payout not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        new_status = request.data.get('status')
        gateway_ref = request.data.get('gateway_reference', '')

        if new_status:
            payout.status = new_status
        if gateway_ref:
            payout.gateway_reference = gateway_ref
        if new_status == 'completed':
            payout.processed_at = timezone.now()

        payout.save()

        return api_response(
            'success',
            'Payout updated successfully',
            data=CommissionPayoutSerializer(payout).data
        )


class CommissionDisputeListView(APIView):
    """Manage commission disputes"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role == 'admin':
            disputes = CommissionDispute.objects.all()
        else:
            disputes = CommissionDispute.objects.filter(
                raised_by=request.user
            )

        dispute_status = request.query_params.get('status')
        if dispute_status:
            disputes = disputes.filter(status=dispute_status)

        serializer = CommissionDisputeSerializer(
            disputes, many=True
        )
        return api_response(
            'success',
            'Disputes retrieved successfully',
            data={
                'count': disputes.count(),
                'results': serializer.data
            }
        )

    def post(self, request):
        """Raise a dispute"""
        commission_id = request.data.get('commission_id')
        reason = request.data.get('reason', '')
        expected_amount = request.data.get('expected_amount')

        try:
            commission = Commission.objects.get(
                pk=commission_id,
                vendor=request.user
            )
        except Commission.DoesNotExist:
            return api_response(
                'error', 'Commission not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        dispute = CommissionDispute.objects.create(
            commission=commission,
            raised_by=request.user,
            reason=reason,
            expected_amount=expected_amount,
        )

        # Notify admin
        from apps.notifications.utils import send_notification
        from django.contrib.auth import get_user_model
        User = get_user_model()
        admins = User.objects.filter(role='admin')
        for admin in admins:
            send_notification(
                user=admin,
                title='Commission Dispute Raised',
                message=f'{request.user.full_name} raised a dispute on commission {commission.reference}',
                notification_type='system'
            )

        serializer = CommissionDisputeSerializer(dispute)
        return api_response(
            'success',
            'Dispute raised successfully',
            data=serializer.data,
            http_status=status.HTTP_201_CREATED
        )


class ResolveDisputeView(APIView):
    """Admin resolves dispute"""
    permission_classes = [IsAdmin]

    def patch(self, request, pk):
        try:
            dispute = CommissionDispute.objects.get(pk=pk)
        except CommissionDispute.DoesNotExist:
            return api_response(
                'error', 'Dispute not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        new_status = request.data.get('status')
        resolution_notes = request.data.get('resolution_notes', '')

        if new_status not in ['resolved', 'rejected']:
            return api_response(
                'error', 'Status must be resolved or rejected',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        dispute.status = new_status
        dispute.resolved_by = request.user
        dispute.resolution_notes = resolution_notes
        dispute.resolved_at = timezone.now()
        dispute.save()

        # Notify vendor
        from apps.notifications.utils import send_notification
        send_notification(
            user=dispute.raised_by,
            title=f'Dispute {new_status.capitalize()}',
            message=f'Your dispute on commission {dispute.commission.reference} has been {new_status}. {resolution_notes}',
            notification_type='system'
        )

        serializer = CommissionDisputeSerializer(dispute)
        return api_response(
            'success',
            f'Dispute {new_status} successfully',
            data=serializer.data
        )


class PlatformRevenueView(APIView):
    """Admin platform revenue overview"""
    permission_classes = [IsAdmin]

    def get(self, request):
        commissions = Commission.objects.all()

        from_date = request.query_params.get('from_date')
        to_date = request.query_params.get('to_date')

        if from_date:
            commissions = commissions.filter(
                created_at__date__gte=from_date
            )
        if to_date:
            commissions = commissions.filter(
                created_at__date__lte=to_date
            )

        total_gross = sum(c.gross_amount for c in commissions)
        total_platform = sum(
            c.platform_commission for c in commissions
        )
        total_vendor = sum(c.vendor_earnings for c in commissions)
        total_driver = sum(c.driver_earnings for c in commissions)

        # By transaction type
        from collections import defaultdict
        by_type = defaultdict(lambda: {
            'count': 0, 'gross': 0, 'platform': 0
        })
        for c in commissions:
            by_type[c.transaction_type]['count'] += 1
            by_type[c.transaction_type]['gross'] += float(
                c.gross_amount
            )
            by_type[c.transaction_type]['platform'] += float(
                c.platform_commission
            )

        # Top businesses by revenue
        from django.db.models import Sum
        top_businesses = Commission.objects.values(
            'business__name'
        ).annotate(
            total=Sum('gross_amount')
        ).order_by('-total')[:10]

        return api_response(
            'success',
            'Platform revenue retrieved successfully',
            data={
                'summary': {
                    'total_transactions': commissions.count(),
                    'total_gross_volume': str(total_gross),
                    'total_platform_revenue': str(total_platform),
                    'total_vendor_payouts': str(total_vendor),
                    'total_driver_payouts': str(total_driver),
                    'average_commission_rate': str(
                        round(
                            float(total_platform) /
                            float(total_gross) * 100
                            if total_gross > 0 else 0,
                            2
                        )
                    ) + '%',
                },
                'by_transaction_type': dict(by_type),
                'top_businesses': list(top_businesses),
            }
        )


class CommissionAdjustmentView(APIView):
    """Create and manage commission adjustments"""
    permission_classes = [IsAdmin]

    def get(self, request, pk):
        """Get adjustments for a commission"""
        try:
            commission = Commission.objects.get(pk=pk)
        except Commission.DoesNotExist:
            return api_response(
                'error', 'Commission not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        adjustments = commission.adjustments.all()
        serializer = CommissionAdjustmentSerializer(
            adjustments, many=True
        )
        return api_response(
            'success',
            'Adjustments retrieved successfully',
            data=serializer.data
        )

    def post(self, request, pk):
        """Create adjustment for a commission"""
        try:
            commission = Commission.objects.get(pk=pk)
        except Commission.DoesNotExist:
            return api_response(
                'error', 'Commission not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        adjustment_type = request.data.get('adjustment_type')
        applies_to = request.data.get('applies_to', 'vendor')
        amount = request.data.get('amount', 0)
        reason = request.data.get('reason', '')
        notes = request.data.get('notes', '')

        from decimal import Decimal
        amount = Decimal(str(amount))

        # Calculate splits based on applies_to
        platform_adj = Decimal('0')
        vendor_adj = Decimal('0')
        driver_adj = Decimal('0')

        if applies_to == 'platform':
            platform_adj = amount
        elif applies_to == 'vendor':
            vendor_adj = amount
        elif applies_to == 'driver':
            driver_adj = amount
        elif applies_to == 'all':
            # Split equally
            each = round(amount / 3, 2)
            platform_adj = each
            vendor_adj = each
            driver_adj = amount - (each * 2)

        adjustment = CommissionAdjustment.objects.create(
            commission=commission,
            adjustment_type=adjustment_type,
            applies_to=applies_to,
            amount=amount,
            platform_adjustment=platform_adj,
            vendor_adjustment=vendor_adj,
            driver_adjustment=driver_adj,
            reason=reason,
            reference=generate_reference('ADJ'),
            requested_by=request.user,
            notes=notes,
        )

        serializer = CommissionAdjustmentSerializer(adjustment)
        return api_response(
            'success',
            'Adjustment created successfully',
            data=serializer.data,
            http_status=status.HTTP_201_CREATED
        )


class ApproveAdjustmentView(APIView):
    """Approve and apply an adjustment"""
    permission_classes = [IsAdmin]

    def post(self, request, pk, adj_id):
        try:
            commission = Commission.objects.get(pk=pk)
            adjustment = CommissionAdjustment.objects.get(
                pk=adj_id,
                commission=commission
            )
        except (Commission.DoesNotExist,
                CommissionAdjustment.DoesNotExist):
            return api_response(
                'error', 'Not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        if adjustment.is_approved:
            return api_response(
                'error',
                'Adjustment already approved',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        adjustment.is_approved = True
        adjustment.approved_by = request.user
        adjustment.approved_at = timezone.now()
        adjustment.save()

        # Apply the adjustment
        adjustment.apply()

        # Notify relevant parties
        from apps.notifications.utils import send_notification
        if commission.vendor:
            send_notification(
                user=commission.vendor,
                title='Commission Adjusted',
                message=f'A {adjustment.adjustment_type} adjustment of ₦{adjustment.amount} has been applied to commission {commission.reference}',
                notification_type='system'
            )

        serializer = CommissionAdjustmentSerializer(adjustment)
        return api_response(
            'success',
            'Adjustment approved and applied successfully',
            data=serializer.data
        )


class RefundCommissionView(APIView):
    """Process refund on a commission"""
    permission_classes = [IsAdmin]

    def post(self, request, pk):
        try:
            commission = Commission.objects.get(pk=pk)
        except Commission.DoesNotExist:
            return api_response(
                'error', 'Commission not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        if commission.refund_status == 'full':
            return api_response(
                'error',
                'Commission already fully refunded',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        refund_amount = request.data.get('amount')
        reason = request.data.get('reason', '')

        if not refund_amount:
            return api_response(
                'error',
                'Refund amount is required',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        commission.process_refund(refund_amount, reason)

        serializer = CommissionSerializer(commission)
        return api_response(
            'success',
            'Refund processed successfully',
            data=serializer.data
        )