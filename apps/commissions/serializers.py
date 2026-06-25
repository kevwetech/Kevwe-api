from rest_framework import serializers
from .models import (
    CommissionRule,
    Commission,
    CommissionPayout,
    CommissionDispute,
    CommissionAdjustment
)


class CommissionRuleSerializer(serializers.ModelSerializer):
    industry_name = serializers.CharField(
        source='industry.name',
        read_only=True
    )
    business_name = serializers.CharField(
        source='business.name',
        read_only=True
    )
    created_by_name = serializers.CharField(
        source='created_by.full_name',
        read_only=True
    )

    class Meta:
        model = CommissionRule
        fields = (
            'id',
            'name',
            'rule_type',
            'calculation_type',
            'industry',
            'industry_name',
            'business',
            'business_name',
            'platform_rate',
            'vendor_rate',
            'driver_rate',
            'platform_fixed',
            'min_platform_commission',
            'max_platform_commission',
            'delivery_platform_rate',
            'delivery_driver_rate',
            'tiered_rates',
            'is_active',
            'notes',
            'created_by',
            'created_by_name',
            'created_at',
        )
        read_only_fields = ('id', 'created_by', 'created_at')


class CommissionSerializer(serializers.ModelSerializer):
    business_name = serializers.CharField(
        source='business.name',
        read_only=True
    )
    vendor_name = serializers.CharField(
        source='vendor.full_name',
        read_only=True
    )
    driver_name = serializers.CharField(
        source='driver.user.full_name',
        read_only=True
    )
    order_number = serializers.CharField(
        source='order.order_number',
        read_only=True
    )
    net_platform_revenue = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True
    )
    total_payouts = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True
    )

    class Meta:
        model = Commission
        fields = (
            'id',
            'rule',
            'business',
            'business_name',
            'vendor',
            'vendor_name',
            'driver',
            'driver_name',
            'transaction_type',
            'order',
            'order_number',
            'reference',
            'gross_amount',
            'delivery_fee',
            'platform_commission',
            'vendor_earnings',
            'driver_earnings',
            'platform_rate',
            'vendor_rate',
            'driver_rate',
            'net_platform_revenue',
            'total_payouts',
            'status',
            'vendor_paid_at',
            'driver_paid_at',
            'notes',
            'created_at',
        )
        read_only_fields = (
            'id',
            'reference',
            'net_platform_revenue',
            'total_payouts',
            'created_at',
        )


class CommissionAdjustmentSerializer(serializers.ModelSerializer):
    commission_reference = serializers.CharField(
        source='commission.reference',
        read_only=True
    )
    requested_by_name = serializers.CharField(
        source='requested_by.full_name',
        read_only=True
    )
    approved_by_name = serializers.CharField(
        source='approved_by.full_name',
        read_only=True
    )

    class Meta:
        model = CommissionAdjustment
        fields = (
            'id',
            'commission',
            'commission_reference',
            'adjustment_type',
            'applies_to',
            'amount',
            'platform_adjustment',
            'vendor_adjustment',
            'driver_adjustment',
            'reason',
            'reference',
            'requested_by',
            'requested_by_name',
            'approved_by',
            'approved_by_name',
            'approved_at',
            'is_approved',
            'is_applied',
            'applied_at',
            'notes',
            'created_at',
        )
        read_only_fields = (
            'id',
            'reference',
            'approved_by',
            'approved_at',
            'is_applied',
            'applied_at',
            'created_at',
        )

class CommissionPayoutSerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(
        source='vendor.full_name',
        read_only=True
    )
    driver_name = serializers.CharField(
        source='driver.user.full_name',
        read_only=True
    )
    business_name = serializers.CharField(
        source='business.name',
        read_only=True
    )
    processed_by_name = serializers.CharField(
        source='processed_by.full_name',
        read_only=True
    )

    class Meta:
        model = CommissionPayout
        fields = (
            'id',
            'payout_type',
            'vendor',
            'vendor_name',
            'driver',
            'driver_name',
            'business',
            'business_name',
            'commissions',
            'total_amount',
            'fee',
            'net_amount',
            'bank_name',
            'account_number',
            'account_name',
            'reference',
            'gateway_reference',
            'status',
            'processed_by',
            'processed_by_name',
            'processed_at',
            'notes',
            'created_at',
        )
        read_only_fields = (
            'id',
            'reference',
            'processed_at',
            'created_at',
        )


class CommissionDisputeSerializer(serializers.ModelSerializer):
    raised_by_name = serializers.CharField(
        source='raised_by.full_name',
        read_only=True
    )
    resolved_by_name = serializers.CharField(
        source='resolved_by.full_name',
        read_only=True
    )
    commission_reference = serializers.CharField(
        source='commission.reference',
        read_only=True
    )

    class Meta:
        model = CommissionDispute
        fields = (
            'id',
            'commission',
            'commission_reference',
            'raised_by',
            'raised_by_name',
            'reason',
            'expected_amount',
            'status',
            'resolved_by',
            'resolved_by_name',
            'resolution_notes',
            'resolved_at',
            'created_at',
        )
        read_only_fields = (
            'id',
            'raised_by',
            'status',
            'resolved_by',
            'resolved_at',
            'created_at',
        )