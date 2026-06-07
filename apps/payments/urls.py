from django.urls import path
from .views import (
    InitializePaymentView,
    VerifyPaymentView,
    PaystackWebhookView,
    FlutterwaveWebhookView,
    RefundPaymentView,
    PaymentHistoryView,
    PaymentDetailView,
    AdminPaymentListView,
    GetBanksView,
    VerifyAccountView,
)

urlpatterns = [
    # Payment initialization
    path('initialize/', InitializePaymentView.as_view(), name='initialize_payment'),

    # Payment verification
    path('verify/', VerifyPaymentView.as_view(), name='verify_payment'),

    # Webhooks
    path('webhook/paystack/', PaystackWebhookView.as_view(), name='paystack_webhook'),
    path('webhook/flutterwave/', FlutterwaveWebhookView.as_view(), name='flutterwave_webhook'),

    # Refunds
    path('refund/', RefundPaymentView.as_view(), name='refund_payment'),

    # Payment history
    path('history/', PaymentHistoryView.as_view(), name='payment_history'),
    path('<int:pk>/', PaymentDetailView.as_view(), name='payment_detail'),

    # Admin
    path('admin/', AdminPaymentListView.as_view(), name='admin_payments'),

    # Bank utilities
    path('banks/', GetBanksView.as_view(), name='get_banks'),
    path('verify-account/', VerifyAccountView.as_view(), name='verify_account'),
]