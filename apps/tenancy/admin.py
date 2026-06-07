from django.contrib import admin
from .models import (
    Tenant,
    TenantMembership,
    TenantInvitation,
    TenantBranch,
    TenantBilling,
    TenantAPILog,
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


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'slug', 'industry', 'status',
        'owner', 'plan', 'is_active', 'created_at'
    )
    list_filter = ('status', 'industry', 'is_active')
    search_fields = ('name', 'slug', 'email')
    ordering = ('-created_at',)


@admin.register(TenantMembership)
class TenantMembershipAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'tenant', 'role',
        'is_active', 'joined_at'
    )
    list_filter = ('role', 'is_active')
    search_fields = ('user__email', 'tenant__name')
    ordering = ('-created_at',)


@admin.register(TenantInvitation)
class TenantInvitationAdmin(admin.ModelAdmin):
    list_display = (
        'email', 'tenant', 'role',
        'status', 'expires_at'
    )
    list_filter = ('status', 'role')
    search_fields = ('email', 'tenant__name')
    ordering = ('-created_at',)


@admin.register(TenantBranch)
class TenantBranchAdmin(admin.ModelAdmin):
    list_display = (
        'tenant', 'branch',
        'is_primary', 'is_active'
    )
    list_filter = ('is_primary', 'is_active')
    ordering = ('-created_at',)


@admin.register(TenantBilling)
class TenantBillingAdmin(admin.ModelAdmin):
    list_display = (
        'tenant', 'plan', 'amount',
        'status', 'invoice_number', 'created_at'
    )
    list_filter = ('status',)
    search_fields = ('tenant__name', 'invoice_number')
    ordering = ('-created_at',)


@admin.register(TenantAPILog)
class TenantAPILogAdmin(admin.ModelAdmin):
    list_display = (
        'tenant', 'method', 'endpoint',
        'status_code', 'response_time', 'created_at'
    )
    list_filter = ('method', 'status_code')
    search_fields = ('tenant__name', 'endpoint')
    ordering = ('-created_at',)

@admin.register(CreditAccount)
class CreditAccountAdmin(admin.ModelAdmin):
    list_display = (
        'tenant', 'balance', 'total_credited',
        'total_debited', 'is_active', 'is_frozen'
    )
    list_filter = ('is_active', 'is_frozen')
    search_fields = ('tenant__name',)
    ordering = ('-created_at',)

@admin.register(CreditTransaction)
class CreditTransactionAdmin(admin.ModelAdmin):
    list_display = (
        'credit_account', 'transaction_type',
        'description_type', 'amount',
        'balance_after', 'status', 'created_at'
    )
    list_filter = ('transaction_type', 'description_type', 'status')
    search_fields = ('credit_account__tenant__name', 'reference')
    ordering = ('-created_at',)



@admin.register(Feature)
class FeatureAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'category', 'pricing_type',
        'price_per_month', 'is_active', 'is_beta'
    )
    list_filter = ('category', 'pricing_type', 'is_active', 'is_beta')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('order',)

@admin.register(TenantFeature)
class TenantFeatureAdmin(admin.ModelAdmin):
    list_display = (
        'tenant', 'feature', 'status',
        'usage_count', 'usage_limit',
        'expires_at'
    )
    list_filter = ('status',)
    search_fields = ('tenant__name', 'feature__name')
    ordering = ('-created_at',)

@admin.register(TenantSetting)
class TenantSettingAdmin(admin.ModelAdmin):
    list_display = (
        'tenant', 'key', 'data_type',
        'category', 'is_public', 'is_encrypted'
    )
    list_filter = ('data_type', 'category', 'is_public')
    search_fields = ('tenant__name', 'key')
    ordering = ('tenant', 'category', 'key')


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = (
        'action', 'severity', 'user',
        'tenant', 'object_type',
        'object_repr', 'created_at'
    )
    list_filter = ('action', 'severity')
    search_fields = (
        'user__email', 'tenant__name',
        'description', 'object_repr'
    )
    ordering = ('-created_at',)


@admin.register(ActivityFeed)
class ActivityFeedAdmin(admin.ModelAdmin):
    list_display = (
        'tenant', 'activity_type',
        'title', 'user', 'is_read',
        'created_at'
    )
    list_filter = ('activity_type', 'is_read')
    search_fields = ('tenant__name', 'title')
    ordering = ('-created_at',)


@admin.register(UsageMetric)
class UsageMetricAdmin(admin.ModelAdmin):
    list_display = (
        'tenant', 'period', 'date',
        'total_api_calls', 'total_revenue',
        'total_orders', 'total_deliveries'
    )
    list_filter = ('period', 'date')
    search_fields = ('tenant__name',)
    ordering = ('-date',)


@admin.register(CustomDomain)
class CustomDomainAdmin(admin.ModelAdmin):
    list_display = (
        'domain', 'tenant', 'domain_type',
        'status', 'ssl_status',
        'is_primary', 'verified_at'
    )
    list_filter = ('status', 'ssl_status', 'domain_type')
    search_fields = ('domain', 'tenant__name')
    ordering = ('-created_at',)