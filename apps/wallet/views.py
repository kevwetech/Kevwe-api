from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from django.db import transaction
from apps.common.views import api_response
from apps.common.permissions import IsAdmin
from apps.common.utils import generate_reference
from .models import Wallet, WalletTransaction, BankAccount, WithdrawalRequest
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
                from apps.payments.paystack import initialize_payment
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
                from apps.payments.flutterwave import initialize_payment
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
            from apps.payments.paystack import verify_payment
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
            from apps.notifications.utils import send_notification
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
            from apps.notifications.utils import send_notification
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
        if serializer.is_valid():
            # Verify account with Paystack
            from apps.payments.paystack import verify_account
            result = verify_account(
                serializer.validated_data['account_number'],
                serializer.validated_data['bank_code']
            )

            account_name = serializer.validated_data.get('account_name', '')
            is_verified = False

            if result.get('status'):
                account_name = result['data']['account_name']
                is_verified = True

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

        return api_response(
            'error',
            'Failed to add bank account',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
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
            from apps.notifications.utils import send_notification
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
        from apps.notifications.utils import send_notification
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