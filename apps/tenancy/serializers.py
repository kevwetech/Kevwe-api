from rest_framework import serializers
from .models import (
    Tenant,
    TenantMembership,
    TenantInvitation,
    TenantBranch,
    TenantBilling,
    CreditAccount, 
    CreditTransaction,
    APIKey, 
    Webhook, 
    WebhookEvent, 
    APIUsage,
    Feature, 
    TenantFeature, 
    TenantSetting,
    AuditLog, 
    ActivityFeed, 
    UsageMetric,
    CustomDomain,
)


class TenantSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(
        source='owner.full_name',
        read_only=True
    )
    owner_email = serializers.CharField(
        source='owner.email',
        read_only=True
    )
    plan_name = serializers.CharField(
        source='plan.name',
        read_only=True
    )
    country_name = serializers.CharField(
        source='country.name',
        read_only=True
    )
    state_name = serializers.CharField(
        source='state.name',
        read_only=True
    )
    city_name = serializers.CharField(
        source='city.name',
        read_only=True
    )
    total_users = serializers.IntegerField(read_only=True)
    total_branches = serializers.IntegerField(read_only=True)

    class Meta:
        model = Tenant
        fields = (
            'id',
            'name',
            'slug',
            'description',
            'industry',
            'status',
            'owner',
            'owner_name',
            'owner_email',
            'email',
            'phone',
            'website',
            'address',
            'country',
            'country_name',
            'state',
            'state_name',
            'city',
            'city_name',
            'logo',
            'favicon',
            'primary_color',
            'secondary_color',
            'accent_color',
            'custom_domain',
            'subdomain',
            'plan',
            'plan_name',
            'trial_ends_at',
            'subscription_ends_at',
            'max_users',
            'max_branches',
            'max_products',
            'max_orders_per_month',
            'enable_orders',
            'enable_bookings',
            'enable_deliveries',
            'enable_rides',
            'enable_shipments',
            'enable_wallet',
            'enable_subscriptions',
            'enable_pos',
            'api_key',
            'webhook_url',
            'is_active',
            'total_users',
            'total_branches',
            'created_at',
        )
        read_only_fields = (
            'id',
            'api_key',
            'total_users',
            'total_branches',
            'created_at',
        )


class TenantMembershipSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(
        source='user.full_name',
        read_only=True
    )
    user_email = serializers.CharField(
        source='user.email',
        read_only=True
    )
    user_phone = serializers.CharField(
        source='user.phone',
        read_only=True
    )
    tenant_name = serializers.CharField(
        source='tenant.name',
        read_only=True
    )

    class Meta:
        model = TenantMembership
        fields = (
            'id',
            'tenant',
            'tenant_name',
            'user',
            'user_name',
            'user_email',
            'user_phone',
            'role',
            'can_manage_users',
            'can_manage_products',
            'can_manage_orders',
            'can_manage_deliveries',
            'can_manage_finance',
            'can_view_reports',
            'can_manage_settings',
            'is_active',
            'joined_at',
            'created_at',
        )
        read_only_fields = (
            'id',
            'joined_at',
            'created_at',
        )


class TenantInvitationSerializer(serializers.ModelSerializer):
    tenant_name = serializers.CharField(
        source='tenant.name',
        read_only=True
    )
    invited_by_name = serializers.CharField(
        source='invited_by.full_name',
        read_only=True
    )
    is_expired = serializers.BooleanField(read_only=True)

    class Meta:
        model = TenantInvitation
        fields = (
            'id',
            'tenant',
            'tenant_name',
            'email',
            'role',
            'token',
            'status',
            'invited_by',
            'invited_by_name',
            'expires_at',
            'accepted_at',
            'is_expired',
            'created_at',
        )
        read_only_fields = (
            'id',
            'token',
            'status',
            'accepted_at',
            'created_at',
        )


class TenantBranchSerializer(serializers.ModelSerializer):
    tenant_name = serializers.CharField(
        source='tenant.name',
        read_only=True
    )
    branch_name = serializers.CharField(
        source='branch.name',
        read_only=True
    )
    branch_code = serializers.CharField(
        source='branch.code',
        read_only=True
    )

    class Meta:
        model = TenantBranch
        fields = (
            'id',
            'tenant',
            'tenant_name',
            'branch',
            'branch_name',
            'branch_code',
            'is_active',
            'is_primary',
            'created_at',
        )
        read_only_fields = ('id', 'created_at')


