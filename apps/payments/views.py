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
        serializer = InitializePaymentSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            payment_for = data['payment_for']
            object_id = data['object_id']
            gateway = data['gateway']

            # Get amount and user
            amount, obj_user = get_payment_amount(
                payment_for, object_id
            )

            if not amount:
                return api_response(
                    'error',
                    'Invalid payment object',
                    http_status=status.HTTP_404_NOT_FOUND
                )

            # Generate reference
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
                    phone=request.user.phone,
                    callback_url=data.get('callback_url'),
                    redirect_url=data.get('redirect_url'),
                    metadata={
                        'payment_id': payment.id,
                        'payment_for': payment_for,
                        'object_id': object_id,
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

            # If we get here gateway failed
            payment.status = 'failed'
            payment.failure_reason = str(result)
            payment.save()

            return api_response(
                'error',
                'Payment initialization failed',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        return api_response(
            'error',
            'Invalid data',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class VerifyPaymentView(APIView):
    """Verify payment after completion"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = VerifyPaymentSerializer(data=request.data)
        if serializer.is_valid():
            reference = serializer.validated_data['reference']
            gateway = serializer.validated_data['gateway']
            transaction_id = serializer.validated_data.get('transaction_id')

            # Get payment record
            try:
                payment = Payment.objects.get(
                    reference=reference,
                    user=request.user
                )
            except Payment.DoesNotExist:
                return api_response(
                    'error',
                    'Payment not found',
                    http_status=status.HTTP_404_NOT_FOUND
                )

            if payment.status == 'success':
                return api_response(
                    'success',
                    'Payment already verified',
                    data=PaymentSerializer(payment).data
                )

            # Verify with gateway
            verified = False

            if gateway == 'paystack':
                result = paystack_gateway.verify_payment(reference)
                if (
                    result.get('status') and
                    result['data']['status'] == 'success'
                ):
                    verified = True
                    payment.gateway_reference = result['data']['id']

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

        # Handle list response
                    if isinstance(data, list):
                        if len(data) == 0:
                # Payment not found or not completed yet
                            return api_response(
                                'error',
                                'Payment not found. Please complete the payment first.',
                                http_status=status.HTTP_400_BAD_REQUEST
                            )
                    data = data[0]

                if data.get('status') in ['successful', 'success']:
                    verified = True
                    payment.gateway_reference = str(data.get('id', ''))

            if verified:
                payment.status = 'success'
                payment.save()

                # Mark the order/booking/ride as paid
                mark_as_paid(
                    payment.payment_for,
                    payment.object_id
                )

                return api_response(
                    'success',
                    'Payment verified successfully',
                    data=PaymentSerializer(payment).data
                )

            else:
                payment.status = 'failed'
                payment.save()

                return api_response(
                    'error',
                    'Payment verification failed',
                    http_status=status.HTTP_400_BAD_REQUEST
                )

        return api_response(
            'error',
            'Invalid data',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class PaystackWebhookView(APIView):
    """Handle Paystack webhook events"""
    permission_classes = [AllowAny]

    def post(self, request):
        # Verify webhook signature
        paystack_signature = request.headers.get('X-Paystack-Signature')
        secret = os.getenv('PAYSTACK_SECRET_KEY', '')

        computed = hmac.new(
            secret.encode('utf-8'),
            request.body,
            hashlib.sha512
        ).hexdigest()

        if not hmac.compare_digest(computed, paystack_signature or ''):
            return api_response(
                'error',
                'Invalid signature',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        payload = json.loads(request.body)
        event = payload.get('event')

        if event == 'charge.success':
            reference = payload['data']['reference']
            amount_kobo = payload['data']['amount']
            amount = amount_kobo / 100  # convert from kobo

            # Check if wallet topup
            metadata = payload['data'].get('metadata', {})
            payment_type = metadata.get('type')

            if payment_type == 'wallet_topup':
                # Auto credit wallet
                from decimal import Decimal
                from apps.wallet.models import Wallet, WalletTransaction
                from apps.wallet.utils import get_or_create_wallet
                from django.contrib.auth import get_user_model
                User = get_user_model()

                user_id = metadata.get('user_id')
                try:
                    user = User.objects.get(pk=user_id)
                    wallet = get_or_create_wallet(user)

                    # Check not already credited
                    already = WalletTransaction.objects.filter(
                        reference=reference,
                        status='success'
                    ).exists()

                    if not already:
                        wallet.credit(
                            amount=Decimal(str(amount)),
                            description='Wallet top up via Paystack',
                            reference=reference
                        )

                        # Update pending transaction if exists
                        WalletTransaction.objects.filter(
                            wallet=wallet,
                            reference=reference,
                            status='pending'
                        ).update(
                            status='success',
                            balance_after=wallet.balance
                        )

                        # Notify user
                        from apps.notifications.utils import send_notification
                        send_notification(
                            user=user,
                            title='Wallet Topped Up! 🎉',
                            message=f'₦{amount} added to your wallet. New balance: ₦{wallet.balance}',
                            notification_type='system',
                            data={
                                'amount': str(amount),
                                'balance': str(wallet.balance),
                            }
                        )
                except Exception as e:
                    print(f"Wallet credit error: {e}")

            else:
                # Regular payment
                try:
                    payment = Payment.objects.get(reference=reference)
                    if payment.status != 'success':
                        payment.status = 'success'
                        payment.gateway_reference = payload['data']['id']
                        payment.save()
                        mark_as_paid(
                            payment.payment_for,
                            payment.object_id
                        )
                except Payment.DoesNotExist:
                    pass

        elif event == 'refund.processed':
            reference = payload['data']['transaction_reference']
            try:
                payment = Payment.objects.get(reference=reference)
                payment.status = 'refunded'
                payment.save()
            except Payment.DoesNotExist:
                pass

        return api_response('success', 'Webhook received')




class FlutterwaveWebhookView(APIView):
    """Handle Flutterwave webhook events"""
    permission_classes = [AllowAny]

    def post(self, request):
        # Verify webhook signature
        signature = request.headers.get('verif-hash')
        secret = os.getenv('FLUTTERWAVE_SECRET_KEY', '')

        if signature != secret:
            return api_response(
                'error',
                'Invalid signature',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        payload = json.loads(request.body)
        event = payload.get('event')

        if event == 'charge.completed':
            data = payload.get('data', {})
            if data.get('status') == 'successful':
                reference = data.get('tx_ref')
                amount = data.get('amount')
                metadata = data.get('meta', {})
                payment_type = metadata.get('type')

                if payment_type == 'wallet_topup':
                    # Auto credit wallet
                    from decimal import Decimal
                    from apps.wallet.models import Wallet, WalletTransaction
                    from apps.wallet.utils import get_or_create_wallet
                    from django.contrib.auth import get_user_model
                    User = get_user_model()

                    user_id = metadata.get('user_id')
                    try:
                        user = User.objects.get(pk=user_id)
                        wallet = get_or_create_wallet(user)

                        # Check not already credited
                        already = WalletTransaction.objects.filter(
                            reference=reference,
                            status='success'
                        ).exists()

                        if not already:
                            wallet.credit(
                                amount=Decimal(str(amount)),
                                description='Wallet top up via Flutterwave',
                                reference=reference
                            )

                            # Update pending transaction
                            WalletTransaction.objects.filter(
                                wallet=wallet,
                                reference=reference,
                                status='pending'
                            ).update(
                                status='success',
                                balance_after=wallet.balance
                            )

                            # Notify user
                            from apps.notifications.utils import send_notification
                            send_notification(
                                user=user,
                                title='Wallet Topped Up! 🎉',
                                message=f'₦{amount} added to your wallet. New balance: ₦{wallet.balance}',
                                notification_type='system',
                                data={
                                    'amount': str(amount),
                                    'balance': str(wallet.balance),
                                }
                            )
                    except Exception as e:
                        print(f"Wallet credit error: {e}")

                else:
                    # Regular payment
                    try:
                        payment = Payment.objects.get(reference=reference)
                        if payment.status != 'success':
                            payment.status = 'success'
                            payment.gateway_reference = data.get('id')
                            payment.save()
                            mark_as_paid(
                                payment.payment_for,
                                payment.object_id
                            )
                    except Payment.DoesNotExist:
                        pass

        return api_response('success', 'Webhook received')


class RefundPaymentView(APIView):
    """Refund a payment"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = RefundPaymentSerializer(data=request.data)
        if serializer.is_valid():
            reference = serializer.validated_data['reference']
            gateway = serializer.validated_data['gateway']
            amount = serializer.validated_data.get('amount')
            transaction_id = serializer.validated_data.get('transaction_id')

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

            if gateway == 'paystack':
                result = paystack_gateway.refund_payment(
                    reference=reference,
                    amount=amount
                )
                success = result.get('status')

            elif gateway == 'flutterwave':
                result = flutterwave_gateway.refund_payment(
                    transaction_id=transaction_id or payment.gateway_reference,
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
                'error',
                'Refund failed',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        return api_response(
            'error',
            'Invalid data',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class PaymentHistoryView(APIView):
    """Get user payment history"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        payments = Payment.objects.filter(user=request.user)

        # Filter by status
        payment_status = request.query_params.get('status')
        if payment_status:
            payments = payments.filter(status=payment_status)

        # Filter by gateway
        gateway = request.query_params.get('gateway')
        if gateway:
            payments = payments.filter(gateway=gateway)

        # Filter by payment_for
        payment_for = request.query_params.get('payment_for')
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
                pk=pk,
                user=request.user
            )
        except Payment.DoesNotExist:
            return api_response(
                'error',
                'Payment not found',
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
        if payment_status:
            payments = payments.filter(status=payment_status)

        gateway = request.query_params.get('gateway')
        if gateway:
            payments = payments.filter(gateway=gateway)

        total_revenue = sum(
            p.amount for p in payments
            if p.status == 'success'
        )

        serializer = PaymentSerializer(payments, many=True)
        return api_response(
            'success',
            'All payments retrieved',
            data={
                'count': payments.count(),
                'total_revenue': str(total_revenue),
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
            'error',
            'Failed to retrieve banks',
            http_status=status.HTTP_400_BAD_REQUEST
        )


class VerifyAccountView(APIView):
    """Verify bank account number"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        account_number = request.data.get('account_number')
        bank_code = request.data.get('bank_code')

        if not account_number or not bank_code:
            return api_response(
                'error',
                'Account number and bank code are required',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        result = paystack_gateway.verify_account(
            account_number,
            bank_code
        )

        if result.get('status'):
            return api_response(
                'success',
                'Account verified successfully',
                data=result['data']
            )

        return api_response(
            'error',
            'Account verification failed',
            http_status=status.HTTP_400_BAD_REQUEST
        )