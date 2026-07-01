from rest_framework import serializers
from .models import (
    FraudRule, FraudAlert, FraudCase, BlockedEntity,
    FraudScore, FraudEvent, DeviceFingerprint,
    FraudActionLog, Chargeback, BlacklistHistory,
    RuleCondition, Whitelist, VelocityTracking,
)


class FraudRuleSerializer(serializers.ModelSerializer):
    conditions_count = serializers.SerializerMethodField()

    class Meta:
        model = FraudRule
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')

    def get_conditions_count(self, obj):
        return obj.conditions.count()


class RuleConditionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RuleCondition
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')


class BlockedEntitySerializer(serializers.ModelSerializer):
    blocked_by_name = serializers.CharField(
        source='blocked_by.full_name', read_only=True
    )

    class Meta:
        model = BlockedEntity
        fields = '__all__'
        read_only_fields = (
            'id', 'blocked_by', 'auto_blocked',
            'created_at', 'updated_at'
        )


class FraudAlertSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(
        source='user.email', read_only=True
    )
    reviewed_by_name = serializers.CharField(
        source='reviewed_by.full_name', read_only=True
    )

    class Meta:
        model = FraudAlert
        fields = '__all__'
        read_only_fields = (
            'id', 'created_at', 'updated_at', 'auto_blocked'
        )


class FraudCaseSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(
        source='user.email', read_only=True
    )
    assigned_to_name = serializers.CharField(
        source='assigned_to.full_name', read_only=True
    )
    alerts_count = serializers.SerializerMethodField()

    class Meta:
        model = FraudCase
        fields = '__all__'
        read_only_fields = (
            'id', 'reference', 'created_at', 'updated_at'
        )

    def get_alerts_count(self, obj):
        return obj.alerts.count()


class FraudScoreSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(
        source='user.email', read_only=True
    )

    class Meta:
        model = FraudScore
        fields = '__all__'
        read_only_fields = (
            'id', 'cumulative_score', 'risk_level',
            'created_at', 'updated_at'
        )


class FraudEventSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(
        source='user.email', read_only=True
    )

    class Meta:
        model = FraudEvent
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')


class DeviceFingerprintSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(
        source='user.email', read_only=True
    )

    class Meta:
        model = DeviceFingerprint
        fields = '__all__'
        read_only_fields = (
            'id', 'fingerprint_hash', 'first_seen',
            'last_seen', 'seen_count', 'created_at',
            'updated_at'
        )


class FraudActionLogSerializer(serializers.ModelSerializer):
    performed_by_name = serializers.CharField(
        source='performed_by.full_name', read_only=True
    )
    target_user_email = serializers.CharField(
        source='target_user.email', read_only=True
    )

    class Meta:
        model = FraudActionLog
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')


class ChargebackSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(
        source='user.email', read_only=True
    )
    resolved_by_name = serializers.CharField(
        source='resolved_by.full_name', read_only=True
    )
    order_number = serializers.CharField(
        source='order.order_number', read_only=True
    )

    class Meta:
        model = Chargeback
        fields = '__all__'
        read_only_fields = (
            'id', 'reference', 'filed_at',
            'created_at', 'updated_at'
        )


class BlacklistHistorySerializer(serializers.ModelSerializer):
    entity_type = serializers.CharField(
        source='entity.entity_type', read_only=True
    )
    entity_value = serializers.CharField(
        source='entity.value', read_only=True
    )
    performed_by_name = serializers.CharField(
        source='performed_by.full_name', read_only=True
    )

    class Meta:
        model = BlacklistHistory
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')


class WhitelistSerializer(serializers.ModelSerializer):
    added_by_name = serializers.CharField(
        source='added_by.full_name', read_only=True
    )

    class Meta:
        model = Whitelist
        fields = '__all__'
        read_only_fields = (
            'id', 'added_by', 'created_at', 'updated_at'
        )


class VelocityTrackingSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(
        source='user.email', read_only=True
    )

    class Meta:
        model = VelocityTracking
        fields = '__all__'
        read_only_fields = (
            'id', 'last_event_at', 'created_at', 'updated_at'
        )