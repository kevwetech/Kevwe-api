from django.urls import path
from .views import (
    BusinessPlanListView,
    BusinessPlanDetailView,
    AdminBusinessPlanView,
    BusinessPlanFeatureView,
    BusinessSubscriptionView,
    SubscribeView,
    UpgradeDowngradeView,
    CancelSubscriptionView,
    SubscriptionHistoryView,
    SubscriptionPaymentHistoryView,
    AdminBusinessSubscriptionListView,
    AdminSuspendSubscriptionView,
    AdminReactivateSubscriptionView,
    AdminUpdateSubscriptionLimitsView,
    AdminUpdatePlanLimitsView,
)

urlpatterns = [
    # Public plans
    path('business/plans/', BusinessPlanListView.as_view(), name='business_plans'),
    path('business/plans/<int:pk>/', BusinessPlanDetailView.as_view(), name='business_plan_detail'),

    # Admin plan management
    path('business/plans/admin/', AdminBusinessPlanView.as_view(), name='admin_business_plans'),
    path('business/plans/admin/<int:pk>/', AdminBusinessPlanView.as_view(), name='admin_business_plan_update'),
    path('business/plans/<int:plan_id>/features/', BusinessPlanFeatureView.as_view(), name='plan_features'),
    path('business/plans/<int:plan_id>/features/<int:feature_id>/', BusinessPlanFeatureView.as_view(), name='plan_feature_delete'),

    # Business subscription management
    path('business/<int:business_id>/', BusinessSubscriptionView.as_view(), name='business_subscription'),
    path('business/<int:business_id>/subscribe/', SubscribeView.as_view(), name='business_subscribe'),
    path('business/<int:business_id>/upgrade/', UpgradeDowngradeView.as_view(), name='business_upgrade'),
    path('business/<int:business_id>/cancel/', CancelSubscriptionView.as_view(), name='business_cancel_subscription'),
    path('business/<int:business_id>/history/', SubscriptionHistoryView.as_view(), name='business_subscription_history'),
    path('business/<int:business_id>/payments/', SubscriptionPaymentHistoryView.as_view(), name='business_subscription_payments'),

    # Admin subscription management
    path('business/admin/all/', AdminBusinessSubscriptionListView.as_view(), name='admin_business_subscriptions'),
    path('business/admin/<int:business_id>/suspend/', AdminSuspendSubscriptionView.as_view(), name='admin_suspend_subscription'),
    path('business/admin/<int:business_id>/reactivate/', AdminReactivateSubscriptionView.as_view(), name='admin_reactivate_subscription'),
    path('business/admin/<int:business_id>/limits/', AdminUpdateSubscriptionLimitsView.as_view(), name='admin_update_limits'),
    path('business/plans/admin/<int:plan_id>/limits/', AdminUpdatePlanLimitsView.as_view(), name='admin_update_plan_limits'),
]