class TenantBillingSerializer(serializers.ModelSerializer):
    tenant_name = serializers.CharField(
        source='tenant.name',
        read_only=True
    )
    plan_name = serializers.CharField(
        source='plan.name',
        read_only=True
    )

    class Meta:
        model = TenantBilling
        fields = (
            'id',
            'tenant',
            'tenant_name',
            'plan',
            'plan_name',
            'amount',
            'currency',
            'status',
            'payment_reference',
            'billing_period_start',
            'billing_period_end',
            'description',
            'invoice_number',
            'created_at',
        )
        read_only_fields = (
            'id',
            'invoice_number',
            'created_at',
        )


class CreateTenantSerializer(serializers.Serializer):
    name = serializers.CharField()
    slug = serializers.SlugField()
    description = serializers.CharField(
        required=False,
        allow_blank=True
    )
    industry = serializers.ChoiceField(
        choices=[
            'ecommerce', 'logistics', 'hospitality',
            'ride_hailing', 'healthcare', 'education',
            'real_estate', 'food_delivery', 'retail', 'other'
        ],
        default='other'
    )
    email = serializers.EmailField()
    phone = serializers.CharField(
        required=False,
        allow_blank=True
    )
    website = serializers.URLField(required=False)
    address = serializers.CharField(
        required=False,
        allow_blank=True
    )
    country = serializers.IntegerField(required=False)
    state = serializers.IntegerField(required=False)
    city = serializers.IntegerField(required=False)
    plan_id = serializers.IntegerField(required=False)


class InviteMemberSerializer(serializers.Serializer):
    email = serializers.EmailField()
    role = serializers.ChoiceField(
        choices=['admin', 'manager', 'staff', 'viewer'],
        default='staff'
    )


class CreditAccountSerializer(serializers.ModelSerializer):
    tenant_name = serializers.CharField(
        source='tenant.name',
        read_only=True
    )

    class Meta:
        model = CreditAccount
        fields = (
            'id',
            'tenant',
            'tenant_name',
            'balance',
            'total_credited',
            'total_debited',
            'low_balance_threshold',
            'auto_topup',
            'auto_topup_amount',
            'is_active',
            'is_frozen',
            'created_at',
            'updated_at',
        )
        read_only_fields = (
            'id',
            'balance',
            'total_credited',
            'total_debited',
            'created_at',
            'updated_at',
        )


class CreditTransactionSerializer(serializers.ModelSerializer):
    tenant_name = serializers.CharField(
        source='credit_account.tenant.name',
        read_only=True
    )
    performed_by_name = serializers.CharField(
        source='performed_by.full_name',
        read_only=True
    )

    class Meta:
        model = CreditTransaction
        fields = (
            'id',
            'credit_account',
            'tenant_name',
            'transaction_type',
            'description_type',
            'amount',
            'balance_after',
            'description',
            'reference',
            'status',
            'metadata',
            'performed_by',
            'performed_by_name',
            'created_at',
        )
        read_only_fields = (
            'id',
            'balance_after',
            'created_at',
        ) 

class APIKeySerializer(serializers.ModelSerializer):
    tenant_name = serializers.CharField(
        source='tenant.name',
        read_only=True
    )
    created_by_name = serializers.CharField(
        source='created_by.full_name',
        read_only=True
    )
    # Never expose full key
    key_display = serializers.SerializerMethodField()

    class Meta:
        model = APIKey
        fields = (
            'id',
            'tenant',
            'tenant_name',
            'name',
            'description',
            'key_prefix',
            'last_four',
            'key_display',
            'can_read',
            'can_write',
            'can_delete',
            'allowed_endpoints',
            'rate_limit',
            'rate_limit_window',
            'status',
            'expires_at',
            'last_used_at',
            'total_requests',
            'created_by',
            'created_by_name',
            'created_at',
        )
        read_only_fields = (
            'id',
            'key_prefix',
            'last_four',
            'key_hash',
            'last_used_at',
            'total_requests',
            'created_at',
        )

    def get_key_display(self, obj):
        return f"{obj.key_prefix}...{obj.last_four}"


