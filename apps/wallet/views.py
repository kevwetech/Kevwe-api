from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction
from apps.common.views import api_response
from apps.common.permissions import IsAdmin
from apps.common.utils import generate_reference
from apps.marketplace.models import Business
from apps.payments.flutterwave import initialize_payment
from apps.payments.paystack import initialize_payment
from apps.notifications.utils import send_notification
from apps.payments.paystack import verify_account
import os
from .models import( 
    Wallet, 
    WalletTransaction, 
    BankAccount, 
    WithdrawalRequest, 
    VendorWallet, 
    VendorTransaction,
    VendorWithdrawalRequest,
    EarningsSummary,
    BankAccount,
)
from decimal import Decimal 
from .serializers import (
    WalletSerializer,
    WalletTransactionSerializer,
    BankAccountSerializer,
    WithdrawalRequestSerializer,
    TopUpSerializer,
    PayWithWalletSerializer,
    TransferSerializer,
    WithdrawalSerializer,
    SetPinSerializer,
    ChangePinSerializer,
    VendorWalletSerializer,
    VendorTransactionSerializer,
    VendorWithdrawalRequestSerializer,
    CreateWithdrawalSerializer,
    EarningsSummarySerializer,
)
from .utils import (
    get_or_create_wallet,
    calculate_withdrawal_fee,
    mark_payment_as_paid,
)

User = get_user_model()


