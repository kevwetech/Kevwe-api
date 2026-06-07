from django.urls import path
from .views import (
    TenantListCreateView,
    TenantDetailView,
    RegenerateAPIKeyView,
    TenantMemberListView,
    InviteMemberView,
    AcceptInvitationView,
    RemoveMemberView,
    TenantBranchListView,
    TenantBillingListView,
    TenantDashboardView,
    AdminTenantListView,
    AdminTenantUpdateView,
    CreditAccountView,
    CreditTopUpView,
    ConfirmCreditTopUpView,
    CreditTransactionListView,
    AdminCreditView,
    APIKeyListCreateView,
    APIKeyDetailView,
    WebhookListCreateView,
    WebhookDetailView,
    WebhookEventListView,
    ResendWebhookEventView,
    APIUsageView,
    FeatureListCreateView,
    FeatureDetailView,
    TenantFeatureListView,
    EnableFeatureView,
    DisableFeatureView,
    TenantSettingListCreateView,
    TenantSettingDetailView,
    BulkTenantSettingsView,
    AuditLogListView,
    CreateAuditLogView,
    ActivityFeedView,
    CreateActivityView,
    UsageMetricView,
    CustomDomainListCreateView,
    CustomDomainDetailView,
    VerifyDomainView,
    SetPrimaryDomainView,
    RefreshSSLView,
    AdminDomainListView,
)

urlpatterns = [
    # Tenants
    path('', TenantListCreateView.as_view(), name='tenants'),
    path('<int:pk>/', TenantDetailView.as_view(), name='tenant_detail'),
    path('<int:pk>/dashboard/', TenantDashboardView.as_view(), name='tenant_dashboard'),
    path('<int:pk>/regenerate-keys/', RegenerateAPIKeyView.as_view(), name='regenerate_keys'),

    # Members
    path('<int:pk>/members/', TenantMemberListView.as_view(), name='tenant_members'),
    path('<int:pk>/invite/', InviteMemberView.as_view(), name='invite_member'),
    path('<int:pk>/members/<int:member_id>/remove/', RemoveMemberView.as_view(), name='remove_member'),
    path('accept-invitation/', AcceptInvitationView.as_view(), name='accept_invitation'),

    # Branches
    path('<int:pk>/branches/', TenantBranchListView.as_view(), name='tenant_branches'),

    # Billing
    path('<int:pk>/billing/', TenantBillingListView.as_view(), name='tenant_billing'),

    # Credit Account
    path('<int:pk>/credits/', CreditAccountView.as_view(), name='credit_account'),
    path('<int:pk>/credits/topup/', CreditTopUpView.as_view(), name='credit_topup'),
    path('<int:pk>/credits/confirm/', ConfirmCreditTopUpView.as_view(), name='confirm_credit_topup'),
    path('<int:pk>/credits/transactions/', CreditTransactionListView.as_view(), name='credit_transactions'),
    path('<int:pk>/credits/admin/', AdminCreditView.as_view(), name='admin_credit'),

    # API Keys
    path('<int:pk>/api-keys/', APIKeyListCreateView.as_view(), name='api_keys'),
    path('<int:pk>/api-keys/<int:key_id>/', APIKeyDetailView.as_view(), name='api_key_detail'),

    # Webhooks
    path('<int:pk>/webhooks/', WebhookListCreateView.as_view(), name='webhooks'),
    path('<int:pk>/webhooks/<int:webhook_id>/', WebhookDetailView.as_view(), name='webhook_detail'),
    path('<int:pk>/webhooks/<int:webhook_id>/events/', WebhookEventListView.as_view(), name='webhook_events'),
    path('<int:pk>/webhooks/<int:webhook_id>/events/<int:event_id>/resend/', ResendWebhookEventView.as_view(), name='resend_webhook_event'),

    # API Usage
    path('<int:pk>/api-usage/', APIUsageView.as_view(), name='api_usage'),

    # Features
    path('features/', FeatureListCreateView.as_view(), name='features'),
    path('features/<int:pk>/', FeatureDetailView.as_view(), name='feature_detail'),
    path('<int:pk>/features/', TenantFeatureListView.as_view(), name='tenant_features'),
    path('<int:pk>/features/enable/', EnableFeatureView.as_view(), name='enable_feature'),
    path('<int:pk>/features/<int:feature_id>/disable/', DisableFeatureView.as_view(), name='disable_feature'),

    # Settings
    path('<int:pk>/settings/', TenantSettingListCreateView.as_view(), name='tenant_settings'),
    path('<int:pk>/settings/bulk/', BulkTenantSettingsView.as_view(), name='bulk_settings'),
    path('<int:pk>/settings/<str:key>/', TenantSettingDetailView.as_view(), name='tenant_setting_detail'),

    # Audit Logs
    path('<int:pk>/audit-logs/', AuditLogListView.as_view(), name='audit_logs'),
    path('<int:pk>/audit-logs/create/', CreateAuditLogView.as_view(), name='create_audit_log'),

    # Activity Feed
    path('<int:pk>/activity/', ActivityFeedView.as_view(), name='activity_feed'),
    path('<int:pk>/activity/create/', CreateActivityView.as_view(), name='create_activity'),

    # Usage Metrics
    path('<int:pk>/metrics/', UsageMetricView.as_view(), name='usage_metrics'),

    # Custom Domains
    path('<int:pk>/domains/', CustomDomainListCreateView.as_view(), name='custom_domains'),
    path('<int:pk>/domains/<int:domain_id>/', CustomDomainDetailView.as_view(), name='custom_domain_detail'),
    path('<int:pk>/domains/<int:domain_id>/verify/', VerifyDomainView.as_view(), name='verify_domain'),
    path('<int:pk>/domains/<int:domain_id>/set-primary/', SetPrimaryDomainView.as_view(), name='set_primary_domain'),
    path('<int:pk>/domains/<int:domain_id>/refresh-ssl/', RefreshSSLView.as_view(), name='refresh_ssl'),

    # Admin
    path('admin/', AdminTenantListView.as_view(), name='admin_tenants'),
    path('admin/<int:pk>/', AdminTenantUpdateView.as_view(), name='admin_tenant_update'),
    path('admin/domains/', AdminDomainListView.as_view(), name='admin_domains'),
    path('admin/domains/<int:domain_id>/', AdminDomainListView.as_view(), name='admin_domain_update'),
]