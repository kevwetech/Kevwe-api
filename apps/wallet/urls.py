from django.urls import path
from .views import (
    WalletView,
    TopUpWalletView,
    VerifyTopUpView,
    PayWithWalletView,
    TransferView,
    BankAccountListCreateView,
    BankAccountDetailView,
    WithdrawalView,
    WithdrawalHistoryView,
    TransactionHistoryView,
    SetPinView,
    ChangePinView,
    AdminCreditWalletView,
    AdminDebitWalletView,
    AdminWithdrawalListView,
    VendorWalletView,
    VendorTransactionListView,
    VendorWithdrawalListCreateView,
    VendorWithdrawalDetailView,
    AdminVendorWithdrawalListView,
    AdminVendorWithdrawalActionView,
    VendorEarningsSummaryView,
    SettlePendingEarningsView,
    AdminResolveWithdrawalView
)

urlpatterns = [
    # Wallet
    path('', WalletView.as_view(), name='wallet'),
    path('topup/', TopUpWalletView.as_view(), name='topup'),
    path('topup/verify/', VerifyTopUpView.as_view(), name='verify_topup'),
    path('pay/', PayWithWalletView.as_view(), name='pay_with_wallet'),
    path('transfer/', TransferView.as_view(), name='transfer'),

    # Transactions
    path('transactions/', TransactionHistoryView.as_view(), name='transactions'),

    # Bank accounts
    path('banks/', BankAccountListCreateView.as_view(), name='bank_accounts'),
    path('banks/<int:pk>/', BankAccountDetailView.as_view(), name='bank_account_detail'),

    # Withdrawals
    path('withdraw/', WithdrawalView.as_view(), name='withdraw'),
    path('withdrawals/', WithdrawalHistoryView.as_view(), name='withdrawal_history'),

    # PIN
    path('pin/set/', SetPinView.as_view(), name='set_pin'),
    path('pin/change/', ChangePinView.as_view(), name='change_pin'),

    # Vendor wallet
    path('vendor/<int:business_id>/', VendorWalletView.as_view(), name='vendor_wallet'),
    path('vendor/<int:business_id>/transactions/', VendorTransactionListView.as_view(), name='vendor_transactions'),
    path('vendor/<int:business_id>/earnings/', VendorEarningsSummaryView.as_view(), name='vendor_earnings'),
    path('vendor/<int:business_id>/settle/', SettlePendingEarningsView.as_view(), name='settle_earnings'),

    # Vendor withdrawals
    path('vendor/<int:business_id>/withdrawals/', VendorWithdrawalListCreateView.as_view(), name='vendor_withdrawals'),
    path('vendor/<int:business_id>/withdrawals/<int:pk>/', VendorWithdrawalDetailView.as_view(), name='vendor_withdrawal_detail'),

    # Admin vendor withdrawals
    path('admin/vendor-withdrawals/', AdminVendorWithdrawalListView.as_view(), name='admin_vendor_withdrawals'),
    path('admin/vendor-withdrawals/<int:pk>/', AdminVendorWithdrawalActionView.as_view(), name='admin_vendor_withdrawal_action'),

    # Admin
    path('admin/credit/', AdminCreditWalletView.as_view(), name='admin_credit'),
    path('admin/debit/', AdminDebitWalletView.as_view(), name='admin_debit'),
    path('admin/withdrawals/', AdminWithdrawalListView.as_view(), name='admin_withdrawals'),
    path('admin/withdrawals/<int:pk>/', AdminWithdrawalListView.as_view(), name='admin_withdrawal_update'),
    path(
        'admin/vendor-withdrawals/<int:pk>/resolve/',
        AdminResolveWithdrawalView.as_view(),
        name='admin_resolve_withdrawal'
    ),
]