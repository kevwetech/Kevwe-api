import json
import hashlib
import hmac
import os
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from apps.common.views import api_response
from apps.common.permissions import IsAdmin
from apps.common.utils import generate_reference
from .models import Payment
from .serializers import (
    PaymentSerializer,
    InitializePaymentSerializer,
    VerifyPaymentSerializer,
    RefundPaymentSerializer,
)
from .utils import get_payment_amount, mark_as_paid
from . import paystack as paystack_gateway
from . import flutterwave as flutterwave_gateway


class InitializePaymentView(APIView):
    """Initialize payment with Paystack or Flutterwave"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = InitializePaymentSerializer(
            data=request.data
        )
        if not serializer.is_valid():
            return api_response(
                'error', 'Invalid data',
                errors=serializer.errors,
                http_status=status.HTTP_400_BAD_REQUEST
            )

        data        = serializer.validated_data
        payment_for = data['payment_for']
        object_id   = data['object_id']
        gateway     = data['gateway']

        # Get amount
        amount, obj_user = get_payment_amount(
            payment_for, object_id
        )
        if not amount:
            return api_response(
                'error', 'Invalid payment object',
                http_status=status.HTTP_404_NOT_FOUND
            )

        reference = generate_reference('PAY')

        # Create payment record
        payment = Payment.objects.create(
            user=request.user,
            reference=reference,
            gateway=gateway,
            status='pending',
            payment_for=payment_for,
            object_id=object_id,
            amount=amount,
            metadata={
                'payment_for': payment_for,
                'object_id': object_id,
                'type': payment_for,
            }
        )

        # Initialize with gateway
        if gateway == 'paystack':
            result = paystack_gateway.initialize_payment(
                email=request.user.email,
                amount=amount,
                reference=reference,
                callback_url=data.get('callback_url'),
                metadata={
                    'payment_id': payment.id,
                    'payment_for': payment_for,
                    'object_id': object_id,
                    'type': payment_for,
                }
            )
            if result.get('status'):
                return api_response(
                    'success',
                    'Payment initialized successfully',
                    data={
                        'payment_id': payment.id,
                        'reference': reference,
                        'gateway': gateway,
                        'amount': str(amount),
                        'currency': 'NGN',
                        'authorization_url': result['data']['authorization_url'],
                        'access_code': result['data']['access_code'],
                    }
                )

        elif gateway == 'flutterwave':
            result = flutterwave_gateway.initialize_payment(
                email=request.user.email,
                amount=amount,
                reference=reference,
                name=request.user.full_name,
                phone=getattr(request.user, 'phone', ''),
                callback_url=data.get('callback_url'),
                redirect_url=data.get('redirect_url'),
                metadata={
                    'payment_id': payment.id,
                    'payment_for': payment_for,
                    'object_id': object_id,
                    'type': payment_for,
                }
            )
            if result.get('status') == 'success':
                return api_response(
                    'success',
                    'Payment initialized successfully',
                    data={
                        'payment_id': payment.id,
                        'reference': reference,
                        'gateway': gateway,
                        'amount': str(amount),
                        'currency': 'NGN',
                        'payment_link': result['data']['link'],
                    }
                )

        # Gateway failed
        payment.status = 'failed'
        payment.failure_reason = str(result)
        payment.save()

        return api_response(
            'error', 'Payment initialization failed',
            http_status=status.HTTP_400_BAD_REQUEST
        )


class VerifyPaymentView(APIView):
    """Verify payment after completion"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = VerifyPaymentSerializer(data=request.data)
        if not serializer.is_valid():
            return api_response(
                'error', 'Invalid data',
                errors=serializer.errors,
                http_status=status.HTTP_400_BAD_REQUEST
            )

        reference      = serializer.validated_data['reference']
        gateway        = serializer.validated_data['gateway']
        transaction_id = serializer.validated_data.get(
            'transaction_id'
        )

        try:
            payment = Payment.objects.get(
                reference=reference,
                user=request.user
            )
        except Payment.DoesNotExist:
            return api_response(
                'error', 'Payment not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        if payment.status == 'success':
            return api_response(
                'success',
                'Payment already verified',
                data=PaymentSerializer(payment).data
            )

        verified = False

        if gateway == 'paystack':
            result = paystack_gateway.verify_payment(reference)
            if (result.get('status') and
                    result['data']['status'] == 'success'):
                verified = True
                payment.gateway_reference = str(
                    result['data']['id']
                )

        elif gateway == 'flutterwave':
            if transaction_id:
                result = flutterwave_gateway.verify_payment(
                    transaction_id
                )
            else:
                result = flutterwave_gateway.verify_payment_by_reference(
                    reference
                )

            if result.get('status') == 'success':
                data = result.get('data', {})
                if isinstance(data, list):
                    if not data:
                        return api_response(
                            'error',
                            'Payment not found. Please complete payment first.',
                            http_status=status.HTTP_400_BAD_REQUEST
                        )
                    data = data[0]
                if data.get('status') in ['successful', 'success']:
                    verified = True
                    payment.gateway_reference = str(
                        data.get('id', '')
                    )

        if verified:
            payment.status = 'success'
            payment.save()
            mark_as_paid(payment.payment_for, payment.object_id)
            return api_response(
                'success',
                'Payment verified successfully',
                data=PaymentSerializer(payment).data
            )

        payment.status = 'failed'
        payment.save()
        return api_response(
            'error', 'Payment verification failed',
            http_status=status.HTTP_400_BAD_REQUEST
        )


class PaystackWebhookView(APIView):
    """Handle Paystack webhook events"""
    permission_classes = [AllowAny]

    def post(self, request):
        # Verify signature
        paystack_signature = request.headers.get(
            'X-Paystack-Signature'
        )
        secret   = os.getenv('PAYSTACK_SECRET_KEY', '')
        computed = hmac.new(
            secret.encode('utf-8'),
            request.body,
            hashlib.sha512
        ).hexdigest()

        if not hmac.compare_digest(
            computed, paystack_signature or ''
        ):
            return api_response(
                'error', 'Invalid signature',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        payload  = json.loads(request.body)
        event    = payload.get('event')
        pdata    = payload.get('data', {})
        metadata = pdata.get('metadata', {})

        # ── Charge success ──────────────────────────
        if event == 'charge.success':
            reference    = pdata.get('reference')
            amount_kobo  = pdata.get('amount', 0)
            amount       = amount_kobo / 100
            payment_type = metadata.get('type')

            if payment_type == 'subscription':
                try:
                    from apps.subscriptions.webhook_handlers import (
                        handle_subscription_payment
                    )
                    success, message = handle_subscription_payment(
                        reference=reference,
                        gateway='paystack',
                        amount=amount,
                        gateway_response=pdata
                    )
                    print(f"Sub webhook Paystack: {message}")
                except Exception as e:
                    print(f"Sub webhook error: {e}")

            elif payment_type == 'wallet_topup':
                self._handle_wallet_topup(
                    reference=reference,
                    amount=amount,
                    metadata=metadata,
                    gateway='Paystack'
                )

            else:
                self._handle_regular_payment(
                    reference=reference,
                    gateway_reference=pdata.get('id')
                )

        # ── Charge failed ───────────────────────────
        elif event == 'charge.failed':
            reference    = pdata.get('reference')
            payment_type = metadata.get('type')

            if payment_type == 'subscription':
                try:
                    from apps.subscriptions.webhook_handlers import (
                        handle_subscription_payment_failed
                    )
                    handle_subscription_payment_failed(
                        reference=reference,
                        reason=pdata.get('gateway_response', '')
                    )
                except Exception as e:
                    print(f"Sub payment failed webhook error: {e}")

        # ── Transfer success ────────────────────────
        elif event == 'transfer.success':
            transfer_ref = pdata.get('reference')
            self._handle_transfer_success(
                transfer_ref, pdata
            )

        # ── Transfer failed ─────────────────────────
        elif event == 'transfer.failed':
            transfer_ref = pdata.get('reference')
            reason       = pdata.get(
                'reason', 'Transfer failed'
            )
            self._handle_transfer_failed(
                transfer_ref, reason
            )

        # ── Transfer reversed ───────────────────────
        elif event == 'transfer.reversed':
            transfer_ref = pdata.get('reference')
            self._handle_transfer_reversed(transfer_ref)

        # ── Refund processed ────────────────────────
        elif event == 'refund.processed':
            reference = pdata.get('transaction_reference')
            try:
                payment        = Payment.objects.get(
                    reference=reference
                )
                payment.status = 'refunded'
                payment.save()
            except Payment.DoesNotExist:
                pass

        return api_response('success', 'Webhook received')

    def _handle_wallet_topup(
        self, reference, amount, metadata, gateway
    ):
        from decimal import Decimal
        from apps.wallet.models import WalletTransaction
        from apps.wallet.utils import get_or_create_wallet
        from django.contrib.auth import get_user_model
        User = get_user_model()

        user_id = metadata.get('user_id')
        try:
            user   = User.objects.get(pk=user_id)
            wallet = get_or_create_wallet(user)

            already = WalletTransaction.objects.filter(
                reference=reference,
                status='success'
            ).exists()

            if not already:
                wallet.credit(
                    amount=Decimal(str(amount)),
                    description=f'Wallet top up via {gateway}',
                    reference=reference
                )
                WalletTransaction.objects.filter(
                    wallet=wallet,
                    reference=reference,
                    status='pending'
                ).update(
                    status='success',
                    balance_after=wallet.balance
                )

                from apps.notifications.utils import (
                    send_notification
                )
                send_notification(
                    user=user,
                    title='Wallet Topped Up! 🎉',
                    message=(
                        f'₦{amount} added to your wallet. '
                        f'New balance: ₦{wallet.balance}'
                    ),
                    notification_type='system',
                    data={
                        'amount': str(amount),
                        'balance': str(wallet.balance),
                    }
                )
        except Exception as e:
            print(f"Wallet topup error: {e}")

    def _handle_regular_payment(
        self, reference, gateway_reference=None
    ):
        try:
            payment = Payment.objects.get(
                reference=reference
            )
            if payment.status != 'success':
                payment.status = 'success'
                if gateway_reference:
                    payment.gateway_reference = str(
                        gateway_reference
                    )
                payment.save()
                mark_as_paid(
                    payment.payment_for,
                    payment.object_id
                )
        except Payment.DoesNotExist:
            pass

    def _handle_transfer_success(self, transfer_ref, data):
        """Auto complete withdrawal on transfer success"""
        from apps.wallet.models import VendorWithdrawalRequest
        from apps.notifications.utils import send_notification
        from django.utils import timezone

        try:
            withdrawal = VendorWithdrawalRequest.objects.get(
                gateway_reference=transfer_ref,
                status__in=['approved', 'processing']
            )
            withdrawal.status       = 'completed'
            withdrawal.completed_at = timezone.now()
            withdrawal.save()

            send_notification(
                user=withdrawal.vendor,
                title='Withdrawal Successful! 💰',
                message=(
                    f'₦{withdrawal.net_amount} has been sent '
                    f'to your '
                    f'{withdrawal.bank_account.bank_name} '
                    f'account ending '
                    f'{withdrawal.bank_account.account_number[-4:]}.'
                ),
                notification_type='system',
                data={
                    'withdrawal_id': withdrawal.id,
                    'amount': str(withdrawal.net_amount),
                    'status': 'completed',
                }
            )
        except VendorWithdrawalRequest.DoesNotExist:
            print(
                f"Transfer webhook: withdrawal not found "
                f"for {transfer_ref}"
            )
        except Exception as e:
            print(f"Transfer success webhook error: {e}")

    def _handle_transfer_failed(self, transfer_ref, reason):
        """Handle failed transfer — reverse the withdrawal"""
        from apps.wallet.models import (
            VendorWithdrawalRequest,
            VendorTransaction,
        )
        from apps.notifications.utils import send_notification
        from apps.common.utils import generate_reference
        from django.utils import timezone

        try:
            withdrawal = VendorWithdrawalRequest.objects.get(
                gateway_reference=transfer_ref,
                status__in=['approved', 'processing']
            )

            # Reverse — return amount to available balance
            wallet                   = withdrawal.vendor_wallet
            wallet.reserved_balance  -= withdrawal.amount
            wallet.available_balance += withdrawal.amount
            wallet.total_withdrawn   -= withdrawal.amount
            wallet.save()

            # Record reversal transaction
            VendorTransaction.objects.create(
                vendor_wallet=wallet,
                transaction_type='release',
                amount=withdrawal.amount,
                available_balance_after=wallet.available_balance,
                pending_balance_after=wallet.pending_balance,
                description=(
                    f'Transfer failed reversal - '
                    f'{withdrawal.reference}'
                ),
                reference=generate_reference('TREV'),
                status='success',
            )

            withdrawal.status         = 'failed'
            withdrawal.failure_reason = reason
            withdrawal.save()

            send_notification(
                user=withdrawal.vendor,
                title='Withdrawal Failed ❌',
                message=(
                    f'Your withdrawal of ₦{withdrawal.net_amount} '
                    f'failed. Reason: {reason}. '
                    f'Amount has been returned to your wallet. '
                    f'Please try again.'
                ),
                notification_type='system',
                data={
                    'withdrawal_id': withdrawal.id,
                    'amount': str(withdrawal.net_amount),
                    'reason': reason,
                }
            )
        except VendorWithdrawalRequest.DoesNotExist:
            print(
                f"Transfer webhook: withdrawal not found "
                f"for {transfer_ref}"
            )
        except Exception as e:
            print(f"Transfer failed webhook error: {e}")

    def _handle_transfer_reversed(self, transfer_ref):
        """Handle reversed transfer"""
        self._handle_transfer_failed(
            transfer_ref,
            'Transfer was reversed by the bank'
        )

class FlutterwaveWebhookView(APIView):
    """Handle Flutterwave webhook events"""
    permission_classes = [AllowAny]

    def post(self, request):
        # Verify signature
        signature = request.headers.get('verif-hash')
        secret    = os.getenv('FLUTTERWAVE_SECRET_KEY', '')

        if signature != secret:
            return api_response(
                'error', 'Invalid signature',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        payload = json.loads(request.body)
        event   = payload.get('event')

        # ── Charge completed ────────────────────────
        if event == 'charge.completed':
            data = payload.get('data', {})
            if data.get('status') == 'successful':
                reference    = data.get('tx_ref')
                amount       = data.get('amount')
                metadata     = data.get('meta', {})
                payment_type = metadata.get('type')

                if payment_type == 'subscription':
                    try:
                        from apps.subscriptions.webhook_handlers import (
                            handle_subscription_payment
                        )
                        success, message = handle_subscription_payment(
                            reference=reference,
                            gateway='flutterwave',
                            amount=amount,
                            gateway_response=data
                        )
                        print(
                            f"Sub webhook Flutterwave: {message}"
                        )
                    except Exception as e:
                        print(f"Sub webhook error: {e}")

                elif payment_type == 'wallet_topup':
                    self._handle_wallet_topup(
                        reference=reference,
                        amount=amount,
                        metadata=metadata,
                        gateway='Flutterwave'
                    )

                else:
                    self._handle_regular_payment(
                        reference=reference,
                        gateway_reference=data.get('id')
                    )

        # ── Charge failed ───────────────────────────
        elif event == 'charge.failed':
            data         = payload.get('data', {})
            reference    = data.get('tx_ref')
            metadata     = data.get('meta', {})
            payment_type = metadata.get('type')

            if payment_type == 'subscription':
                try:
                    from apps.subscriptions.webhook_handlers import (
                        handle_subscription_payment_failed
                    )
                    handle_subscription_payment_failed(
                        reference=reference,
                        reason=data.get(
                            'processor_response', ''
                        )
                    )
                except Exception as e:
                    print(f"Sub payment failed error: {e}")

        # ── Transfer completed ──────────────────────
        elif event == 'transfer.completed':
            data   = payload.get('data', {})
            status = data.get('status', '')
            ref    = data.get('reference')

            if status == 'SUCCESSFUL':
                self._handle_transfer_success(ref, data)
            elif status in ['FAILED', 'CANCELLED']:
                reason = data.get(
                    'complete_message',
                    'Transfer failed'
                )
                self._handle_transfer_failed(ref, reason)

        return api_response('success', 'Webhook received')

    def _handle_wallet_topup(
        self, reference, amount, metadata, gateway
    ):
        from decimal import Decimal
        from apps.wallet.models import WalletTransaction
        from apps.wallet.utils import get_or_create_wallet
        from django.contrib.auth import get_user_model
        User = get_user_model()

        user_id = metadata.get('user_id')
        try:
            user   = User.objects.get(pk=user_id)
            wallet = get_or_create_wallet(user)

            already = WalletTransaction.objects.filter(
                reference=reference,
                status='success'
            ).exists()

            if not already:
                wallet.credit(
                    amount=Decimal(str(amount)),
                    description=f'Wallet top up via {gateway}',
                    reference=reference
                )
                WalletTransaction.objects.filter(
                    wallet=wallet,
                    reference=reference,
                    status='pending'
                ).update(
                    status='success',
                    balance_after=wallet.balance
                )

                from apps.notifications.utils import (
                    send_notification
                )
                send_notification(
                    user=user,
                    title='Wallet Topped Up! 🎉',
                    message=(
                        f'₦{amount} added to your wallet. '
                        f'New balance: ₦{wallet.balance}'
                    ),
                    notification_type='system',
                    data={
                        'amount': str(amount),
                        'balance': str(wallet.balance),
                    }
                )
        except Exception as e:
            print(f"Wallet topup error: {e}")

    def _handle_regular_payment(
        self, reference, gateway_reference=None
    ):
        try:
            payment = Payment.objects.get(
                reference=reference
            )
            if payment.status != 'success':
                payment.status = 'success'
                if gateway_reference:
                    payment.gateway_reference = str(
                        gateway_reference
                    )
                payment.save()
                mark_as_paid(
                    payment.payment_for,
                    payment.object_id
                )
        except Payment.DoesNotExist:
            pass

    def _handle_transfer_success(self, transfer_ref, data):
        """Auto complete withdrawal on transfer success"""
        from apps.wallet.models import VendorWithdrawalRequest
        from apps.notifications.utils import send_notification
        from django.utils import timezone

        try:
            withdrawal = VendorWithdrawalRequest.objects.get(
                gateway_reference=transfer_ref,
                status__in=['approved', 'processing']
            )
            withdrawal.status       = 'completed'
            withdrawal.completed_at = timezone.now()
            withdrawal.save()

            send_notification(
                user=withdrawal.vendor,
                title='Withdrawal Successful! 💰',
                message=(
                    f'₦{withdrawal.net_amount} has been '
                    f'sent to your '
                    f'{withdrawal.bank_account.bank_name} '
                    f'account ending '
                    f'{withdrawal.bank_account.account_number[-4:]}.'
                ),
                notification_type='system',
                data={
                    'withdrawal_id': withdrawal.id,
                    'amount': str(withdrawal.net_amount),
                    'status': 'completed',
                }
            )
        except VendorWithdrawalRequest.DoesNotExist:
            print(
                f"Transfer webhook: withdrawal not found "
                f"for {transfer_ref}"
            )
        except Exception as e:
            print(f"Transfer success webhook error: {e}")

    def _handle_transfer_failed(self, transfer_ref, reason):
        """Handle failed transfer — reverse the withdrawal"""
        from apps.wallet.models import (
            VendorWithdrawalRequest,
            VendorTransaction,
        )
        from apps.notifications.utils import send_notification
        from apps.common.utils import generate_reference
        from django.utils import timezone

        try:
            withdrawal = VendorWithdrawalRequest.objects.get(
                gateway_reference=transfer_ref,
                status__in=['approved', 'processing']
            )

            # Reverse — return amount to available balance
            wallet                   = withdrawal.vendor_wallet
            wallet.reserved_balance  -= withdrawal.amount
            wallet.available_balance += withdrawal.amount
            wallet.total_withdrawn   -= withdrawal.amount
            wallet.save()

            # Record reversal
            VendorTransaction.objects.create(
                vendor_wallet=wallet,
                transaction_type='release',
                amount=withdrawal.amount,
                available_balance_after=wallet.available_balance,
                pending_balance_after=wallet.pending_balance,
                description=(
                    f'Transfer failed reversal - '
                    f'{withdrawal.reference}'
                ),
                reference=generate_reference('TREV'),
                status='success',
            )

            withdrawal.status         = 'failed'
            withdrawal.failure_reason = reason
            withdrawal.save()

            send_notification(
                user=withdrawal.vendor,
                title='Withdrawal Failed ❌',
                message=(
                    f'Your withdrawal of '
                    f'₦{withdrawal.net_amount} failed. '
                    f'Reason: {reason}. '
                    f'Amount returned to your wallet. '
                    f'Please try again.'
                ),
                notification_type='system',
                data={
                    'withdrawal_id': withdrawal.id,
                    'amount': str(withdrawal.net_amount),
                    'reason': reason,
                }
            )
        except VendorWithdrawalRequest.DoesNotExist:
            print(
                f"Transfer webhook: withdrawal not found "
                f"for {transfer_ref}"
            )
        except Exception as e:
            print(f"Transfer failed webhook error: {e}")

class RefundPaymentView(APIView):
    """Refund a payment"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = RefundPaymentSerializer(data=request.data)
        if not serializer.is_valid():
            return api_response(
                'error', 'Invalid data',
                errors=serializer.errors,
                http_status=status.HTTP_400_BAD_REQUEST
            )

        reference      = serializer.validated_data['reference']
        gateway        = serializer.validated_data['gateway']
        amount         = serializer.validated_data.get('amount')
        transaction_id = serializer.validated_data.get(
            'transaction_id'
        )

        try:
            payment = Payment.objects.get(
                reference=reference,
                user=request.user,
                status='success'
            )
        except Payment.DoesNotExist:
            return api_response(
                'error',
                'Payment not found or not eligible for refund',
                http_status=status.HTTP_404_NOT_FOUND
            )

        success = False

        if gateway == 'paystack':
            result  = paystack_gateway.refund_payment(
                reference=reference, amount=amount
            )
            success = result.get('status')

        elif gateway == 'flutterwave':
            result  = flutterwave_gateway.refund_payment(
                transaction_id=(
                    transaction_id or payment.gateway_reference
                ),
                amount=amount
            )
            success = result.get('status') == 'success'

        if success:
            payment.status = 'refunded'
            payment.save()
            return api_response(
                'success',
                'Refund processed successfully',
                data=PaymentSerializer(payment).data
            )

        return api_response(
            'error', 'Refund failed',
            http_status=status.HTTP_400_BAD_REQUEST
        )


class PaymentHistoryView(APIView):
    """Get user payment history"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        payments = Payment.objects.filter(user=request.user)

        payment_status = request.query_params.get('status')
        gateway        = request.query_params.get('gateway')
        payment_for    = request.query_params.get('payment_for')

        if payment_status:
            payments = payments.filter(status=payment_status)
        if gateway:
            payments = payments.filter(gateway=gateway)
        if payment_for:
            payments = payments.filter(payment_for=payment_for)

        serializer = PaymentSerializer(payments, many=True)
        return api_response(
            'success',
            'Payment history retrieved successfully',
            data={
                'count': payments.count(),
                'total_paid': str(sum(
                    p.amount for p in payments
                    if p.status == 'success'
                )),
                'results': serializer.data
            }
        )


class PaymentDetailView(APIView):
    """Get single payment details"""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            payment = Payment.objects.get(
                pk=pk, user=request.user
            )
        except Payment.DoesNotExist:
            return api_response(
                'error', 'Payment not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = PaymentSerializer(payment)
        return api_response(
            'success',
            'Payment retrieved successfully',
            data=serializer.data
        )


class AdminPaymentListView(APIView):
    """Admin - list all payments"""
    permission_classes = [IsAdmin]

    def get(self, request):
        payments = Payment.objects.all()

        payment_status = request.query_params.get('status')
        gateway        = request.query_params.get('gateway')

        if payment_status:
            payments = payments.filter(status=payment_status)
        if gateway:
            payments = payments.filter(gateway=gateway)

        serializer = PaymentSerializer(payments, many=True)
        return api_response(
            'success',
            'All payments retrieved',
            data={
                'count': payments.count(),
                'total_revenue': str(sum(
                    p.amount for p in payments
                    if p.status == 'success'
                )),
                'results': serializer.data
            }
        )


class GetBanksView(APIView):
    """Get list of Nigerian banks"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        gateway = request.query_params.get('gateway', 'paystack')

        if gateway == 'paystack':
            result = paystack_gateway.get_banks()
            if result.get('status'):
                return api_response(
                    'success',
                    'Banks retrieved successfully',
                    data=result['data']
                )

        elif gateway == 'flutterwave':
            result = flutterwave_gateway.get_banks()
            if result.get('status') == 'success':
                return api_response(
                    'success',
                    'Banks retrieved successfully',
                    data=result['data']
                )

        return api_response(
            'error', 'Failed to retrieve banks',
            http_status=status.HTTP_400_BAD_REQUEST
        )


class VerifyAccountView(APIView):
    """Verify bank account number"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        account_number = request.data.get('account_number')
        bank_code      = request.data.get('bank_code')

        if not account_number or not bank_code:
            return api_response(
                'error',
                'Account number and bank code are required',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        result = paystack_gateway.verify_account(
            account_number, bank_code
        )

        if result.get('status'):
            return api_response(
                'success',
                'Account verified successfully',
                data=result['data']
            )

        return api_response(
            'error', 'Account verification failed',
            http_status=status.HTTP_400_BAD_REQUEST
        )