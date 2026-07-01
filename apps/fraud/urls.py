from django.urls import path
from .views import (
    FraudDashboardView,
    FraudAlertListView,
    FraudAlertDetailView,
    BlockedEntityListView,
    UnblockEntityView,
    FraudRuleListView,
    FraudScoreListView,
    UserFraudScoreView,
    FraudEventListView,
    DeviceFingerprintListView,
    DeviceFingerprintDetailView,
    FraudActionLogListView,
    ChargebackListCreateView,
    ChargebackDetailView,
    WhitelistListCreateView,
    WhitelistDetailView,
    VelocityTrackingListView,
    RuleConditionListCreateView,
    BlacklistHistoryListView,
)

urlpatterns = [
    # Dashboard
    path(
        'dashboard/',
        FraudDashboardView.as_view(),
        name='fraud_dashboard'
    ),

    # Alerts
    path(
        'alerts/',
        FraudAlertListView.as_view(),
        name='fraud_alerts'
    ),
    path(
        'alerts/<int:pk>/',
        FraudAlertDetailView.as_view(),
        name='fraud_alert_detail'
    ),

    # Scores
    path(
        'scores/',
        FraudScoreListView.as_view(),
        name='fraud_scores'
    ),
    path(
        'scores/user/<int:user_id>/',
        UserFraudScoreView.as_view(),
        name='user_fraud_score'
    ),

    # Events
    path(
        'events/',
        FraudEventListView.as_view(),
        name='fraud_events'
    ),

    # Devices
    path(
        'devices/',
        DeviceFingerprintListView.as_view(),
        name='device_fingerprints'
    ),
    path(
        'devices/<int:pk>/',
        DeviceFingerprintDetailView.as_view(),
        name='device_fingerprint_detail'
    ),

    # Action logs
    path(
        'action-logs/',
        FraudActionLogListView.as_view(),
        name='fraud_action_logs'
    ),

    # Chargebacks
    path(
        'chargebacks/',
        ChargebackListCreateView.as_view(),
        name='chargebacks'
    ),
    path(
        'chargebacks/<int:pk>/',
        ChargebackDetailView.as_view(),
        name='chargeback_detail'
    ),

    # Whitelist
    path(
        'whitelist/',
        WhitelistListCreateView.as_view(),
        name='whitelist'
    ),
    path(
        'whitelist/<int:pk>/',
        WhitelistDetailView.as_view(),
        name='whitelist_detail'
    ),

    # Blocked entities
    path(
        'blocked/',
        BlockedEntityListView.as_view(),
        name='blocked_entities'
    ),
    path(
        'blocked/<int:pk>/unblock/',
        UnblockEntityView.as_view(),
        name='unblock_entity'
    ),
    path(
        'blocked/<int:entity_id>/history/',
        BlacklistHistoryListView.as_view(),
        name='blacklist_history'
    ),

    # Rules
    path(
        'rules/',
        FraudRuleListView.as_view(),
        name='fraud_rules'
    ),
    path(
        'rules/<int:rule_id>/conditions/',
        RuleConditionListCreateView.as_view(),
        name='rule_conditions'
    ),

    # Velocity
    path(
        'velocity/',
        VelocityTrackingListView.as_view(),
        name='velocity_tracking'
    ),
]