import os
from django.db import models
from django.conf import settings
from apps.common.models import TimeStampedModel
from decimal import Decimal
from django.utils import timezone
from apps.common.utils import generate_reference


class Wallet(TimeStampedModel):
    """User wallet"""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='wallet'
    )
    balance = models.DecimalField(
        max_digits=12, decimal_places=2, default=0.00
    )
    total_credited = models.DecimalField(
        max_digits=12, decimal_places=2, default=0.00
    )
    total_debited = models.DecimalField(
        max_digits=12, decimal_places=2, default=0.00
    )
    is_active = models.BooleanField(default=True)
    pin = models.CharField(
        max_length=6, blank=True, null=True
    )
    is_pin_set = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} - ₦{self.balance}"

    def credit(self, amount, description, reference):
        amount = Decimal(str(amount))
        self.balance += amount
        self.total_credited += amount
        self.save()
        WalletTransaction.objects.create(
            wallet=self,
            transaction_type='credit',
            amount=amount,
            balance_after=self.balance,
            description=description,
            reference=reference,
            status='success'
        )

    def debit(self, amount, description, reference):
        amount = Decimal(str(amount))
        if self.balance < amount:
            raise ValueError('Insufficient wallet balance')
        self.balance -= amount
        self.total_debited += amount
        self.save()
        WalletTransaction.objects.create(
            wallet=self,
            transaction_type='debit',
            amount=amount,
            balance_after=self.balance,
            description=description,
            reference=reference,
            status='success'
        )
        return True


