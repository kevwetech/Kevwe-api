from django.contrib import admin
from .models import (
    CommissionRule,
    Commission,
    CommissionPayout,
    CommissionDispute,
    CommissionAdjustment,
)


@admin.register(CommissionRule)
class CommissionRuleAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'rule_type', 'calculation_type',
        'platform_rate', 'vendor_rate', 'driver_rate',
        'is_active'
    )
    list_filter = ('rule_type', 'calculation_type', 'is_active')
    search_fields = ('name',)
    ordering = ('-created_at',)


@admin.register(Commission)
class CommissionAdmin(admin.ModelAdmin):
    list_display = (
        'reference', 'business', 'transaction_type',
        'gross_amount', 'platform_commission',
        'vendor_earnings', 'status', 'created_at'
    )
    list_filter = ('transaction_type', 'status')
    search_fields = ('reference', 'business__name')
    ordering = ('-created_at',)


@admin.register(CommissionPayout)
class CommissionPayoutAdmin(admin.ModelAdmin):
    list_display = (
        'reference', 'payout_type', 'business',
        'total_amount', 'net_amount',
        'status', 'created_at'
    )
    list_filter = ('payout_type', 'status')
    search_fields = ('reference', 'business__name')
    ordering = ('-created_at',)


@admin.register(CommissionDispute)
class CommissionDisputeAdmin(admin.ModelAdmin):
    list_display = (
        'commission', 'raised_by',
        'status', 'created_at'
    )
    list_filter = ('status',)
    search_fields = ('commission__reference',)
    ordering = ('-created_at',)

@admin.register(CommissionAdjustment)
class CommissionAdjustmentAdmin(admin.ModelAdmin):
    list_display = (
        'reference', 'commission', 'adjustment_type',
        'applies_to', 'amount', 'is_approved',
        'is_applied', 'created_at'
    )
    list_filter = (
        'adjustment_type', 'applies_to',
        'is_approved', 'is_applied'
    )
    search_fields = ('reference', 'commission__reference')
    ordering = ('-created_at',)