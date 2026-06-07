from django.urls import path
from .views import (
    PlanListView,
    PlanDetailView,
    AddPlanFeatureView,
    SubscribeView,
    MySubscriptionView,
    CancelSubscriptionView,
    UpgradeSubscriptionView,
    RenewSubscriptionView,
    SubscriptionHistoryView,
    AdminSubscriptionListView,
)

urlpatterns = [
    # Plans
    path('plans/', PlanListView.as_view(), name='plans'),
    path('plans/<int:pk>/', PlanDetailView.as_view(), name='plan_detail'),
    path('plans/<int:pk>/features/', AddPlanFeatureView.as_view(), name='plan_features'),

    # Subscriptions
    path('subscribe/', SubscribeView.as_view(), name='subscribe'),
    path('my-subscription/', MySubscriptionView.as_view(), name='my_subscription'),
    path('cancel/', CancelSubscriptionView.as_view(), name='cancel_subscription'),
    path('upgrade/', UpgradeSubscriptionView.as_view(), name='upgrade_subscription'),
    path('renew/', RenewSubscriptionView.as_view(), name='renew_subscription'),
    path('history/', SubscriptionHistoryView.as_view(), name='subscription_history'),

    # Admin
    path('admin/', AdminSubscriptionListView.as_view(), name='admin_subscriptions'),
]