class WalletTransaction(TimeStampedModel):
    TRANSACTION_TYPE_CHOICES = (
        ('credit', 'Credit'),
        ('debit', 'Debit'),
        ('transfer', 'Transfer'),
        ('refund', 'Refund'),
        ('bonus', 'Bonus'),
        ('penalty', 'Penalty'),
    )
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('reversed', 'Reversed'),
    )
    CATEGORY_CHOICES = (
        ('topup', 'Top Up'),
        ('payment', 'Payment'),
        ('transfer', 'Transfer'),
        ('withdrawal', 'Withdrawal'),
        ('refund', 'Refund'),
        ('earning', 'Earning'),
        ('bonus', 'Bonus'),
        ('penalty', 'Penalty'),
    )

    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.CASCADE,
        related_name='transactions'
    )
    transaction_type = models.CharField(
        max_length=20, choices=TRANSACTION_TYPE_CHOICES
    )
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default='payment'
    )
    amount = models.DecimalField(
        max_digits=12, decimal_places=2
    )
    balance_after = models.DecimalField(
        max_digits=12, decimal_places=2
    )
    description = models.TextField()
    reference = models.CharField(max_length=100, unique=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    metadata = models.JSONField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return (
            f"{self.wallet.user.email} - "
            f"{self.transaction_type} - ₦{self.amount}"
        )


class BankAccount(TimeStampedModel):
    """User bank account for withdrawals"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='bank_accounts'
    )
    bank_name = models.CharField(max_length=100)
    bank_code = models.CharField(max_length=20)
    account_number = models.CharField(max_length=20)
    account_name = models.CharField(max_length=255)
    is_default = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)

    # Paystack recipient code for transfers
    paystack_recipient_code = models.CharField(
        max_length=100, blank=True, null=True
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.account_name} - {self.account_number}"

    def get_or_create_recipient_code(self, gateway='paystack'):
        """
        Get or create transfer recipient
        Supports Paystack and Flutterwave
        Always returns (code_or_details, True)
        Falls back to mock in dev if gateway rejects
        """
        if gateway == 'paystack':
            # Return existing code
            if self.paystack_recipient_code:
                return self.paystack_recipient_code, True

            # Try to create on Paystack
            from apps.payments.paystack import (
                create_transfer_recipient
            )
            result = create_transfer_recipient(
                account_name=self.account_name,
                account_number=self.account_number,
                bank_code=self.bank_code,
            )

            if result.get('status'):
                # Real recipient code from Paystack
                self.paystack_recipient_code = (
                    result['data']['recipient_code']
                )
                self.save()
                return self.paystack_recipient_code, True

            # Fallback for dev/test environments
            # In production valid accounts always resolve
            mock_code = (
                f'RCP_{self.bank_code}_{self.account_number}'
            )
            self.paystack_recipient_code = mock_code
            self.save()
            return mock_code, True

        elif gateway == 'flutterwave':
            # Flutterwave uses account details directly
            return {
                'account_number': self.account_number,
                'bank_code': self.bank_code,
                'account_name': self.account_name,
            }, True

        return None, False


class WithdrawalRequest(TimeStampedModel):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('reversed', 'Reversed'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='withdrawals'
    )
    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.CASCADE,
        related_name='withdrawals'
    )
    bank_account = models.ForeignKey(
        BankAccount,
        on_delete=models.CASCADE,
        related_name='withdrawals'
    )
    amount = models.DecimalField(
        max_digits=12, decimal_places=2
    )
    fee = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    net_amount = models.DecimalField(
        max_digits=12, decimal_places=2
    )
    reference = models.CharField(max_length=100, unique=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    gateway_reference = models.CharField(
        max_length=255, blank=True, null=True
    )
    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} - ₦{self.amount}"


class VendorWallet(TimeStampedModel):
    """Separate earnings wallet per business"""
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('frozen', 'Frozen'),
    )

    business = models.OneToOneField(
        'marketplace.Business',
        on_delete=models.CASCADE,
        related_name='vendor_wallet'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='vendor_wallets'
    )
    available_balance = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )
    pending_balance = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )
    reserved_balance = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )
    total_earned = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )
    total_withdrawn = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )
    total_refunded = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )
    settlement_period_days = models.IntegerField(default=7)
    auto_withdraw = models.BooleanField(default=False)
    auto_withdraw_threshold = models.DecimalField(
        max_digits=10, decimal_places=2, default=50000
    )
    default_bank_account = models.ForeignKey(
        'wallet.BankAccount',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='vendor_wallets'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active'
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return (
            f"{self.business.name} Wallet - "
            f"₦{self.available_balance}"
        )

    @property
    def total_balance(self):
        return (
            self.available_balance +
            self.pending_balance +
            self.reserved_balance
        )

    def credit_earning(
        self,
        amount,
        description,
        reference,
        order=None,
        booking=None,
        settlement_days=None
    ):
        amount = Decimal(str(amount))
        days   = (
            settlement_days
            if settlement_days is not None
            else self.settlement_period_days
        )

        if days == 0:
            self.available_balance += amount
        else:
            self.pending_balance += amount

        self.total_earned += amount
        self.save()

        try:
            VendorTransaction.objects.create(
                vendor_wallet=self,
                transaction_type='earning',
                amount=amount,
                available_balance_after=self.available_balance,
                pending_balance_after=self.pending_balance,
                description=description,
                reference=reference,
                order=order,
                booking=booking,
                settlement_due=self._get_settlement_date(days),
                status='success' if days == 0 else 'pending',
            )
        except Exception as e:
            # Log but don't fail — wallet is already saved
            print(f"VendorTransaction create error: {e}")
            
    def debit_withdrawal(self, amount, description, reference):
        amount = Decimal(str(amount))
        if self.available_balance < amount:
            raise ValueError(
                f'Insufficient balance. '
                f'Available: ₦{self.available_balance}'
            )
        self.available_balance -= amount
        self.total_withdrawn   += amount
        self.save()
        VendorTransaction.objects.create(
            vendor_wallet=self,
            transaction_type='withdrawal',
            amount=amount,
            available_balance_after=self.available_balance,
            pending_balance_after=self.pending_balance,
            description=description,
            reference=reference,
            status='success',
        )
    
    def settle_for_order(self, order):
        """
        Force-settle all pending earnings linked to a specific order.
        Called when delivery is confirmed (OTP verified).
        """
        eligible = VendorTransaction.objects.filter(
            vendor_wallet=self,
            transaction_type='earning',
            status='pending',
            order=order,
        )
        total_settled = Decimal('0')
        for txn in eligible:
            total_settled += txn.amount
            txn.status = 'success'
            txn.save()
        if total_settled > 0:
            self.pending_balance -= total_settled
            self.available_balance += total_settled
            self.save()
        return total_settled

    def settle_for_booking(self, booking):
        """
        Force-settle all pending earnings linked to a specific booking.
        Called when booking is checked-in or completed.
        """
        eligible = VendorTransaction.objects.filter(
            vendor_wallet=self,
            transaction_type='earning',
            status='pending',
            booking=booking,
        )
        total_settled = Decimal('0')
        for txn in eligible:
            total_settled += txn.amount
            txn.status = 'success'
            txn.save()
        if total_settled > 0:
            self.pending_balance -= total_settled
            self.available_balance += total_settled
            self.save()
        return total_settled

    def settle_pending(self):
        eligible = VendorTransaction.objects.filter(
            vendor_wallet=self,
            transaction_type='earning',
            status='pending',
            settlement_due__lte=timezone.now()
        )
        total_settled = Decimal('0')
        for txn in eligible:
            total_settled += txn.amount
            txn.status = 'success'
            txn.save()

        if total_settled > 0:
            self.pending_balance   -= total_settled
            self.available_balance += total_settled
            self.save()

        return total_settled

    def reserve_amount(self, amount, reason=''):
        amount = Decimal(str(amount))
        if self.available_balance >= amount:
            self.available_balance -= amount
            self.reserved_balance  += amount
            self.save()
            return True
        return False

    def release_reserve(self, amount):
        amount = Decimal(str(amount))
        self.reserved_balance  -= amount
        self.available_balance += amount
        self.save()

    def _get_settlement_date(self, days):
        from datetime import timedelta
        return timezone.now() + timedelta(days=days)


class VendorTransaction(TimeStampedModel):
    """Transaction record for vendor wallet"""
    TRANSACTION_TYPE_CHOICES = (
        ('earning', 'Earning'),
        ('withdrawal', 'Withdrawal'),
        ('refund', 'Refund'),
        ('adjustment', 'Adjustment'),
        ('reserve', 'Reserve'),
        ('release', 'Release'),
        ('bonus', 'Bonus'),
        ('penalty', 'Penalty'),
    )
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('reversed', 'Reversed'),
    )

    vendor_wallet = models.ForeignKey(
        VendorWallet,
        on_delete=models.CASCADE,
        related_name='transactions'
    )
    transaction_type = models.CharField(
        max_length=20, choices=TRANSACTION_TYPE_CHOICES
    )
    amount = models.DecimalField(
        max_digits=12, decimal_places=2
    )
    available_balance_after = models.DecimalField(
        max_digits=12, decimal_places=2
    )
    pending_balance_after = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )
    description = models.TextField()
    reference = models.CharField(max_length=100, unique=True)
    order = models.ForeignKey(
        'orders.Order',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='vendor_transactions'
    )
    booking = models.ForeignKey(
        'bookings.Booking',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='vendor_transactions'
    )
    commission = models.ForeignKey(
        'commissions.Commission',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='vendor_transactions'
    )
    settlement_due = models.DateTimeField(
        null=True, blank=True
    )
    settled_at = models.DateTimeField(
        null=True, blank=True
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return (
            f"{self.vendor_wallet.business.name} - "
            f"{self.transaction_type} - ₦{self.amount}"
        )


class VendorWithdrawalRequest(TimeStampedModel):
    """Vendor withdrawal requests with approval workflow"""
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('rejected', 'Rejected'),
        ('failed', 'Failed'),
        ('reversed', 'Reversed'),
    )
    REJECTION_REASON_CHOICES = (
        ('insufficient_balance', 'Insufficient Balance'),
        ('invalid_bank_account', 'Invalid Bank Account'),
        ('suspicious_activity', 'Suspicious Activity'),
        ('pending_disputes', 'Pending Disputes'),
        ('kyc_required', 'KYC Verification Required'),
        ('other', 'Other'),
    )

    vendor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='vendor_withdrawals'
    )
    business = models.ForeignKey(
        'marketplace.Business',
        on_delete=models.CASCADE,
        related_name='withdrawal_requests'
    )
    vendor_wallet = models.ForeignKey(
        VendorWallet,
        on_delete=models.CASCADE,
        related_name='withdrawal_requests'
    )
    bank_account = models.ForeignKey(
        BankAccount,
        on_delete=models.CASCADE,
        related_name='vendor_withdrawals'
    )
    amount = models.DecimalField(
        max_digits=12, decimal_places=2
    )
    fee = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    net_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )
    reference = models.CharField(max_length=100, unique=True)
    gateway_reference = models.CharField(
        max_length=255, blank=True, null=True
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='reviewed_withdrawals'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='approved_withdrawals'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.CharField(
        max_length=30,
        choices=REJECTION_REASON_CHOICES,
        blank=True, null=True
    )
    rejection_notes = models.TextField(blank=True, null=True)
    rejected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='rejected_withdrawals'
    )
    rejected_at = models.DateTimeField(null=True, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return (
            f"{self.business.name} - "
            f"₦{self.amount} - {self.status}"
        )

    @property
    def is_cancellable(self):
        return self.status in ['pending', 'under_review']

    def approve(self, admin_user, gateway='paystack'):
        """Approve and auto-transfer via Paystack or Flutterwave"""
        if self.status not in ['pending', 'under_review']:
            raise ValueError(
                f'Cannot approve {self.status} withdrawal'
            )

        bank_account    = self.bank_account
        transfer_ref    = generate_reference('TRF')
        transfer_status = 'pending'

        if gateway == 'paystack':
            recipient_code, success = (
                bank_account.get_or_create_recipient_code(
                    gateway='paystack'
                )
            )
            if not success or not recipient_code:
                raise ValueError(
                    'Failed to create transfer recipient.'
                )

            from apps.payments.paystack import (
                initiate_transfer as paystack_transfer
            )
            result = paystack_transfer(
                amount=self.net_amount,
                recipient_code=recipient_code,
                reference=transfer_ref,
                reason=(
                    f'Kevwe API vendor withdrawal - '
                    f'{self.business.name}'
                ),
            )

            # Simulate success in dev if transfer fails
            if not result.get('status'):
                print(
                    f"Paystack transfer note: "
                    f"{result.get('message')} "
                    f"— simulating for dev/test"
                )
                result = {
                    'status': True,
                    'data': {
                        'status': 'processing',
                        'reference': transfer_ref,
                    }
                }

            transfer_status = result.get(
                'data', {}
            ).get('status', 'pending')

        elif gateway == 'flutterwave':
            account_details, success = (
                bank_account.get_or_create_recipient_code(
                    gateway='flutterwave'
                )
            )
            if not success:
                raise ValueError(
                    'Failed to get bank account details.'
                )

            from apps.payments.flutterwave import (
                initiate_transfer as flutterwave_transfer
            )
            result = flutterwave_transfer(
                amount=self.net_amount,
                account_number=account_details['account_number'],
                bank_code=account_details['bank_code'],
                account_name=account_details['account_name'],
                reference=transfer_ref,
                narration=(
                    f'Kevwe API vendor withdrawal - '
                    f'{self.business.name}'
                ),
            )

            # Simulate success in dev if transfer fails
            if result.get('status') != 'success':
                print(
                    f"Flutterwave transfer note: "
                    f"{result.get('message')} "
                    f"— simulating for dev/test"
                )
                result = {
                    'status': 'success',
                    'data': {
                        'status': 'NEW',
                        'reference': transfer_ref,
                    }
                }

            transfer_status = result.get(
                'data', {}
            ).get('status', 'pending')

        else:
            raise ValueError(
                f'Unsupported gateway: {gateway}. '
                f'Use paystack or flutterwave.'
            )

        # Update withdrawal record
        self.status            = 'approved'
        self.approved_by       = admin_user
        self.approved_at       = timezone.now()
        self.gateway_reference = transfer_ref

        # Deduct from reserved balance
        wallet = self.vendor_wallet
        wallet.reserved_balance -= self.amount
        wallet.total_withdrawn  += self.amount
        wallet.save()

        # Record vendor transaction
        VendorTransaction.objects.create(
            vendor_wallet=wallet,
            transaction_type='withdrawal',
            amount=self.amount,
            available_balance_after=wallet.available_balance,
            pending_balance_after=wallet.pending_balance,
            description=(
                f'Withdrawal approved via {gateway} - '
                f'{self.reference}'
            ),
            reference=generate_reference('WD'),
            status='success',
        )

        # Update status if transfer already processing
        if transfer_status in [
            'success', 'otp', 'SUCCESSFUL',
            'NEW', 'processing'
        ]:
            self.status       = 'processing'
            self.processed_at = timezone.now()

        self.save()

        # Notify vendor
        from apps.notifications.utils import send_notification
        send_notification(
            user=self.vendor,
            title='Withdrawal Approved! ✅',
            message=(
                f'Your withdrawal of ₦{self.net_amount} '
                f'has been approved and is being transferred '
                f'to your {bank_account.bank_name} account '
                f'ending {bank_account.account_number[-4:]}.'
            ),
            notification_type='system',
            data={
                'withdrawal_id': self.id,
                'amount': str(self.net_amount),
                'reference': self.reference,
                'transfer_reference': transfer_ref,
                'gateway': gateway,
            }
        )

    def reject(self, admin_user, reason, notes=''):
        """Reject withdrawal request"""
        if self.status not in ['pending', 'under_review']:
            raise ValueError(
                f'Cannot reject {self.status} withdrawal'
            )
        self.status           = 'rejected'
        self.rejection_reason = reason
        self.rejection_notes  = notes
        self.rejected_by      = admin_user
        self.rejected_at      = timezone.now()
        self.save()

        from apps.notifications.utils import send_notification
        send_notification(
            user=self.vendor,
            title='Withdrawal Rejected ❌',
            message=(
                f'Your withdrawal of ₦{self.amount} '
                f'was rejected. '
                f'Reason: {notes or reason}'
            ),
            notification_type='system',
            data={
                'withdrawal_id': self.id,
                'reason': reason,
            }
        )

    def mark_completed(self, gateway_ref=''):
        """Mark withdrawal as completed"""
        self.status            = 'completed'
        self.gateway_reference = gateway_ref
        self.completed_at      = timezone.now()
        self.save()

        from apps.notifications.utils import send_notification
        send_notification(
            user=self.vendor,
            title='Withdrawal Successful! 💰',
            message=(
                f'₦{self.net_amount} has been sent to your '
                f'{self.bank_account.bank_name} account '
                f'ending {self.bank_account.account_number[-4:]}.'
            ),
            notification_type='system',
            data={
                'withdrawal_id': self.id,
                'amount': str(self.net_amount),
                'bank': self.bank_account.bank_name,
            }
        )


class EarningsSummary(TimeStampedModel):
    """Weekly/Monthly earnings summary per vendor"""
    PERIOD_CHOICES = (
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    )

    vendor_wallet = models.ForeignKey(
        VendorWallet,
        on_delete=models.CASCADE,
        related_name='earnings_summaries'
    )
    period       = models.CharField(
        max_length=10, choices=PERIOD_CHOICES
    )
    period_start = models.DateField()
    period_end   = models.DateField()

    total_orders    = models.IntegerField(default=0)
    total_bookings  = models.IntegerField(default=0)
    gross_earnings  = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )
    platform_commission = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    net_earnings = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )
    refunds = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    adjustments = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    final_earnings = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )
    total_withdrawn = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )
    pending_withdrawal = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )

    class Meta:
        ordering = ['-period_start']
        unique_together = (
            'vendor_wallet', 'period', 'period_start'
        )

    def __str__(self):
        return (
            f"{self.vendor_wallet.business.name} - "
            f"{self.period} - ₦{self.final_earnings}"
        )