class WebhookSerializer(serializers.ModelSerializer):
    tenant_name = serializers.CharField(
        source='tenant.name',
        read_only=True
    )
    success_rate = serializers.SerializerMethodField()

    class Meta:
        model = Webhook
        fields = (
            'id',
            'tenant',
            'tenant_name',
            'name',
            'url',
            'description',
            'events',
            'status',
            'is_active',
            'total_deliveries',
            'successful_deliveries',
            'failed_deliveries',
            'success_rate',
            'last_triggered_at',
            'last_success_at',
            'last_failure_at',
            'created_at',
        )
        read_only_fields = (
            'id',
            'tenant',
            'secret',
            'total_deliveries',
            'successful_deliveries',
            'failed_deliveries',
            'last_triggered_at',
            'last_success_at',
            'last_failure_at',
            'created_at',
        )

    def get_success_rate(self, obj):
        if obj.total_deliveries == 0:
            return 100
        return round(
            (obj.successful_deliveries / obj.total_deliveries) * 100,
            2
        )


class WebhookEventSerializer(serializers.ModelSerializer):
    webhook_name = serializers.CharField(
        source='webhook.name',
        read_only=True
    )
    webhook_url = serializers.CharField(
        source='webhook.url',
        read_only=True
    )

    class Meta:
        model = WebhookEvent
        fields = (
            'id',
            'webhook',
            'webhook_name',
            'webhook_url',
            'tenant',
            'event_type',
            'payload',
            'status',
            'response_status_code',
            'response_body',
            'response_time_ms',
            'attempt_count',
            'max_attempts',
            'next_retry_at',
            'delivered_at',
            'error_message',
            'created_at',
        )
        read_only_fields = (
            'id',
            'created_at',
        )


class APIUsageSerializer(serializers.ModelSerializer):
    tenant_name = serializers.CharField(
        source='tenant.name',
        read_only=True
    )

    class Meta:
        model = APIUsage
        fields = (
            'id',
            'tenant',
            'tenant_name',
            'endpoint',
            'method',
            'status_code',
            'response_time_ms',
            'ip_address',
            'date',
            'hour',
            'created_at',
        )
        read_only_fields = ('id', 'created_at')

class FeatureSerializer(serializers.ModelSerializer):
    included_in_plans_names = serializers.SerializerMethodField()

    class Meta:
        model = Feature
        fields = (
            'id',
            'name',
            'slug',
            'description',
            'category',
            'icon',
            'pricing_type',
            'price_per_month',
            'price_per_use',
            'included_in_plans',
            'included_in_plans_names',
            'is_active',
            'is_beta',
            'order',
            'created_at',
        )
        read_only_fields = ('id', 'created_at')

    def get_included_in_plans_names(self, obj):
        return [
            plan.name
            for plan in obj.included_in_plans.all()
        ]


class TenantFeatureSerializer(serializers.ModelSerializer):
    feature_name = serializers.CharField(
        source='feature.name',
        read_only=True
    )
    feature_slug = serializers.CharField(
        source='feature.slug',
        read_only=True
    )
    feature_category = serializers.CharField(
        source='feature.category',
        read_only=True
    )
    feature_icon = serializers.CharField(
        source='feature.icon',
        read_only=True
    )
    tenant_name = serializers.CharField(
        source='tenant.name',
        read_only=True
    )
    is_active = serializers.BooleanField(read_only=True)
    enabled_by_name = serializers.CharField(
        source='enabled_by.full_name',
        read_only=True
    )

    class Meta:
        model = TenantFeature
        fields = (
            'id',
            'tenant',
            'tenant_name',
            'feature',
            'feature_name',
            'feature_slug',
            'feature_category',
            'feature_icon',
            'status',
            'custom_price',
            'usage_count',
            'usage_limit',
            'enabled_at',
            'expires_at',
            'config',
            'enabled_by',
            'enabled_by_name',
            'notes',
            'is_active',
            'created_at',
        )
        read_only_fields = (
            'id',
            'usage_count',
            'enabled_at',
            'created_at',
        )


