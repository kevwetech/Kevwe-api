from django.contrib import admin
from .models import Wallet, WalletTransaction, BankAccount, WithdrawalRequest

@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'balance',
        'total_credited', 'total_debited',
        'is_active',
    )
    list_filter = ('is_active',)
    search_fields = ('user__email',)
    ordering = ('-created_at',)

@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = (
        'wallet', 'transaction_type',
        'amount', 'balance_after',
        'status', 'created_at'
    )
    list_filter = ('transaction_type', 'status')
    search_fields = ('wallet__user__email', 'reference')
    ordering = ('-created_at',)

@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'bank_name', 'account_number',
        'account_name', 'is_default', 'is_verified'
    )
    list_filter = ('is_default', 'is_verified')
    search_fields = ('user__email', 'account_number')
    ordering = ('-created_at',)

@admin.register(WithdrawalRequest)
class WithdrawalRequestAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'amount', 'fee',
        'net_amount', 'status', 'created_at'
    )
    list_filter = ('status',)
    search_fields = ('user__email', 'reference')
    ordering = ('-created_at',)