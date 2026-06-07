from django.db import models
from django.conf import settings
from apps.common.models import TimeStampedModel
from decimal import Decimal


class Wallet(TimeStampedModel):
    """User wallet"""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='wallet'
    )
    balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00
    )
    total_credited = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00
    )
    total_debited = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00
    )
    is_active = models.BooleanField(default=True)
    pin = models.CharField(
        max_length=6,
        blank=True,
        null=True
    )
    is_pin_set = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} - ₦{self.balance}"

    def credit(self, amount, description, reference):
        """Add money to wallet"""
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
        """Remove money from wallet"""

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
        max_length=20,
        choices=TRANSACTION_TYPE_CHOICES
    )
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default='payment'
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )
    balance_after = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )
    description = models.TextField()
    reference = models.CharField(
        max_length=100,
        unique=True
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    metadata = models.JSONField(
        blank=True,
        null=True
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.wallet.user.email} - {self.transaction_type} - ₦{self.amount}"


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

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.account_name} - {self.account_number}"


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
        max_digits=12,
        decimal_places=2
    )
    fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    net_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )
    reference = models.CharField(
        max_length=100,
        unique=True
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    gateway_reference = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )
    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} - ₦{self.amount}"