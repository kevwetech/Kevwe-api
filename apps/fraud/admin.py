from django.contrib import admin
from .models import (
    FraudRule, FraudAlert, FraudCase, BlockedEntity,
    FraudScore, FraudEvent, DeviceFingerprint,
    FraudActionLog, Chargeback, BlacklistHistory,
    RuleCondition, Whitelist, VelocityTracking,
)


@admin.register(FraudRule)
class FraudRuleAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'rule_type', 'score',
        'threshold', 'time_window_minutes', 'is_active'
    )
    list_filter = ('rule_type', 'is_active')
    search_fields = ('name',)


@admin.register(FraudAlert)
class FraudAlertAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'alert_type', 'risk_level',
        'risk_score', 'status', 'auto_blocked',
        'user', 'created_at'
    )
    list_filter = (
        'alert_type', 'risk_level',
        'status', 'auto_blocked'
    )
    search_fields = ('title', 'user__email')
    readonly_fields = (
        'created_at', 'updated_at',
        'reviewed_at', 'triggered_rules', 'metadata'
    )


@admin.register(FraudCase)
class FraudCaseAdmin(admin.ModelAdmin):
    list_display = (
        'reference', 'status',
        'total_risk_score', 'user', 'created_at'
    )
    list_filter = ('status',)
    search_fields = ('reference', 'user__email')


@admin.register(BlockedEntity)
class BlockedEntityAdmin(admin.ModelAdmin):
    list_display = (
        'entity_type', 'value', 'reason',
        'auto_blocked', 'is_active', 'created_at'
    )
    list_filter = ('entity_type', 'auto_blocked', 'is_active')
    search_fields = ('value', 'reason')


@admin.register(FraudScore)
class FraudScoreAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'event_type', 'event_score',
        'cumulative_score', 'risk_level', 'created_at'
    )
    list_filter = ('event_type', 'risk_level')
    search_fields = ('user__email',)


@admin.register(FraudEvent)
class FraudEventAdmin(admin.ModelAdmin):
    list_display = (
        'event_type', 'user', 'ip_address',
        'risk_score_added', 'created_at'
    )
    list_filter = ('event_type',)
    search_fields = ('user__email', 'ip_address')


@admin.register(DeviceFingerprint)
class DeviceFingerprintAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'browser', 'os', 'ip_address',
        'is_trusted', 'is_flagged',
        'seen_count', 'last_seen'
    )
    list_filter = ('is_trusted', 'is_flagged', 'device_type')
    search_fields = ('user__email', 'ip_address')


@admin.register(FraudActionLog)
class FraudActionLogAdmin(admin.ModelAdmin):
    list_display = (
        'action_type', 'performed_by', 'target_user',
        'is_system_action', 'created_at'
    )
    list_filter = ('action_type', 'is_system_action')
    search_fields = ('performed_by__email', 'target_user__email')


@admin.register(Chargeback)
class ChargebackAdmin(admin.ModelAdmin):
    list_display = (
        'reference', 'chargeback_type', 'status',
        'reason', 'amount', 'user', 'filed_at'
    )
    list_filter = (
        'chargeback_type', 'status', 'reason', 'gateway'
    )
    search_fields = (
        'reference', 'user__email', 'payment_reference'
    )


@admin.register(BlacklistHistory)
class BlacklistHistoryAdmin(admin.ModelAdmin):
    list_display = (
        'entity', 'action', 'performed_by',
        'is_system_action', 'created_at'
    )
    list_filter = ('action', 'is_system_action')


@admin.register(RuleCondition)
class RuleConditionAdmin(admin.ModelAdmin):
    list_display = (
        'rule', 'field', 'operator',
        'value', 'join_with_next', 'order'
    )
    list_filter = ('operator', 'join_with_next')


@admin.register(Whitelist)
class WhitelistAdmin(admin.ModelAdmin):
    list_display = (
        'entity_type', 'value', 'reason',
        'added_by', 'is_active', 'expires_at'
    )
    list_filter = ('entity_type', 'is_active')
    search_fields = ('value',)


@admin.register(VelocityTracking)
class VelocityTrackingAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'event_type', 'count_1hour',
        'count_24hour', 'is_throttled', 'last_event_at'
    )
    list_filter = ('event_type', 'is_throttled')
    search_fields = ('user__email',)