class TenantSettingSerializer(serializers.ModelSerializer):
    tenant_name = serializers.CharField(
        source='tenant.name',
        read_only=True
    )
    typed_value = serializers.SerializerMethodField()

    class Meta:
        model = TenantSetting
        fields = (
            'id',
            'tenant',
            'tenant_name',
            'key',
            'value',
            'typed_value',
            'data_type',
            'category',
            'description',
            'is_public',
            'is_encrypted',
            'updated_by',
            'created_at',
            'updated_at',
        )
        read_only_fields = (
            'id',
            'typed_value',
            'created_at',
            'updated_at',
        )

    def get_typed_value(self, obj):
        if obj.is_encrypted:
            return '***encrypted***'
        return obj.get_value()

class AuditLogSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(
        source='user.full_name',
        read_only=True
    )
    user_email = serializers.CharField(
        source='user.email',
        read_only=True
    )
    tenant_name = serializers.CharField(
        source='tenant.name',
        read_only=True
    )

    class Meta:
        model = AuditLog
        fields = (
            'id',
            'tenant',
            'tenant_name',
            'user',
            'user_name',
            'user_email',
            'action',
            'severity',
            'description',
            'object_type',
            'object_id',
            'object_repr',
            'changes',
            'ip_address',
            'endpoint',
            'metadata',
            'created_at',
        )
        read_only_fields = ('id', 'created_at')


class ActivityFeedSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(
        source='user.full_name',
        read_only=True
    )
    user_avatar = serializers.ImageField(
        source='user.avatar',
        read_only=True
    )

    class Meta:
        model = ActivityFeed
        fields = (
            'id',
            'tenant',
            'user',
            'user_name',
            'user_avatar',
            'activity_type',
            'title',
            'description',
            'icon',
            'color',
            'object_type',
            'object_id',
            'object_url',
            'metadata',
            'is_read',
            'created_at',
        )
        read_only_fields = ('id', 'created_at')


class UsageMetricSerializer(serializers.ModelSerializer):
    tenant_name = serializers.CharField(
        source='tenant.name',
        read_only=True
    )
    success_rate = serializers.SerializerMethodField()

    class Meta:
        model = UsageMetric
        fields = (
            'id',
            'tenant',
            'tenant_name',
            'period',
            'period_start',
            'period_end',
            'date',
            'total_api_calls',
            'successful_api_calls',
            'failed_api_calls',
            'avg_response_time_ms',
            'success_rate',
            'total_orders',
            'total_deliveries',
            'total_shipments',
            'total_rides',
            'total_bookings',
            'total_revenue',
            'total_payments',
            'successful_payments',
            'failed_payments',
            'active_users',
            'new_users',
            'credits_used',
            'credits_added',
            'created_at',
        )
        read_only_fields = ('id', 'created_at')

    def get_success_rate(self, obj):
        if obj.total_api_calls == 0:
            return 100
        return round(
            (obj.successful_api_calls / obj.total_api_calls) * 100,
            2
        )


class CustomDomainSerializer(serializers.ModelSerializer):
    tenant_name = serializers.CharField(
        source='tenant.name',
        read_only=True
    )
    added_by_name = serializers.CharField(
        source='added_by.full_name',
        read_only=True
    )
    is_verified = serializers.BooleanField(read_only=True)
    is_ssl_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = CustomDomain
        fields = (
            'id',
            'tenant',
            'tenant_name',
            'domain',
            'domain_type',
            'is_primary',
            'status',
            'verification_token',
            'verification_method',
            'verified_at',
            'ssl_status',
            'ssl_issued_at',
            'ssl_expires_at',
            'dns_records',
            'redirect_to_primary',
            'force_https',
            'last_checked_at',
            'check_error',
            'added_by',
            'added_by_name',
            'notes',
            'is_verified',
            'is_ssl_active',
            'created_at',
        )
        read_only_fields = (
            'id',
            'verification_token',
            'verified_at',
            'ssl_issued_at',
            'ssl_expires_at',
            'dns_records',
            'last_checked_at',
            'check_error',
            'is_verified',
            'is_ssl_active',
            'created_at',
        )