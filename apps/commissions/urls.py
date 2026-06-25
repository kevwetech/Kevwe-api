from django.urls import path
from .views import (
    CommissionRuleListCreateView,
    CommissionRuleDetailView,
    SimulateCommissionView,
    CommissionListView,
    CommissionDetailView,
    BusinessCommissionView,
    CommissionAdjustmentView,
    ApproveAdjustmentView,
    RefundCommissionView,
    CommissionPayoutListView,
    CommissionPayoutDetailView,
    CommissionDisputeListView,
    ResolveDisputeView,
    PlatformRevenueView,
)

urlpatterns = [
    # Rules
    path('rules/', CommissionRuleListCreateView.as_view(), name='commission_rules'),
    path('rules/<int:pk>/', CommissionRuleDetailView.as_view(), name='commission_rule_detail'),
    path('rules/simulate/', SimulateCommissionView.as_view(), name='simulate_commission'),

    # Commissions
    path('', CommissionListView.as_view(), name='commissions'),
    path('<int:pk>/', CommissionDetailView.as_view(), name='commission_detail'),
    path('business/<int:business_id>/', BusinessCommissionView.as_view(), name='business_commissions'),

    # Adjustments
    path('<int:pk>/adjustments/', CommissionAdjustmentView.as_view(), name='commission_adjustments'),
    path('<int:pk>/adjustments/<int:adj_id>/approve/', ApproveAdjustmentView.as_view(), name='approve_adjustment'),

    # Refunds
    path('<int:pk>/refund/', RefundCommissionView.as_view(), name='refund_commission'),

    # Payouts
    path('payouts/', CommissionPayoutListView.as_view(), name='payouts'),
    path('payouts/<int:pk>/', CommissionPayoutDetailView.as_view(), name='payout_detail'),

    # Disputes
    path('disputes/', CommissionDisputeListView.as_view(), name='disputes'),
    path('disputes/<int:pk>/resolve/', ResolveDisputeView.as_view(), name='resolve_dispute'),

    # Revenue
    path('revenue/', PlatformRevenueView.as_view(), name='platform_revenue'),
]