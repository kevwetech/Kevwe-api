from django.contrib import admin
from .models import (
    Wallet,
    WalletTransaction,
    BankAccount,
    WithdrawalRequest,
    VendorWallet,
    VendorTransaction,
    VendorWithdrawalRequest,
    EarningsSummary,
)


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'balance', 'total_credited',
        'total_debited', 'is_active', 'is_pin_set',
        'created_at'
    )
    list_filter  = ('is_active', 'is_pin_set')
    search_fields = ('user__email', 'user__full_name')
    ordering      = ('-created_at',)
    readonly_fields = (
        'balance', 'total_credited',
        'total_debited', 'created_at'
    )


@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = (
        'wallet', 'transaction_type', 'category',
        'amount', 'balance_after', 'status',
        'reference', 'created_at'
    )
    list_filter  = (
        'transaction_type', 'category', 'status'
    )
    search_fields = (
        'wallet__user__email',
        'reference',
        'description'
    )
    ordering      = ('-created_at',)
    readonly_fields = (
        'wallet', 'amount', 'balance_after',
        'reference', 'created_at'
    )


@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'bank_name', 'account_number',
        'account_name', 'bank_code',
        'is_default', 'is_verified', 'created_at'
    )
    list_filter  = ('is_default', 'is_verified', 'bank_name')
    search_fields = (
        'user__email', 'account_number',
        'account_name', 'bank_name'
    )
    ordering      = ('-created_at',)
    readonly_fields = (
        'paystack_recipient_code', 'created_at'
    )


@admin.register(WithdrawalRequest)
class WithdrawalRequestAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'amount', 'fee', 'net_amount',
        'status', 'reference',
        'gateway_reference', 'created_at'
    )
    list_filter  = ('status',)
    search_fields = (
        'user__email', 'reference',
        'gateway_reference'
    )
    ordering      = ('-created_at',)
    readonly_fields = (
        'reference', 'gateway_reference', 'created_at'
    )


@admin.register(VendorWallet)
class VendorWalletAdmin(admin.ModelAdmin):
    list_display = (
        'business', 'user',
        'available_balance', 'pending_balance',
        'reserved_balance', 'total_earned',
        'total_withdrawn', 'status', 'created_at'
    )
    list_filter  = ('status',)
    search_fields = (
        'business__name', 'user__email'
    )
    ordering      = ('-created_at',)
    readonly_fields = (
        'available_balance', 'pending_balance',
        'reserved_balance', 'total_earned',
        'total_withdrawn', 'total_refunded',
        'created_at'
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'business', 'user'
        )


@admin.register(VendorTransaction)
class VendorTransactionAdmin(admin.ModelAdmin):
    list_display = (
        'vendor_wallet', 'transaction_type',
        'amount', 'available_balance_after',
        'pending_balance_after', 'status',
        'reference', 'created_at'
    )
    list_filter  = ('transaction_type', 'status')
    search_fields = (
        'vendor_wallet__business__name',
        'reference', 'description'
    )
    ordering      = ('-created_at',)
    readonly_fields = (
        'vendor_wallet', 'amount',
        'available_balance_after',
        'pending_balance_after',
        'reference', 'settlement_due',
        'settled_at', 'created_at'
    )


@admin.register(VendorWithdrawalRequest)
class VendorWithdrawalRequestAdmin(admin.ModelAdmin):
    list_display = (
        'business', 'vendor', 'amount',
        'fee', 'net_amount', 'status',
        'gateway_reference', 'approved_by',
        'approved_at', 'completed_at', 'created_at'
    )
    list_filter  = ('status', 'rejection_reason')
    search_fields = (
        'business__name', 'vendor__email',
        'reference', 'gateway_reference'
    )
    ordering      = ('-created_at',)
    readonly_fields = (
        'reference', 'gateway_reference',
        'approved_by', 'approved_at',
        'reviewed_by', 'reviewed_at',
        'rejected_by', 'rejected_at',
        'processed_at', 'completed_at',
        'created_at'
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'business', 'vendor',
            'vendor_wallet', 'bank_account'
        )


@admin.register(EarningsSummary)
class EarningsSummaryAdmin(admin.ModelAdmin):
    list_display = (
        'vendor_wallet', 'period',
        'period_start', 'period_end',
        'gross_earnings', 'net_earnings',
        'final_earnings', 'total_withdrawn'
    )
    list_filter  = ('period',)
    search_fields = ('vendor_wallet__business__name',)
    ordering      = ('-period_start',)
    readonly_fields = (
        'gross_earnings', 'net_earnings',
        'final_earnings', 'total_withdrawn',
        'created_at'
    )