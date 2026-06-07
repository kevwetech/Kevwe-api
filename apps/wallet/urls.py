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

    # Admin
    path('admin/credit/', AdminCreditWalletView.as_view(), name='admin_credit'),
    path('admin/debit/', AdminDebitWalletView.as_view(), name='admin_debit'),
    path('admin/withdrawals/', AdminWithdrawalListView.as_view(), name='admin_withdrawals'),
    path('admin/withdrawals/<int:pk>/', AdminWithdrawalListView.as_view(), name='admin_withdrawal_update'),
]