from rest_framework import serializers
from .models import (
    Plan,
    PlanFeature,
    Subscription,
    SubscriptionHistory,
    BusinessPlan,
    BusinessPlanFeature,
    BusinessSubscription,
    BusinessSubscriptionHistory,
    BusinessSubscriptionPayment,
)


# ─── User/Tenant Plan Serializers ─────────────────

class PlanFeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlanFeature
        fields = ('id', 'feature', 'is_included')
        read_only_fields = ('id',)


class PlanSerializer(serializers.ModelSerializer):
    features = PlanFeatureSerializer(many=True, read_only=True)
    subscriber_count = serializers.SerializerMethodField()

    class Meta:
        model = Plan
        fields = (
            'id',
            'name',
            'slug',
            'description',
            'price',
            'billing_cycle',
            'trial_days',
            'is_active',
            'is_featured',
            'max_products',
            'max_orders',
            'max_users',
            'max_storage_gb',
            'order',
            'features',
            'subscriber_count',
            'created_at',
        )
        read_only_fields = ('id', 'created_at')

    def get_subscriber_count(self, obj):
        return obj.subscriptions.filter(
            status__in=['active', 'trial']
        ).count()


class SubscriptionSerializer(serializers.ModelSerializer):
    plan_name = serializers.CharField(
        source='plan.name',
        read_only=True
    )
    plan_price = serializers.DecimalField(
        source='plan.price',
        max_digits=10,
        decimal_places=2,
        read_only=True
    )
    plan_billing_cycle = serializers.CharField(
        source='plan.billing_cycle',
        read_only=True
    )
    is_active = serializers.BooleanField(read_only=True)
    days_remaining = serializers.IntegerField(read_only=True)

    class Meta:
        model = Subscription
        fields = (
            'id',
            'plan',
            'plan_name',
            'plan_price',
            'plan_billing_cycle',
            'status',
            'start_date',
            'end_date',
            'trial_end_date',
            'cancelled_at',
            'payment_reference',
            'auto_renew',
            'is_active',
            'days_remaining',
            'created_at',
        )
        read_only_fields = (
            'id',
            'status',
            'start_date',
            'end_date',
            'trial_end_date',
            'cancelled_at',
            'created_at',
        )


class SubscriptionHistorySerializer(serializers.ModelSerializer):
    plan_name = serializers.CharField(
        source='plan.name',
        read_only=True
    )

    class Meta:
        model = SubscriptionHistory
        fields = (
            'id',
            'plan',
            'plan_name',
            'action',
            'amount',
            'payment_reference',
            'notes',
            'created_at',
        )
        read_only_fields = ('id', 'created_at')


class SubscribeSerializer(serializers.Serializer):
    plan_id = serializers.IntegerField()
    billing_cycle = serializers.ChoiceField(
        choices=['monthly', 'yearly'],
        default='monthly'
    )
    payment_method = serializers.ChoiceField(
        choices=['wallet', 'paystack', 'flutterwave'],
        default='wallet'
    )


class UpgradeSerializer(serializers.Serializer):
    plan_id = serializers.IntegerField()
    payment_reference = serializers.CharField(
        required=False,
        allow_blank=True
    )


class UpgradeDowngradeSerializer(serializers.Serializer):
    new_plan_id = serializers.IntegerField()
    billing_cycle = serializers.ChoiceField(
        choices=['monthly', 'yearly'],
        default='monthly'
    )
    payment_method = serializers.ChoiceField(
        choices=['wallet', 'paystack', 'flutterwave'],
        default='wallet'
    )


# ─── Business Plan Serializers ─────────────────────

class BusinessPlanFeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessPlanFeature
        fields = (
            'id',
            'plan',
            'name',
            'description',
            'feature_type',
            'limit_value',
            'icon',
            'is_highlight',
            'order',
            'created_at',
        )
        read_only_fields = ('id', 'created_at')


class BusinessPlanSerializer(serializers.ModelSerializer):
    yearly_savings = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True
    )
    is_free = serializers.BooleanField(read_only=True)
    plan_features = BusinessPlanFeatureSerializer(
        many=True,
        read_only=True
    )
    supported_industry_names = serializers.SerializerMethodField()

    class Meta:
        model = BusinessPlan
        fields = (
            'id',
            'name',
            'slug',
            'description',
            'plan_type',
            'monthly_price',
            'yearly_price',
            'yearly_savings',
            'commission_rate',
            'commission_discount',
            'allows_exclusive_bookings',
            'allows_slot_bookings',
            'allows_seat_bookings',
            'supported_industries',
            'supported_industry_names',
            'max_bookable_items',
            'max_monthly_bookings',
            'max_monthly_orders',
            'max_products',
            'max_staff',
            'grace_period_days',
            'trial_days',
            'features',
            'plan_features',
            'is_active',
            'is_featured',
            'is_public',
            'is_free',
            'order',
            'created_at',
        )
        read_only_fields = (
            'id',
            'yearly_savings',
            'is_free',
            'plan_features',
            'created_at',
        )

    def get_supported_industry_names(self, obj):
        return list(
            obj.supported_industries.values_list(
                'name', flat=True
            )
        )