class WalletView(APIView):
    """Get wallet balance and details"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        wallet = get_or_create_wallet(request.user)
        serializer = WalletSerializer(wallet)
        return api_response(
            'success',
            'Wallet retrieved successfully',
            data=serializer.data
        )


class TopUpWalletView(APIView):
    """Initialize wallet top up via Paystack or Flutterwave"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = TopUpSerializer(data=request.data)
        if serializer.is_valid():
            amount = serializer.validated_data['amount']
            gateway = serializer.validated_data['gateway']
            callback_url = serializer.validated_data.get('callback_url')

            reference = generate_reference('WLT')

            # Create pending transaction
            wallet = get_or_create_wallet(request.user)
            WalletTransaction.objects.create(
                wallet=wallet,
                transaction_type='credit',
                category='topup',
                amount=amount,
                balance_after=wallet.balance,
                description=f'Wallet top up - ₦{amount}',
                reference=reference,
                status='pending',
                metadata={
                    'gateway': gateway,
                    'type': 'topup'
                }
            )

            # Initialize payment
            if gateway == 'paystack':
                
                result = initialize_payment(
                    email=request.user.email,
                    amount=amount,
                    reference=reference,
                    callback_url=callback_url,
                    metadata={
                        'type': 'wallet_topup',
                        'user_id': request.user.id,
                        'wallet_id': wallet.id,
                    }
                )

                if result.get('status'):
                    return api_response(
                        'success',
                        'Top up initialized successfully',
                        data={
                            'reference': reference,
                            'amount': str(amount),
                            'gateway': gateway,
                            'authorization_url': result['data']['authorization_url'],
                            'access_code': result['data']['access_code'],
                        }
                    )

            elif gateway == 'flutterwave':
                
                result = initialize_payment(
                    email=request.user.email,
                    amount=amount,
                    reference=reference,
                    name=request.user.full_name,
                    phone=request.user.phone,
                    callback_url=callback_url,
                    metadata={
                        'type': 'wallet_topup',
                        'user_id': request.user.id,
                        'wallet_id': wallet.id,
                    }
                )

                if result.get('status') == 'success':
                    return api_response(
                        'success',
                        'Top up initialized successfully',
                        data={
                            'reference': reference,
                            'amount': str(amount),
                            'gateway': gateway,
                            'payment_link': result['data']['link'],
                        }
                    )

            return api_response(
                'error',
                'Failed to initialize top up',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        return api_response(
            'error',
            'Invalid data',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class VerifyTopUpView(APIView):
    """Confirm wallet top up after payment"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        reference = request.data.get('reference')
        gateway = request.data.get('gateway', 'paystack')
        transaction_id = request.data.get('transaction_id')

        if not reference:
            return api_response(
                'error',
                'Reference is required',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        wallet = get_or_create_wallet(request.user)

        # Check if already confirmed
        already_confirmed = wallet.transactions.filter(
            reference=reference,
            status='success'
        ).exists()

        if already_confirmed:
            return api_response(
                'success',
                'Wallet already topped up with this reference',
                data={
                    'balance': str(wallet.balance),
                }
            )

        # Get pending transaction OR create if not exists
        transaction = wallet.transactions.filter(
            reference=reference
        ).first()

        if not transaction:
            return api_response(
                'error',
                'Transaction not found. Make sure you initialized the topup first.',
                http_status=status.HTTP_404_NOT_FOUND
            )

        # Verify payment with gateway
        verified = False
        amount = transaction.amount

        if gateway == 'paystack':
            
            result = verify_payment(reference)
            print(f"Paystack verify: {result}")
            if (
                result.get('status') and
                result['data']['status'] == 'success'
            ):
                verified = True
                amount = result['data']['amount'] / 100  # convert from kobo

        elif gateway == 'flutterwave':
            from apps.payments.flutterwave import (
                verify_payment,
                verify_payment_by_reference
            )
            if transaction_id:
                result = verify_payment(transaction_id)
                if result.get('status') == 'success':
                    data = result.get('data', {})
                    if data.get('status') in ['successful', 'success']:
                        verified = True
                        amount = data.get('amount', amount)
            else:
                result = verify_payment_by_reference(reference)
                if result.get('status') == 'success':
                    data = result.get('data', [])
                    if isinstance(data, list) and len(data) > 0:
                        if data[0].get('status') == 'successful':
                            verified = True
                            amount = data[0].get('amount', amount)

        if verified:
            # Credit wallet
            wallet.balance += amount
            wallet.total_credited += amount
            wallet.save()

            # Update transaction
            transaction.status = 'success'
            transaction.balance_after = wallet.balance
            transaction.save()

            # Send notification
            from apps.notifications.utils import send_notification
            send_notification(
                user=request.user,
                title='Wallet Topped Up! 🎉',
                message=f'₦{amount} added to your wallet. New balance: ₦{wallet.balance}',
                notification_type='system',
                data={
                    'amount': str(amount),
                    'balance': str(wallet.balance),
                }
            )

            return api_response(
                'success',
                f'Wallet topped up successfully with ₦{amount}',
                data={
                    'amount_added': str(amount),
                    'new_balance': str(wallet.balance),
                }
            )

        return api_response(
            'error',
            'Payment not verified. Please complete the payment first.',
            http_status=status.HTTP_400_BAD_REQUEST
        )


class PayWithWalletView(APIView):
    """Pay for services using wallet balance"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PayWithWalletSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            amount = data['amount']
            payment_for = data['payment_for']
            object_id = data['object_id']
            description = data['description']
            pin = data.get('pin')

            wallet = get_or_create_wallet(request.user)

            # Verify PIN if set
            if wallet.is_pin_set:
                if not pin:
                    return api_response(
                        'error',
                        'Wallet PIN is required',
                        http_status=status.HTTP_400_BAD_REQUEST
                    )
                if wallet.pin != pin:
                    return api_response(
                        'error',
                        'Invalid wallet PIN',
                        http_status=status.HTTP_400_BAD_REQUEST
                    )

            # Check balance
            if wallet.balance < amount:
                return api_response(
                    'error',
                    f'Insufficient wallet balance. Balance: ₦{wallet.balance}',
                    http_status=status.HTTP_400_BAD_REQUEST
                )

            reference = generate_reference('WPAY')

            with transaction.atomic():
                # Debit wallet
                wallet.debit(
                    amount=amount,
                    description=description,
                    reference=reference
                )

                # Mark payment as paid
                mark_payment_as_paid(payment_for, object_id)

            # Send notification
            
            send_notification(
                user=request.user,
                title='Payment Successful',
                message=f'₦{amount} paid for {payment_for}. Wallet balance: ₦{wallet.balance}',
                notification_type='system',
                data={
                    'amount': str(amount),
                    'payment_for': payment_for,
                    'balance': str(wallet.balance),
                }
            )

            return api_response(
                'success',
                'Payment successful',
                data={
                    'amount_paid': str(amount),
                    'payment_for': payment_for,
                    'reference': reference,
                    'new_balance': str(wallet.balance),
                }
            )

        return api_response(
            'error',
            'Payment failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class TransferView(APIView):
    """Transfer money to another user's wallet"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = TransferSerializer(data=request.data)
        if serializer.is_valid():
            recipient_email = serializer.validated_data['recipient_email']
            amount = serializer.validated_data['amount']
            description = serializer.validated_data.get(
                'description', 'Wallet transfer'
            )
            pin = serializer.validated_data['pin']

            # Get sender wallet
            sender_wallet = get_or_create_wallet(request.user)

            # Verify PIN
            if sender_wallet.is_pin_set and sender_wallet.pin != pin:
                return api_response(
                    'error',
                    'Invalid wallet PIN',
                    http_status=status.HTTP_400_BAD_REQUEST
                )

            # Check balance
            if sender_wallet.balance < amount:
                return api_response(
                    'error',
                    f'Insufficient balance. Balance: ₦{sender_wallet.balance}',
                    http_status=status.HTTP_400_BAD_REQUEST
                )

            # Get recipient
            try:
                recipient = User.objects.get(email=recipient_email)
            except User.DoesNotExist:
                return api_response(
                    'error',
                    'Recipient not found',
                    http_status=status.HTTP_404_NOT_FOUND
                )

            if recipient == request.user:
                return api_response(
                    'error',
                    'Cannot transfer to yourself',
                    http_status=status.HTTP_400_BAD_REQUEST
                )

            recipient_wallet = get_or_create_wallet(recipient)
            reference = generate_reference('WTRN')

            with transaction.atomic():
                # Debit sender
                sender_wallet.debit(
                    amount=amount,
                    description=f'Transfer to {recipient.full_name}: {description}',
                    reference=f'{reference}-OUT'
                )

                # Credit recipient
                recipient_wallet.credit(
                    amount=amount,
                    description=f'Transfer from {request.user.full_name}: {description}',
                    reference=f'{reference}-IN'
                )

            # Notify sender
            
            send_notification(
                user=request.user,
                title='Transfer Successful',
                message=f'₦{amount} sent to {recipient.full_name}. Balance: ₦{sender_wallet.balance}',
                notification_type='system'
            )

            # Notify recipient
            send_notification(
                user=recipient,
                title='Money Received',
                message=f'₦{amount} received from {request.user.full_name}',
                notification_type='system'
            )

            return api_response(
                'success',
                'Transfer successful',
                data={
                    'amount_sent': str(amount),
                    'recipient': recipient.full_name,
                    'reference': reference,
                    'new_balance': str(sender_wallet.balance),
                }
            )

        return api_response(
            'error',
            'Transfer failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class BankAccountListCreateView(APIView):
    """Manage bank accounts"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        accounts = BankAccount.objects.filter(user=request.user)
        serializer = BankAccountSerializer(accounts, many=True)
        return api_response(
            'success',
            'Bank accounts retrieved successfully',
            data={
                'count': accounts.count(),
                'results': serializer.data
            }
        )

    def post(self, request):
        serializer = BankAccountSerializer(data=request.data)
        if not serializer.is_valid():
            return api_response(
                'error',
                'Failed to add bank account',
                errors=serializer.errors,
                http_status=status.HTTP_400_BAD_REQUEST
            )

        from apps.payments.paystack import verify_account
        import os

        account_name  = serializer.validated_data.get(
            'account_name', ''
        )
        is_verified   = False
        is_production = os.getenv(
            'DJANGO_ENV', 'development'
        ) == 'production'

        # Verify account with Paystack
        result = verify_account(
            serializer.validated_data['account_number'],
            serializer.validated_data['bank_code']
        )

        if result.get('status'):
            # Paystack verified successfully
            account_name  = result['data']['account_name']
            is_verified   = True
            verified_name = account_name.upper()
            user_name     = request.user.full_name.upper()

            # Name validation — production only
            if is_production:
                from apps.marketplace.models import Business
                business_names = list(
                    Business.objects.filter(
                        owner=request.user
                    ).values_list('name', flat=True)
                )

                user_parts     = user_name.split()
                name_match     = any(
                    part in verified_name
                    for part in user_parts
                    if len(part) > 2
                )
                business_match = any(
                    biz_name.upper() in verified_name or
                    verified_name in biz_name.upper()
                    for biz_name in business_names
                )

                if not name_match and not business_match:
                    return api_response(
                        'error',
                        f'Bank account name "{account_name}" '
                        f'does not match your name or '
                        f'business name. Please use a bank '
                        f'account registered under your name '
                        f'or business name.',
                        data={
                            'verified_account_name': account_name,
                            'your_name': request.user.full_name,
                            'your_businesses': business_names,
                        },
                        http_status=status.HTTP_400_BAD_REQUEST
                    )

        else:
            # Paystack could not verify
            if is_production:
                return api_response(
                    'error',
                    'Could not verify bank account. '
                    'Please check your account number '
                    'and bank code.',
                    http_status=status.HTTP_400_BAD_REQUEST
                )
            # Dev: allow unverified accounts for testing

        # Set as default if first account
        is_default = not BankAccount.objects.filter(
            user=request.user
        ).exists()

        account = serializer.save(
            user=request.user,
            account_name=account_name,
            is_verified=is_verified,
            is_default=is_default
        )

        return api_response(
            'success',
            'Bank account added successfully',
            data=BankAccountSerializer(account).data,
            http_status=status.HTTP_201_CREATED
        )

class BankAccountDetailView(APIView):
    """Get, update and delete bank account"""
    permission_classes = [IsAuthenticated]

    def get_object(self, pk, user):
        try:
            return BankAccount.objects.get(pk=pk, user=user)
        except BankAccount.DoesNotExist:
            return None

    def delete(self, request, pk):
        account = self.get_object(pk, request.user)
        if not account:
            return api_response(
                'error',
                'Bank account not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        account.delete()
        return api_response(
            'success',
            'Bank account removed successfully'
        )

    def patch(self, request, pk):
        """Set as default bank account"""
        account = self.get_object(pk, request.user)
        if not account:
            return api_response(
                'error',
                'Bank account not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        # Remove default from others
        BankAccount.objects.filter(
            user=request.user
        ).update(is_default=False)

        account.is_default = True
        account.save()

        return api_response(
            'success',
            'Default bank account updated',
            data=BankAccountSerializer(account).data
        )


class WithdrawalView(APIView):
    """Request withdrawal to bank account"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = WithdrawalSerializer(data=request.data)
        if serializer.is_valid():
            bank_account_id = serializer.validated_data['bank_account_id']
            amount = serializer.validated_data['amount']
            pin = serializer.validated_data['pin']

            wallet = get_or_create_wallet(request.user)

            # Verify PIN
            if wallet.is_pin_set and wallet.pin != pin:
                return api_response(
                    'error',
                    'Invalid wallet PIN',
                    http_status=status.HTTP_400_BAD_REQUEST
                )

            # Calculate fee
            fee = calculate_withdrawal_fee(amount)
            net_amount = float(amount) - fee

            # Check balance
            if wallet.balance < amount:
                return api_response(
                    'error',
                    f'Insufficient balance. Balance: ₦{wallet.balance}',
                    http_status=status.HTTP_400_BAD_REQUEST
                )

            # Get bank account
            try:
                bank_account = BankAccount.objects.get(
                    pk=bank_account_id,
                    user=request.user
                )
            except BankAccount.DoesNotExist:
                return api_response(
                    'error',
                    'Bank account not found',
                    http_status=status.HTTP_404_NOT_FOUND
                )

            reference = generate_reference('WDRL')

            with transaction.atomic():
                # Debit wallet
                wallet.debit(
                    amount=amount,
                    description=f'Withdrawal to {bank_account.account_number}',
                    reference=reference
                )

                # Create withdrawal request
                withdrawal = WithdrawalRequest.objects.create(
                    user=request.user,
                    wallet=wallet,
                    bank_account=bank_account,
                    amount=amount,
                    fee=fee,
                    net_amount=net_amount,
                    reference=reference,
                    status='pending'
                )

            # Send notification
            
            send_notification(
                user=request.user,
                title='Withdrawal Requested',
                message=f'₦{net_amount} withdrawal to {bank_account.account_name} is being processed',
                notification_type='system'
            )

            return api_response(
                'success',
                'Withdrawal request submitted successfully',
                data=WithdrawalRequestSerializer(withdrawal).data
            )

        return api_response(
            'error',
            'Withdrawal failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class WithdrawalHistoryView(APIView):
    """Get withdrawal history"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        withdrawals = WithdrawalRequest.objects.filter(
            user=request.user
        )
        serializer = WithdrawalRequestSerializer(
            withdrawals,
            many=True
        )
        return api_response(
            'success',
            'Withdrawal history retrieved',
            data={
                'count': withdrawals.count(),
                'results': serializer.data
            }
        )


class TransactionHistoryView(APIView):
    """Get wallet transaction history"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        wallet = get_or_create_wallet(request.user)
        transactions = WalletTransaction.objects.filter(
            wallet=wallet
        )

        # Filter by type
        txn_type = request.query_params.get('type')
        if txn_type:
            transactions = transactions.filter(
                transaction_type=txn_type
            )

        # Filter by category
        category = request.query_params.get('category')
        if category:
            transactions = transactions.filter(category=category)

        serializer = WalletTransactionSerializer(
            transactions,
            many=True
        )

        return api_response(
            'success',
            'Transaction history retrieved successfully',
            data={
                'count': transactions.count(),
                'wallet_balance': str(wallet.balance),
                'total_credited': str(wallet.total_credited),
                'total_debited': str(wallet.total_debited),
                'results': serializer.data
            }
        )


class SetPinView(APIView):
    """Set wallet PIN"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = SetPinSerializer(data=request.data)
        if serializer.is_valid():
            wallet = get_or_create_wallet(request.user)

            if wallet.is_pin_set:
                return api_response(
                    'error',
                    'PIN already set. Use change PIN instead.',
                    http_status=status.HTTP_400_BAD_REQUEST
                )

            wallet.pin = serializer.validated_data['pin']
            wallet.is_pin_set = True
            wallet.save()

            return api_response(
                'success',
                'Wallet PIN set successfully'
            )

        return api_response(
            'error',
            'Failed to set PIN',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class ChangePinView(APIView):
    """Change wallet PIN"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePinSerializer(data=request.data)
        if serializer.is_valid():
            wallet = get_or_create_wallet(request.user)

            if not wallet.is_pin_set:
                return api_response(
                    'error',
                    'No PIN set. Use set PIN first.',
                    http_status=status.HTTP_400_BAD_REQUEST
                )

            if wallet.pin != serializer.validated_data['old_pin']:
                return api_response(
                    'error',
                    'Incorrect current PIN',
                    http_status=status.HTTP_400_BAD_REQUEST
                )

            wallet.pin = serializer.validated_data['new_pin']
            wallet.save()

            return api_response(
                'success',
                'Wallet PIN changed successfully'
            )

        return api_response(
            'error',
            'Failed to change PIN',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class AdminCreditWalletView(APIView):
    """Admin - credit user wallet manually"""
    permission_classes = [IsAdmin]

    def post(self, request):
        user_id = request.data.get('user_id')
        amount = request.data.get('amount')
        description = request.data.get('description', 'Admin credit')

        if not user_id or not amount:
            return api_response(
                'error',
                'user_id and amount are required',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return api_response(
                'error',
                'User not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        wallet = get_or_create_wallet(user)
        reference = generate_reference('ADMC')

        wallet.credit(
            amount=Decimal(str(amount)),
            description=description,
            reference=reference
        )

        # Notify user
        
        send_notification(
            user=user,
            title='Wallet Credited',
            message=f'₦{amount} has been added to your wallet by admin. Balance: ₦{wallet.balance}',
            notification_type='system'
        )

        return api_response(
            'success',
            f'₦{amount} credited to {user.full_name} wallet',
            data={
                'user': user.full_name,
                'amount': str(amount),
                'new_balance': str(wallet.balance),
            }
        )


class AdminDebitWalletView(APIView):
    """Admin - debit user wallet manually"""
    permission_classes = [IsAdmin]

    def post(self, request):
        user_id = request.data.get('user_id')
        amount = request.data.get('amount')
        description = request.data.get('description', 'Admin debit')

        if not user_id or not amount:
            return api_response(
                'error',
                'user_id and amount are required',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return api_response(
                'error',
                'User not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        wallet = get_or_create_wallet(user)

        try:
            reference = generate_reference('ADMD')
            wallet.debit(
                amount=Decimal(str(amount)),
                description=description,
                reference=reference
            )

            return api_response(
                'success',
                f'₦{amount} debited from {user.full_name} wallet',
                data={
                    'user': user.full_name,
                    'amount': str(amount),
                    'new_balance': str(wallet.balance),
                }
            )
        except ValueError as e:
            return api_response(
                'error',
                str(e),
                http_status=status.HTTP_400_BAD_REQUEST
            )


class AdminWithdrawalListView(APIView):
    """Admin - manage withdrawal requests"""
    permission_classes = [IsAdmin]

    def get(self, request):
        withdrawals = WithdrawalRequest.objects.all()

        w_status = request.query_params.get('status')
        if w_status:
            withdrawals = withdrawals.filter(status=w_status)

        serializer = WithdrawalRequestSerializer(
            withdrawals,
            many=True
        )
        return api_response(
            'success',
            'Withdrawals retrieved',
            data={
                'count': withdrawals.count(),
                'results': serializer.data
            }
        )

    def patch(self, request, pk):
        """Update withdrawal status"""
        try:
            withdrawal = WithdrawalRequest.objects.get(pk=pk)
        except WithdrawalRequest.DoesNotExist:
            return api_response(
                'error',
                'Withdrawal not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        new_status = request.data.get('status')
        gateway_reference = request.data.get('gateway_reference', '')
        notes = request.data.get('notes', '')

        withdrawal.status = new_status
        if gateway_reference:
            withdrawal.gateway_reference = gateway_reference
        if notes:
            withdrawal.notes = notes
        withdrawal.save()

        # Notify user
        from apps.notifications.utils import send_notification
        send_notification(
            user=withdrawal.user,
            title='Withdrawal Update',
            message=f'Your withdrawal of ₦{withdrawal.net_amount} is now {new_status}',
            notification_type='system'
        )

        # If failed reverse the debit
        if new_status == 'failed':
            wallet = withdrawal.wallet
            wallet.credit(
                amount=withdrawal.amount,
                description=f'Withdrawal reversal - {withdrawal.reference}',
                reference=generate_reference('WREV')
            )

            send_notification(
                user=withdrawal.user,
                title='Withdrawal Reversed',
                message=f'₦{withdrawal.amount} has been returned to your wallet',
                notification_type='system'
            )

        return api_response(
            'success',
            'Withdrawal updated successfully',
            data=WithdrawalRequestSerializer(withdrawal).data
        )


# ─── Vendor Wallet Views ──────────────────────────

def get_or_create_vendor_wallet(business):
    """Get or create vendor wallet for a business"""
    wallet, created = VendorWallet.objects.get_or_create(
        business=business,
        defaults={
            'user': business.owner,
            'settlement_period_days': 7,
        }
    )
    return wallet


class VendorWalletView(APIView):
    """Get vendor wallet details"""
    permission_classes = [IsAuthenticated]

    def get(self, request, business_id):
        from apps.marketplace.models import Business
        try:
            business = Business.objects.get(pk=business_id)
        except Business.DoesNotExist:
            return api_response(
                'error', 'Business not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        if (business.owner != request.user and
                request.user.role != 'admin'):
            return api_response(
                'error', 'Access denied',
                http_status=status.HTTP_403_FORBIDDEN
            )

        wallet = get_or_create_vendor_wallet(business)
        settled = wallet.settle_pending()

        from .serializers import VendorWalletSerializer
        serializer = VendorWalletSerializer(wallet)
        return api_response(
            'success',
            'Vendor wallet retrieved successfully',
            data={
                **serializer.data,
                'just_settled': str(settled),
            }
        )
    def patch(self, request, business_id):
        """Vendor updates wallet settings"""
        from apps.marketplace.models import Business
        try:
            business = Business.objects.get(pk=business_id)
        except Business.DoesNotExist:
            return api_response(
                'error', 'Business not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        if business.owner != request.user:
            return api_response(
                'error', 'Access denied',
                http_status=status.HTTP_403_FORBIDDEN
            )

        wallet = get_or_create_vendor_wallet(business)

        # Only allow updating these fields
        allowed_fields = [
            'auto_withdraw',
            'auto_withdraw_threshold',
            'default_bank_account',
        ]

        for field in allowed_fields:
            if field in request.data:
                setattr(wallet, field, request.data[field])

        wallet.save()

        from .serializers import VendorWalletSerializer
        return api_response(
            'success',
            'Wallet settings updated successfully',
            data=VendorWalletSerializer(wallet).data
        )


class VendorTransactionListView(APIView):
    """List vendor transactions"""
    permission_classes = [IsAuthenticated]

    def get(self, request, business_id):
        from apps.marketplace.models import Business
        try:
            business = Business.objects.get(pk=business_id)
        except Business.DoesNotExist:
            return api_response(
                'error', 'Business not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        if (business.owner != request.user and
                request.user.role != 'admin'):
            return api_response(
                'error', 'Access denied',
                http_status=status.HTTP_403_FORBIDDEN
            )

        wallet = get_or_create_vendor_wallet(business)
        transactions = wallet.transactions.all()

        txn_type   = request.query_params.get('type')
        txn_status = request.query_params.get('status')
        from_date  = request.query_params.get('from_date')
        to_date    = request.query_params.get('to_date')

        if txn_type:
            transactions = transactions.filter(
                transaction_type=txn_type
            )
        if txn_status:
            transactions = transactions.filter(
                status=txn_status
            )
        if from_date:
            transactions = transactions.filter(
                created_at__date__gte=from_date
            )
        if to_date:
            transactions = transactions.filter(
                created_at__date__lte=to_date
            )

        total_earned = sum(
            t.amount for t in
            transactions.filter(transaction_type='earning')
        )
        total_withdrawn = sum(
            t.amount for t in
            transactions.filter(transaction_type='withdrawal')
        )

        
        serializer = VendorTransactionSerializer(
            transactions, many=True
        )
        return api_response(
            'success',
            'Vendor transactions retrieved successfully',
            data={
                'summary': {
                    'total_earned': str(total_earned),
                    'total_withdrawn': str(total_withdrawn),
                    'available_balance': str(
                        wallet.available_balance
                    ),
                    'pending_balance': str(
                        wallet.pending_balance
                    ),
                },
                'count': transactions.count(),
                'results': serializer.data
            }
        )


class VendorWithdrawalListCreateView(APIView):
    """List and create vendor withdrawal requests"""
    permission_classes = [IsAuthenticated]

    def get(self, request, business_id):
        from apps.marketplace.models import Business
        try:
            business = Business.objects.get(pk=business_id)
        except Business.DoesNotExist:
            return api_response(
                'error', 'Business not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        if (business.owner != request.user and
                request.user.role != 'admin'):
            return api_response(
                'error', 'Access denied',
                http_status=status.HTTP_403_FORBIDDEN
            )

        withdrawals = VendorWithdrawalRequest.objects.filter(
            business=business
        )

        wd_status = request.query_params.get('status')
        if wd_status:
            withdrawals = withdrawals.filter(status=wd_status)

        from .serializers import VendorWithdrawalRequestSerializer
        serializer = VendorWithdrawalRequestSerializer(
            withdrawals, many=True
        )
        return api_response(
            'success',
            'Withdrawal requests retrieved successfully',
            data={
                'count': withdrawals.count(),
                'pending': withdrawals.filter(
                    status='pending'
                ).count(),
                'processing': withdrawals.filter(
                    status='processing'
                ).count(),
                'completed': withdrawals.filter(
                    status='completed'
                ).count(),
                'total_withdrawn': str(sum(
                    w.net_amount for w in
                    withdrawals.filter(status='completed')
                )),
                'results': serializer.data
            }
        )

    def post(self, request, business_id):
        """Create withdrawal and auto-transfer immediately"""
        from apps.marketplace.models import Business
        try:
            business = Business.objects.get(pk=business_id)
        except Business.DoesNotExist:
            return api_response(
                'error', 'Business not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        if business.owner != request.user:
            return api_response(
                'error', 'Only business owner can withdraw',
                http_status=status.HTTP_403_FORBIDDEN
            )

        from .serializers import (
            CreateWithdrawalSerializer,
            VendorWithdrawalRequestSerializer,
        )
        serializer = CreateWithdrawalSerializer(
            data=request.data
        )
        if not serializer.is_valid():
            return api_response(
                'error', 'Withdrawal failed',
                errors=serializer.errors,
                http_status=status.HTTP_400_BAD_REQUEST
            )

        data   = serializer.validated_data
        wallet = get_or_create_vendor_wallet(business)

        # Settle pending earnings first
        wallet.settle_pending()

        amount       = data['amount']
        fee          = Decimal('50.00')
        total_amount = amount + fee   # ← total deducted
        net_amount   = amount         # ← vendor receives full

        # Validate balance covers amount + fee
        if wallet.available_balance < total_amount:
            return api_response(
                'error',
                f'Insufficient balance. '
                f'You need ₦{total_amount} '
                f'(₦{amount} + ₦{fee} fee). '
                f'Available: ₦{wallet.available_balance}',
                data={
                    'available_balance': str(
                        wallet.available_balance
                    ),
                    'pending_balance': str(
                        wallet.pending_balance
                    ),
                    'requested': str(amount),
                    'fee': str(fee),
                    'total_required': str(total_amount),
                },
                http_status=status.HTTP_400_BAD_REQUEST
            )

        # Check no pending withdrawal exists
        has_pending = VendorWithdrawalRequest.objects.filter(
            business=business,
            status__in=[
                'pending', 'under_review',
                'approved', 'processing'
            ]
        ).exists()

        if has_pending:
            return api_response(
                'error',
                'You have a pending withdrawal. '
                'Wait for it to complete.',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        # Validate bank account
        try:
            bank_account = BankAccount.objects.get(
                pk=data['bank_account_id'],
                user=request.user
            )
        except BankAccount.DoesNotExist:
            return api_response(
                'error', 'Bank account not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        # Create withdrawal record
        withdrawal = VendorWithdrawalRequest.objects.create(
            vendor=request.user,
            business=business,
            vendor_wallet=wallet,
            bank_account=bank_account,
            amount=total_amount,    # ← total including fee
            fee=fee,
            net_amount=net_amount,  # ← vendor receives full
            reference=generate_reference('VWD'),
            notes=data.get('notes', ''),
            status='pending',
        )

        # Reserve total amount including fee
        wallet.reserve_amount(total_amount)

        # ── Auto transfer ──
        gateway = data.get('gateway', 'paystack')

        try:
            withdrawal.approve(
                admin_user=request.user,
                gateway=gateway
            )
            return api_response(
                'success',
                f'Withdrawal of ₦{net_amount} initiated! '
                f'Transfer is being processed. '
                f'(₦{fee} fee charged)',
                data=VendorWithdrawalRequestSerializer(
                    withdrawal
                ).data,
                http_status=status.HTTP_201_CREATED
            )

        except ValueError as e:
            # Transfer failed — release reserved amount
            wallet.release_reserve(total_amount)
            withdrawal.status         = 'failed'
            withdrawal.failure_reason = str(e)
            withdrawal.save()

            return api_response(
                'error',
                f'Transfer failed: {str(e)}',
                http_status=status.HTTP_400_BAD_REQUEST
            )

class VendorWithdrawalDetailView(APIView):
    """Get or cancel a vendor withdrawal"""
    permission_classes = [IsAuthenticated]

    def get(self, request, business_id, pk):
        try:
            withdrawal = VendorWithdrawalRequest.objects.get(
                pk=pk, business__id=business_id
            )
        except VendorWithdrawalRequest.DoesNotExist:
            return api_response(
                'error', 'Withdrawal not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        from .serializers import VendorWithdrawalRequestSerializer
        return api_response(
            'success',
            'Withdrawal retrieved successfully',
            data=VendorWithdrawalRequestSerializer(
                withdrawal
            ).data
        )

    def delete(self, request, business_id, pk):
        """Cancel withdrawal request"""
        try:
            withdrawal = VendorWithdrawalRequest.objects.get(
                pk=pk,
                vendor=request.user,
                business__id=business_id
            )
        except VendorWithdrawalRequest.DoesNotExist:
            return api_response(
                'error', 'Withdrawal not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        if not withdrawal.is_cancellable:
            return api_response(
                'error',
                f'Cannot cancel a {withdrawal.status} withdrawal',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        # Release reserved amount
        withdrawal.vendor_wallet.release_reserve(
            withdrawal.amount
        )

        withdrawal.status           = 'rejected'
        withdrawal.rejection_reason = 'other'
        withdrawal.rejection_notes  = 'Cancelled by vendor'
        withdrawal.rejected_by      = request.user
        withdrawal.rejected_at      = timezone.now()
        withdrawal.save()

        return api_response(
            'success',
            'Withdrawal cancelled successfully'
        )

class AdminVendorWithdrawalListView(APIView):
    """Admin views all vendor withdrawal requests"""
    permission_classes = [IsAdmin]

    def get(self, request):
        withdrawals = VendorWithdrawalRequest.objects.all()

        wd_status   = request.query_params.get('status')
        business_id = request.query_params.get('business')

        if wd_status:
            withdrawals = withdrawals.filter(status=wd_status)
        if business_id:
            withdrawals = withdrawals.filter(
                business__id=business_id
            )

        from .serializers import VendorWithdrawalRequestSerializer
        serializer = VendorWithdrawalRequestSerializer(
            withdrawals, many=True
        )
        return api_response(
            'success',
            'All vendor withdrawal requests retrieved',
            data={
                'count': withdrawals.count(),
                'pending': withdrawals.filter(
                    status='pending'
                ).count(),
                'under_review': withdrawals.filter(
                    status='under_review'
                ).count(),
                'approved': withdrawals.filter(
                    status='approved'
                ).count(),
                'completed': withdrawals.filter(
                    status='completed'
                ).count(),
                'total_pending_amount': str(sum(
                    w.amount for w in withdrawals.filter(
                        status__in=['pending', 'under_review']
                    )
                )),
                'results': serializer.data
            }
        )


class AdminVendorWithdrawalActionView(APIView):
    """Admin approves/rejects vendor withdrawal"""
    permission_classes = [IsAdmin]

    def patch(self, request, pk):
        try:
            withdrawal = VendorWithdrawalRequest.objects.get(
                pk=pk
            )
        except VendorWithdrawalRequest.DoesNotExist:
            return api_response(
                'error', 'Withdrawal not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        action = request.data.get('action')
        # review, approve, reject, complete

        from .serializers import VendorWithdrawalRequestSerializer

        if action == 'review':
            withdrawal.status = 'under_review'
            withdrawal.reviewed_by = request.user
            withdrawal.reviewed_at = timezone.now()
            withdrawal.save()
            return api_response(
                'success',
                'Withdrawal marked as under review',
                data=VendorWithdrawalRequestSerializer(
                    withdrawal
                ).data
            )

        elif action == 'approve':
            gateway = request.data.get('gateway', 'paystack')
            try:
                withdrawal.approve(request.user, gateway=gateway)
                return api_response(
                    'success',
                    f'Withdrawal approved via {gateway}',
                    data=VendorWithdrawalRequestSerializer(
                        withdrawal
                    ).data
                )
            except ValueError as e:
                return api_response(
                    'error', str(e),
                    http_status=status.HTTP_400_BAD_REQUEST
                )

        elif action == 'reject':
            reason = request.data.get(
                'rejection_reason', 'other'
            )
            notes = request.data.get('rejection_notes', '')
            try:
                withdrawal.reject(request.user, reason, notes)
                # Release reserved amount back to available
                withdrawal.vendor_wallet.release_reserve(
                    withdrawal.amount
                )
                return api_response(
                    'success',
                    'Withdrawal rejected',
                    data=VendorWithdrawalRequestSerializer(
                        withdrawal
                    ).data
                )
            except ValueError as e:
                return api_response(
                    'error', str(e),
                    http_status=status.HTTP_400_BAD_REQUEST
                )

        elif action == 'complete':
            gateway_ref = request.data.get(
                'gateway_reference', ''
            )
            withdrawal.mark_completed(gateway_ref)
            return api_response(
                'success',
                'Withdrawal marked as completed',
                data=VendorWithdrawalRequestSerializer(
                    withdrawal
                ).data
            )

        return api_response(
            'error',
            'Invalid action. Use: review, approve, reject, complete',
            http_status=status.HTTP_400_BAD_REQUEST
        )


class VendorEarningsSummaryView(APIView):
    """Vendor earnings summary dashboard"""
    permission_classes = [IsAuthenticated]

    def get(self, request, business_id):
        from apps.marketplace.models import Business
        from apps.orders.models import Order
        from datetime import timedelta

        try:
            business = Business.objects.get(pk=business_id)
        except Business.DoesNotExist:
            return api_response(
                'error', 'Business not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        if (business.owner != request.user and
                request.user.role != 'admin'):
            return api_response(
                'error', 'Access denied',
                http_status=status.HTTP_403_FORBIDDEN
            )

        wallet = get_or_create_vendor_wallet(business)
        today  = timezone.now().date()

        # Today
        today_orders = Order.objects.filter(
            business=business,
            created_at__date=today,
            status='delivered'
        )
        today_earnings = sum(
            o.business_earnings for o in today_orders
        )

        # This week
        week_start   = today - timedelta(days=today.weekday())
        week_orders  = Order.objects.filter(
            business=business,
            created_at__date__gte=week_start,
            status='delivered'
        )
        week_earnings = sum(
            o.business_earnings for o in week_orders
        )

        # This month
        month_start  = today.replace(day=1)
        month_orders = Order.objects.filter(
            business=business,
            created_at__date__gte=month_start,
            status='delivered'
        )
        month_earnings = sum(
            o.business_earnings for o in month_orders
        )

        # Pending withdrawals
        pending_wd = VendorWithdrawalRequest.objects.filter(
            business=business,
            status__in=['pending', 'under_review', 'approved']
        )

        # Recent transactions
        recent_txns = wallet.transactions.all()[:10]

        from .serializers import (
            VendorTransactionSerializer,
            VendorWalletSerializer,
        )

        return api_response(
            'success',
            'Earnings summary retrieved successfully',
            data={
                'wallet': VendorWalletSerializer(wallet).data,
                'earnings': {
                    'today': str(today_earnings),
                    'this_week': str(week_earnings),
                    'this_month': str(month_earnings),
                    'today_orders': today_orders.count(),
                    'week_orders': week_orders.count(),
                    'month_orders': month_orders.count(),
                },
                'withdrawals': {
                    'pending_count': pending_wd.count(),
                    'pending_amount': str(sum(
                        w.amount for w in pending_wd
                    )),
                },
                'recent_transactions': VendorTransactionSerializer(
                    recent_txns, many=True
                ).data,
            }
        )


class SettlePendingEarningsView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, business_id):
        from apps.marketplace.models import Business
        try:
            business = Business.objects.get(pk=business_id)
        except Business.DoesNotExist:
            return api_response(
                'error', 'Business not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        wallet = get_or_create_vendor_wallet(business)

        # Force settle ignores settlement_due date
        force = request.data.get('force', False)

        if force:
            from apps.wallet.models import VendorTransaction
            from decimal import Decimal

            eligible = VendorTransaction.objects.filter(
                vendor_wallet=wallet,
                transaction_type='earning',
                status='pending',
            )
            total_settled = Decimal('0')
            for txn in eligible:
                total_settled += txn.amount
                txn.status = 'success'
                txn.save()

            if total_settled > 0:
                wallet.pending_balance -= total_settled
                wallet.available_balance += total_settled
                wallet.save()

            settled = total_settled
        else:
            settled = wallet.settle_pending()

        from .serializers import VendorWalletSerializer
        return api_response(
            'success',
            f'₦{settled} settled to available balance',
            data=VendorWalletSerializer(wallet).data
        )

class AdminResolveWithdrawalView(APIView):
    """
    Admin manually resolves a stuck withdrawal
    (processing/approved that never got webhook confirmation)
    """
    permission_classes = [IsAdmin]

    def patch(self, request, pk):
        try:
            withdrawal = VendorWithdrawalRequest.objects.get(
                pk=pk
            )
        except VendorWithdrawalRequest.DoesNotExist:
            return api_response(
                'error', 'Withdrawal not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        if withdrawal.status not in [
            'pending', 'under_review',
            'approved', 'processing'
        ]:
            return api_response(
                'error',
                f'Cannot resolve a {withdrawal.status} '
                f'withdrawal. Already final.',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        action = request.data.get('action')  # complete | fail
        reason = request.data.get('reason', '')

        if action == 'complete':
            withdrawal.mark_completed(
                gateway_ref=withdrawal.gateway_reference or ''
            )
            return api_response(
                'success',
                f'Withdrawal {withdrawal.reference} '
                f'marked as completed',
                data=VendorWithdrawalRequestSerializer(
                    withdrawal
                ).data
            )

        elif action == 'fail':
            wallet = withdrawal.vendor_wallet

            # Release reserved amount back if still reserved
            if withdrawal.status in [
                'approved', 'processing'
            ]:
                wallet.reserved_balance  -= withdrawal.amount
                wallet.available_balance += withdrawal.amount
                wallet.total_withdrawn   -= withdrawal.amount
                wallet.save()

                VendorTransaction.objects.create(
                    vendor_wallet=wallet,
                    transaction_type='release',
                    amount=withdrawal.amount,
                    available_balance_after=(
                        wallet.available_balance
                    ),
                    pending_balance_after=(
                        wallet.pending_balance
                    ),
                    description=(
                        f'Admin resolved failed withdrawal - '
                        f'{withdrawal.reference}'
                    ),
                    reference=generate_reference('TREV'),
                    status='success',
                )

            withdrawal.status         = 'failed'
            withdrawal.failure_reason = (
                reason or 'Manually resolved by admin'
            )
            withdrawal.save()

            from apps.notifications.utils import send_notification
            send_notification(
                user=withdrawal.vendor,
                title='Withdrawal Failed ❌',
                message=(
                    f'Your withdrawal of '
                    f'₦{withdrawal.net_amount} failed. '
                    f'Amount has been returned to your wallet.'
                ),
                notification_type='system',
                data={'withdrawal_id': withdrawal.id}
            )

            return api_response(
                'success',
                f'Withdrawal {withdrawal.reference} '
                f'marked as failed, amount reversed',
                data=VendorWithdrawalRequestSerializer(
                    withdrawal
                ).data
            )

        return api_response(
            'error',
            'Invalid action. Use "complete" or "fail".',
            http_status=status.HTTP_400_BAD_REQUEST
        )