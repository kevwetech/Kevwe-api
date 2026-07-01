from rest_framework.views import APIView
from rest_framework import status
from apps.common.views import api_response
from apps.common.permissions import IsAdmin
from .serializers import (
    FraudAlertSerializer, FraudCaseSerializer,
    BlockedEntitySerializer, FraudRuleSerializer,
    FraudScoreSerializer, FraudEventSerializer,
    DeviceFingerprintSerializer, FraudActionLogSerializer,
    ChargebackSerializer, BlacklistHistorySerializer,
    RuleConditionSerializer, WhitelistSerializer,
    VelocityTrackingSerializer,
)
from .models import (
    FraudAlert, FraudCase, BlockedEntity, FraudRule,
    FraudScore, FraudEvent, DeviceFingerprint,
    FraudActionLog, Chargeback, BlacklistHistory,
    RuleCondition, Whitelist, VelocityTracking,
)
from django.utils import timezone


class FraudAlertListView(APIView):
    """
    GET  - List all fraud alerts (admin)
    GET /api/v1/fraud/alerts/?risk_level=high&status=open
    """
    permission_classes = [IsAdmin]

    def get(self, request):
        alerts = FraudAlert.objects.all()

        risk_level = request.query_params.get('risk_level')
        alert_status = request.query_params.get('status')
        alert_type = request.query_params.get('type')

        if risk_level:
            alerts = alerts.filter(risk_level=risk_level)
        if alert_status:
            alerts = alerts.filter(status=alert_status)
        if alert_type:
            alerts = alerts.filter(alert_type=alert_type)

        return api_response(
            'success',
            'Fraud alerts retrieved',
            data={
                'count': alerts.count(),
                'summary': {
                    'critical': alerts.filter(
                        risk_level='critical', status='open'
                    ).count(),
                    'high': alerts.filter(
                        risk_level='high', status='open'
                    ).count(),
                    'medium': alerts.filter(
                        risk_level='medium', status='open'
                    ).count(),
                    'total_open': alerts.filter(
                        status='open'
                    ).count(),
                },
                'results': FraudAlertSerializer(
                    alerts[:50], many=True
                ).data
            }
        )