class BusinessSubscriptionPaymentSerializer(
    serializers.ModelSerializer
):
    business_name = serializers.CharField(
        source='business.name',
        read_only=True
    )
    plan_name = serializers.CharField(
        source='plan.name',
        read_only=True
    )
    is_successful = serializers.BooleanField(read_only=True)

    class Meta:
        model = BusinessSubscriptionPayment
        fields = (
            'id',
            'subscription',
            'business',
            'business_name',
            'plan',
            'plan_name',
            'payment_type',
            'gateway',
            'billing_cycle',
            'amount',
            'discount_amount',
            'tax_amount',
            'net_amount',
            'currency',
            'reference',
            'gateway_reference',
            'period_start',
            'period_end',
            'status',
            'refunded_amount',
            'refunded_at',
            'refund_reason',
            'paid_at',
            'is_successful',
            'notes',
            'created_at',
        )
        read_only_fields = (
            'id',
            'reference',
            'is_successful',
            'created_at',
        )


class BusinessSubscriptionSerializer(
    serializers.ModelSerializer
):
    business_name = serializers.CharField(
        source='business.name',
        read_only=True
    )
    plan_name = serializers.CharField(
        source='plan.name',
        read_only=True
    )
    plan_type = serializers.CharField(
        source='plan.plan_type',
        read_only=True
    )
    is_active = serializers.BooleanField(read_only=True)
    is_on_trial = serializers.BooleanField(read_only=True)
    is_in_grace_period = serializers.BooleanField(
        read_only=True
    )
    days_remaining = serializers.IntegerField(read_only=True)
    grace_days_remaining = serializers.IntegerField(
        read_only=True
    )
    effective_commission_rate = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        read_only=True
    )
    plan_details = BusinessPlanSerializer(
        source='plan',
        read_only=True
    )
    suspended_by_name = serializers.CharField(
        source='suspended_by.full_name',
        read_only=True
    )

    class Meta:
        model = BusinessSubscription
        fields = (
            'id',
            'business',
            'business_name',
            'plan',
            'plan_name',
            'plan_type',
            'plan_details',
            'billing_cycle',
            'status',
            'start_date',
            'end_date',
            'trial_end_date',
            'grace_period_end',
            'next_billing_date',
            'last_renewed_at',
            'cancelled_at',
            'amount_paid',
            'payment_reference',
            'auto_renew',
            'commission_rate_override',
            'suspension_reason',
            'suspended_at',
            'suspended_by',
            'suspended_by_name',
            'current_products',
            'current_staff',
            'custom_max_products',
            'custom_max_staff',
            'custom_max_monthly_orders',
            'custom_max_monthly_bookings',
            'custom_max_bookable_items',
            'effective_limits',
            'current_monthly_orders',
            'current_monthly_bookings',
            'is_active',
            'is_on_trial',
            'is_in_grace_period',
            'days_remaining',
            'grace_days_remaining',
            'effective_commission_rate',
            'notes',
            'created_at',
        )
        read_only_fields = (
            'id',
            'is_active',
            'is_on_trial',
            'is_in_grace_period',
            'days_remaining',
            'grace_days_remaining',
            'effective_commission_rate',
            'current_products',
            'current_staff',
            'current_monthly_orders',
            'current_monthly_bookings',
            'suspended_at',
            'suspended_by',
            'created_at',
        )
        effective_limits = serializers.SerializerMethodField()

        def get_effective_limits(self, obj):
            return obj.effective_limits



class BusinessSubscriptionHistorySerializer(
    serializers.ModelSerializer
):
    business_name = serializers.CharField(
        source='business.name',
        read_only=True
    )
    plan_name = serializers.CharField(
        source='plan.name',
        read_only=True
    )
    previous_plan_name = serializers.CharField(
        source='previous_plan.name',
        read_only=True
    )

    class Meta:
        model = BusinessSubscriptionHistory
        fields = (
            'id',
            'business',
            'business_name',
            'plan',
            'plan_name',
            'previous_plan',
            'previous_plan_name',
            'action',
            'billing_cycle',
            'amount',
            'payment_reference',
            'notes',
            'created_at',
        )
        read_only_fields = ('id', 'created_at')