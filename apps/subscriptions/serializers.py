from rest_framework import serializers
from .models import Plan, PlanFeature, Subscription, SubscriptionHistory


class PlanFeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlanFeature
        fields = ('id', 'feature', 'is_included')


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
    payment_reference = serializers.CharField(
        required=False,
        allow_blank=True
    )
    gateway = serializers.ChoiceField(
        choices=['paystack', 'flutterwave'],
        required=False
    )


class UpgradeSerializer(serializers.Serializer):
    plan_id = serializers.IntegerField()
    payment_reference = serializers.CharField(
        required=False,
        allow_blank=True
    )