class FraudAlertDetailView(APIView):
    """Review and resolve a fraud alert (admin)"""
    permission_classes = [IsAdmin]

    def get(self, request, pk):
        try:
            alert = FraudAlert.objects.get(pk=pk)
        except FraudAlert.DoesNotExist:
            return api_response(
                'error', 'Alert not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        return api_response(
            'success', 'Alert retrieved',
            data=FraudAlertSerializer(alert).data
        )

    def patch(self, request, pk):
        try:
            alert = FraudAlert.objects.get(pk=pk)
        except FraudAlert.DoesNotExist:
            return api_response(
                'error', 'Alert not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        new_status = request.data.get('status')
        notes = request.data.get('resolution_notes', '')

        if new_status not in [
            'reviewed', 'resolved', 'false_positive'
        ]:
            return api_response(
                'error',
                'Invalid status. Use: reviewed, resolved, '
                'false_positive',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        alert.status = new_status
        alert.reviewed_by = request.user
        alert.reviewed_at = timezone.now()
        alert.resolution_notes = notes
        alert.save()

        # If false positive and user was auto-blocked, unblock them
        if (
            new_status == 'false_positive'
            and alert.auto_blocked
            and alert.user
        ):
            alert.user.is_active = True
            alert.user.save()
            BlockedEntity.objects.filter(
                entity_type='user',
                value=str(alert.user.id)
            ).update(is_active=False)

        return api_response(
            'success', 'Alert updated',
            data=FraudAlertSerializer(alert).data
        )


class BlockedEntityListView(APIView):
    """
    GET  - List blocked entities (admin)
    POST - Manually block an entity (admin)
    """
    permission_classes = [IsAdmin]

    def get(self, request):
        entities = BlockedEntity.objects.filter(is_active=True)
        entity_type = request.query_params.get('type')
        if entity_type:
            entities = entities.filter(entity_type=entity_type)
        return api_response(
            'success', 'Blocked entities retrieved',
            data={
                'count': entities.count(),
                'results': BlockedEntitySerializer(
                    entities, many=True
                ).data
            }
        )

    def post(self, request):
        serializer = BlockedEntitySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(
                blocked_by=request.user,
                auto_blocked=False
            )
            return api_response(
                'success', 'Entity blocked successfully',
                data=serializer.data,
                http_status=status.HTTP_201_CREATED
            )
        return api_response(
            'error', 'Invalid data',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class UnblockEntityView(APIView):
    """Unblock a blocked entity (admin)"""
    permission_classes = [IsAdmin]

    def post(self, request, pk):
        try:
            entity = BlockedEntity.objects.get(pk=pk)
        except BlockedEntity.DoesNotExist:
            return api_response(
                'error', 'Entity not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        entity.is_active = False
        entity.save()

        # If it's a user, re-activate them
        if entity.entity_type == 'user':
            try:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                user = User.objects.get(id=int(entity.value))
                user.is_active = True
                user.save()
            except Exception as e:
                print(f"User reactivation error: {e}")

        return api_response(
            'success',
            f'{entity.entity_type} {entity.value} unblocked'
        )


class FraudRuleListView(APIView):
    """
    GET  - List fraud rules (admin)
    POST - Create fraud rule (admin)
    """
    permission_classes = [IsAdmin]

    def get(self, request):
        rules = FraudRule.objects.filter(is_active=True)
        return api_response(
            'success', 'Fraud rules retrieved',
            data={
                'count': rules.count(),
                'results': FraudRuleSerializer(
                    rules, many=True
                ).data
            }
        )

    def post(self, request):
        serializer = FraudRuleSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success', 'Rule created',
                data=serializer.data,
                http_status=status.HTTP_201_CREATED
            )
        return api_response(
            'error', 'Invalid data',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class FraudDashboardView(APIView):
    """
    Admin fraud overview dashboard.
    GET /api/v1/fraud/dashboard/
    """
    permission_classes = [IsAdmin]

    def get(self, request):
        from datetime import timedelta
        from django.utils import timezone

        now = timezone.now()
        today = now.replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        this_week = now - timedelta(days=7)
        this_month = now.replace(day=1)

        alerts = FraudAlert.objects.all()
        blocked = BlockedEntity.objects.filter(is_active=True)

        return api_response(
            'success', 'Fraud dashboard retrieved',
            data={
                'alerts': {
                    'total': alerts.count(),
                    'open': alerts.filter(
                        status='open'
                    ).count(),
                    'critical_open': alerts.filter(
                        risk_level='critical',
                        status='open'
                    ).count(),
                    'high_open': alerts.filter(
                        risk_level='high',
                        status='open'
                    ).count(),
                    'today': alerts.filter(
                        created_at__gte=today
                    ).count(),
                    'this_week': alerts.filter(
                        created_at__gte=this_week
                    ).count(),
                    'this_month': alerts.filter(
                        created_at__gte=this_month
                    ).count(),
                    'auto_blocked': alerts.filter(
                        auto_blocked=True
                    ).count(),
                },
                'blocked_entities': {
                    'total': blocked.count(),
                    'users': blocked.filter(
                        entity_type='user'
                    ).count(),
                    'ips': blocked.filter(
                        entity_type='ip'
                    ).count(),
                    'emails': blocked.filter(
                        entity_type='email'
                    ).count(),
                    'phones': blocked.filter(
                        entity_type='phone'
                    ).count(),
                },
                'by_type': {
                    'payment': alerts.filter(
                        alert_type='payment'
                    ).count(),
                    'account': alerts.filter(
                        alert_type='account'
                    ).count(),
                    'order': alerts.filter(
                        alert_type='order'
                    ).count(),
                },
            }
        )



class FraudScoreListView(APIView):
    """
    GET - List fraud scores (admin)
    GET /api/v1/fraud/scores/?user_id=2&risk_level=high
    """
    permission_classes = [IsAdmin]

    def get(self, request):
        scores = FraudScore.objects.all()
        user_id = request.query_params.get('user_id')
        risk_level = request.query_params.get('risk_level')
        event_type = request.query_params.get('event_type')

        if user_id:
            scores = scores.filter(user__id=user_id)
        if risk_level:
            scores = scores.filter(risk_level=risk_level)
        if event_type:
            scores = scores.filter(event_type=event_type)

        return api_response(
            'success', 'Fraud scores retrieved',
            data={
                'count': scores.count(),
                'results': FraudScoreSerializer(
                    scores[:100], many=True
                ).data
            }
        )


class UserFraudScoreView(APIView):
    """
    GET - Get cumulative fraud score for a specific user (admin)
    GET /api/v1/fraud/scores/user/<user_id>/
    """
    permission_classes = [IsAdmin]

    def get(self, request, user_id):
        from django.contrib.auth import get_user_model
        User = get_user_model()

        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return api_response(
                'error', 'User not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        scores = FraudScore.objects.filter(user=user)
        latest = scores.order_by('-created_at').first()
        alerts = FraudAlert.objects.filter(user=user)
        events = FraudEvent.objects.filter(user=user)

        return api_response(
            'success', f'Fraud profile for {user.email}',
            data={
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'is_active': user.is_active,
                    'date_joined': user.date_joined,
                },
                'cumulative_score': (
                    latest.cumulative_score if latest else 0
                ),
                'risk_level': (
                    latest.risk_level if latest else 'low'
                ),
                'total_alerts': alerts.count(),
                'open_alerts': alerts.filter(
                    status='open'
                ).count(),
                'total_events': events.count(),
                'is_blocked': not user.is_active,
                'recent_scores': FraudScoreSerializer(
                    scores[:10], many=True
                ).data,
            }
        )


class FraudEventListView(APIView):
    """GET - List fraud events (admin)"""
    permission_classes = [IsAdmin]

    def get(self, request):
        events = FraudEvent.objects.all()
        user_id = request.query_params.get('user_id')
        event_type = request.query_params.get('event_type')

        if user_id:
            events = events.filter(user__id=user_id)
        if event_type:
            events = events.filter(event_type=event_type)

        return api_response(
            'success', 'Fraud events retrieved',
            data={
                'count': events.count(),
                'results': FraudEventSerializer(
                    events[:100], many=True
                ).data
            }
        )


class DeviceFingerprintListView(APIView):
    """
    GET - List device fingerprints (admin)
    GET /api/v1/fraud/devices/?user_id=2&is_flagged=true
    """
    permission_classes = [IsAdmin]

    def get(self, request):
        devices = DeviceFingerprint.objects.all()
        user_id = request.query_params.get('user_id')
        is_flagged = request.query_params.get('is_flagged')
        is_trusted = request.query_params.get('is_trusted')

        if user_id:
            devices = devices.filter(user__id=user_id)
        if is_flagged:
            devices = devices.filter(
                is_flagged=is_flagged == 'true'
            )
        if is_trusted:
            devices = devices.filter(
                is_trusted=is_trusted == 'true'
            )

        return api_response(
            'success', 'Device fingerprints retrieved',
            data={
                'count': devices.count(),
                'results': DeviceFingerprintSerializer(
                    devices[:100], many=True
                ).data
            }
        )


class DeviceFingerprintDetailView(APIView):
    """
    PATCH - Trust or flag a device (admin)
    PATCH /api/v1/fraud/devices/<pk>/
    Body: { "is_trusted": true } or { "is_flagged": true }
    """
    permission_classes = [IsAdmin]

    def patch(self, request, pk):
        try:
            device = DeviceFingerprint.objects.get(pk=pk)
        except DeviceFingerprint.DoesNotExist:
            return api_response(
                'error', 'Device not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        if 'is_trusted' in request.data:
            device.is_trusted = request.data['is_trusted']
        if 'is_flagged' in request.data:
            device.is_flagged = request.data['is_flagged']
            if request.data['is_flagged']:
                device.flagged_reason = request.data.get(
                    'reason', 'Manually flagged by admin'
                )

        device.save()

        return api_response(
            'success', 'Device updated',
            data=DeviceFingerprintSerializer(device).data
        )


class FraudActionLogListView(APIView):
    """GET - List fraud action logs (admin)"""
    permission_classes = [IsAdmin]

    def get(self, request):
        logs = FraudActionLog.objects.all()
        action_type = request.query_params.get('action_type')
        user_id = request.query_params.get('user_id')
        is_system = request.query_params.get('is_system')

        if action_type:
            logs = logs.filter(action_type=action_type)
        if user_id:
            logs = logs.filter(target_user__id=user_id)
        if is_system:
            logs = logs.filter(
                is_system_action=is_system == 'true'
            )

        return api_response(
            'success', 'Action logs retrieved',
            data={
                'count': logs.count(),
                'results': FraudActionLogSerializer(
                    logs[:100], many=True
                ).data
            }
        )


class ChargebackListCreateView(APIView):
    """
    GET  - List chargebacks (admin)
    POST - File a chargeback (customer or admin)
    """
    def get_permissions(self):
        if self.request.method == 'GET':
            return [IsAdmin()]
        return []

    def get(self, request):
        chargebacks = Chargeback.objects.all()
        cb_status = request.query_params.get('status')
        cb_type = request.query_params.get('type')
        user_id = request.query_params.get('user_id')

        if cb_status:
            chargebacks = chargebacks.filter(status=cb_status)
        if cb_type:
            chargebacks = chargebacks.filter(
                chargeback_type=cb_type
            )
        if user_id:
            chargebacks = chargebacks.filter(user__id=user_id)

        return api_response(
            'success', 'Chargebacks retrieved',
            data={
                'count': chargebacks.count(),
                'results': ChargebackSerializer(
                    chargebacks, many=True
                ).data
            }
        )

    def post(self, request):
        from .utils import create_chargeback
        from apps.orders.models import Order

        amount = request.data.get('amount')
        reason = request.data.get('reason')
        description = request.data.get('description', '')
        order_id = request.data.get('order_id')
        payment_reference = request.data.get(
            'payment_reference', ''
        )

        if not amount or not reason:
            return api_response(
                'error', 'amount and reason are required',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        order = None
        if order_id:
            try:
                order = Order.objects.get(pk=order_id)
            except Order.DoesNotExist:
                pass

        chargeback = create_chargeback(
            user=request.user,
            amount=amount,
            reason=reason,
            description=description,
            order=order,
            payment_reference=payment_reference,
        )

        return api_response(
            'success',
            'Chargeback filed successfully',
            data=ChargebackSerializer(chargeback).data,
            http_status=status.HTTP_201_CREATED
        )


class ChargebackDetailView(APIView):
    """PATCH - Resolve a chargeback (admin)"""
    permission_classes = [IsAdmin]

    def patch(self, request, pk):
        try:
            chargeback = Chargeback.objects.get(pk=pk)
        except Chargeback.DoesNotExist:
            return api_response(
                'error', 'Chargeback not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        new_status = request.data.get('status')
        notes = request.data.get('resolution_notes', '')

        if new_status not in [
            'under_review', 'won', 'lost',
            'resolved', 'cancelled'
        ]:
            return api_response(
                'error', 'Invalid status',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        chargeback.status = new_status
        chargeback.resolution_notes = notes
        chargeback.resolved_by = request.user

        if new_status in ('won', 'lost', 'resolved'):
            chargeback.resolved_at = timezone.now()

        chargeback.save()

        from .utils import log_action
        log_action(
            action_type='chargeback_resolved',
            reason=f'Chargeback {chargeback.reference} '
                   f'resolved as {new_status}',
            performed_by=request.user,
            target_user=chargeback.user,
            metadata={
                'chargeback_id': chargeback.id,
                'new_status': new_status
            }
        )

        return api_response(
            'success', 'Chargeback updated',
            data=ChargebackSerializer(chargeback).data
        )


class WhitelistListCreateView(APIView):
    """
    GET  - List whitelisted entities (admin)
    POST - Add to whitelist (admin)
    """
    permission_classes = [IsAdmin]

    def get(self, request):
        entries = Whitelist.objects.filter(is_active=True)
        entity_type = request.query_params.get('type')
        if entity_type:
            entries = entries.filter(entity_type=entity_type)

        return api_response(
            'success', 'Whitelist retrieved',
            data={
                'count': entries.count(),
                'results': WhitelistSerializer(
                    entries, many=True
                ).data
            }
        )

    def post(self, request):
        serializer = WhitelistSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(added_by=request.user)

            from .utils import log_action
            log_action(
                action_type='whitelist_added',
                reason=request.data.get('reason', ''),
                performed_by=request.user,
                metadata={
                    'entity_type': request.data.get(
                        'entity_type'
                    ),
                    'value': request.data.get('value'),
                }
            )

            return api_response(
                'success', 'Added to whitelist',
                data=serializer.data,
                http_status=status.HTTP_201_CREATED
            )
        return api_response(
            'error', 'Invalid data',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class WhitelistDetailView(APIView):
    """DELETE - Remove from whitelist (admin)"""
    permission_classes = [IsAdmin]

    def delete(self, request, pk):
        try:
            entry = Whitelist.objects.get(pk=pk)
        except Whitelist.DoesNotExist:
            return api_response(
                'error', 'Entry not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        entry.is_active = False
        entry.save()

        return api_response(
            'success',
            f'{entry.entity_type} {entry.value} '
            f'removed from whitelist'
        )


class VelocityTrackingListView(APIView):
    """GET - List velocity tracking records (admin)"""
    permission_classes = [IsAdmin]

    def get(self, request):
        records = VelocityTracking.objects.all()
        event_type = request.query_params.get('event_type')
        is_throttled = request.query_params.get('is_throttled')
        user_id = request.query_params.get('user_id')

        if event_type:
            records = records.filter(event_type=event_type)
        if is_throttled:
            records = records.filter(
                is_throttled=is_throttled == 'true'
            )
        if user_id:
            records = records.filter(user__id=user_id)

        return api_response(
            'success', 'Velocity tracking retrieved',
            data={
                'count': records.count(),
                'results': VelocityTrackingSerializer(
                    records[:100], many=True
                ).data
            }
        )


class RuleConditionListCreateView(APIView):
    """
    GET  - List conditions for a rule (admin)
    POST - Add condition to a rule (admin)
    GET /api/v1/fraud/rules/<rule_id>/conditions/
    """
    permission_classes = [IsAdmin]

    def get(self, request, rule_id):
        try:
            rule = FraudRule.objects.get(pk=rule_id)
        except FraudRule.DoesNotExist:
            return api_response(
                'error', 'Rule not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        conditions = rule.conditions.all()
        return api_response(
            'success',
            f'Conditions for rule: {rule.name}',
            data={
                'rule': rule.name,
                'count': conditions.count(),
                'results': RuleConditionSerializer(
                    conditions, many=True
                ).data
            }
        )

    def post(self, request, rule_id):
        try:
            rule = FraudRule.objects.get(pk=rule_id)
        except FraudRule.DoesNotExist:
            return api_response(
                'error', 'Rule not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        data = request.data.copy()
        data['rule'] = rule.id
        serializer = RuleConditionSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success', 'Condition added',
                data=serializer.data,
                http_status=status.HTTP_201_CREATED
            )
        return api_response(
            'error', 'Invalid data',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class BlacklistHistoryListView(APIView):
    """GET - View blacklist history for an entity (admin)"""
    permission_classes = [IsAdmin]

    def get(self, request, entity_id):
        try:
            entity = BlockedEntity.objects.get(pk=entity_id)
        except BlockedEntity.DoesNotExist:
            return api_response(
                'error', 'Entity not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        history = entity.history.all()
        return api_response(
            'success',
            f'History for {entity.entity_type}: {entity.value}',
            data={
                'entity': BlockedEntitySerializer(entity).data,
                'count': history.count(),
                'results': BlacklistHistorySerializer(
                    history, many=True
                ).data
            }
        )