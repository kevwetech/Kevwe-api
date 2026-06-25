from django.db import models
from django.conf import settings
from apps.common.models import TimeStampedModel


class CommissionRule(TimeStampedModel):
    """
    Platform commission rules
    Can be set globally, per industry or per business
    """
    RULE_TYPE_CHOICES = (
        ('global', 'Global'),
        ('industry', 'Per Industry'),
        ('business', 'Per Business'),
    )

    CALCULATION_TYPE_CHOICES = (
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
        ('percentage_with_min', 'Percentage with Minimum'),
        ('percentage_with_max', 'Percentage with Maximum'),
        ('tiered', 'Tiered'),
    )

    name = models.CharField(max_length=255)
    rule_type = models.CharField(
        max_length=20,
        choices=RULE_TYPE_CHOICES,
        default='global'
    )
    calculation_type = models.CharField(
        max_length=30,
        choices=CALCULATION_TYPE_CHOICES,
        default='percentage'
    )

    # Targets
    industry = models.ForeignKey(
        'marketplace.Industry',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='commission_rules'
    )
    business = models.ForeignKey(
        'marketplace.Business',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='commission_rules'
    )

    # Commission rates
    platform_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=10.00
    )
    vendor_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=70.00
    )
    driver_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=20.00
    )

    # Fixed amounts
    platform_fixed = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    min_platform_commission = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    max_platform_commission = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )

    # Delivery commission
    delivery_platform_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=20.00
    )
    delivery_driver_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=80.00
    )

    # Tiered rates
    tiered_rates = models.JSONField(
        default=list,
        blank=True
    )

    # Currency
    currency = models.CharField(
        max_length=10,
        default='NGN'
    )
    currency_symbol = models.CharField(
        max_length=5,
        default='₦'
    )

    # Settlement period
    settlement_period_days = models.IntegerField(
        default=7
    )  # days after transaction before payout
    auto_settle = models.BooleanField(default=False)

    # Tax
    tax_inclusive = models.BooleanField(default=False)
    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )  # VAT percentage e.g 7.5 for Nigeria

    # Validity
    valid_from = models.DateTimeField(
        null=True,
        blank=True
    )
    valid_until = models.DateTimeField(
        null=True,
        blank=True
    )

    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='commission_rules'
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.rule_type})"

    def clean(self):
        """Validation"""
        from django.core.exceptions import ValidationError
        from decimal import Decimal

        # Rates must add up to 100%
        total = (
            Decimal(str(self.platform_rate)) +
            Decimal(str(self.vendor_rate)) +
            Decimal(str(self.driver_rate))
        )
        if total != Decimal('100.00'):
            raise ValidationError(
                f'Commission rates must add up to 100%. '
                f'Current total: {total}%'
            )

        # Rule type validations
        if self.rule_type == 'industry' and not self.industry:
            raise ValidationError(
                'Industry is required for industry-type rules'
            )
        if self.rule_type == 'business' and not self.business:
            raise ValidationError(
                'Business is required for business-type rules'
            )

        # Tiered validation
        if self.calculation_type == 'tiered':
            if not self.tiered_rates:
                raise ValidationError(
                    'Tiered rates are required for tiered calculation'
                )
            for tier in self.tiered_rates:
                if 'min' not in tier or 'rate' not in tier:
                    raise ValidationError(
                        'Each tier must have min and rate fields'
                    )

        # Valid date range
        if self.valid_from and self.valid_until:
            if self.valid_from >= self.valid_until:
                raise ValidationError(
                    'valid_from must be before valid_until'
                )

        # Tax rate range
        if self.tax_rate < 0 or self.tax_rate > 100:
            raise ValidationError(
                'Tax rate must be between 0 and 100'
            )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    @property
    def is_valid_now(self):
        """Check if rule is valid at current time"""
        from django.utils import timezone
        now = timezone.now()
        if not self.is_active:
            return False
        if self.valid_from and now < self.valid_from:
            return False
        if self.valid_until and now > self.valid_until:
            return False
        return True

    def calculate(self, amount):
        """Calculate commission splits for a given amount"""
        from decimal import Decimal
        amount = Decimal(str(amount))

        # Extract tax if inclusive
        tax_amount = Decimal('0')
        taxable_amount = amount
        if self.tax_inclusive and self.tax_rate > 0:
            tax_rate = Decimal(str(self.tax_rate)) / 100
            tax_amount = amount * tax_rate / (1 + tax_rate)
            taxable_amount = amount - tax_amount

        if self.calculation_type == 'percentage':
            platform = taxable_amount * (
                Decimal(str(self.platform_rate)) / 100
            )
            vendor = taxable_amount * (
                Decimal(str(self.vendor_rate)) / 100
            )
            driver = taxable_amount * (
                Decimal(str(self.driver_rate)) / 100
            )

        elif self.calculation_type == 'fixed':
            platform = Decimal(str(self.platform_fixed))
            vendor = taxable_amount - platform
            driver = Decimal('0')

        elif self.calculation_type == 'percentage_with_min':
            platform = max(
                taxable_amount *
                Decimal(str(self.platform_rate)) / 100,
                Decimal(str(self.min_platform_commission))
            )
            vendor = taxable_amount - platform
            driver = Decimal('0')

        elif self.calculation_type == 'percentage_with_max':
            platform = min(
                taxable_amount *
                Decimal(str(self.platform_rate)) / 100,
                Decimal(str(
                    self.max_platform_commission or 999999
                ))
            )
            vendor = taxable_amount - platform
            driver = Decimal('0')

        elif self.calculation_type == 'tiered':
            rate = self._get_tiered_rate(taxable_amount)
            platform = taxable_amount * Decimal(str(rate)) / 100
            vendor = taxable_amount - platform
            driver = Decimal('0')

        else:
            platform = taxable_amount * Decimal('0.10')
            vendor = taxable_amount * Decimal('0.70')
            driver = taxable_amount * Decimal('0.20')

        return {
            'amount': amount,
            'taxable_amount': taxable_amount,
            'tax_amount': round(tax_amount, 2),
            'platform': round(platform, 2),
            'vendor': round(vendor, 2),
            'driver': round(driver, 2),
            'platform_rate': self.platform_rate,
            'vendor_rate': self.vendor_rate,
            'driver_rate': self.driver_rate,
            'currency': self.currency,
            'currency_symbol': self.currency_symbol,
        }

    def _get_tiered_rate(self, amount):
        from decimal import Decimal
        amount = float(amount)
        for tier in self.tiered_rates:
            min_val = tier.get('min', 0)
            max_val = tier.get('max')
            if amount >= min_val:
                if max_val is None or amount < max_val:
                    return Decimal(str(tier['rate']))
        return Decimal(str(self.platform_rate))


class Commission(TimeStampedModel):
    """
    Commission record for each transaction
    """
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('settled', 'Settled'),
        ('paid', 'Paid'),
        ('reversed', 'Reversed'),
        ('disputed', 'Disputed'),
        ('adjusted', 'Adjusted'),
    )

    TRANSACTION_TYPE_CHOICES = (
        ('order', 'Order'),
        ('delivery', 'Delivery'),
        ('shipment', 'Shipment'),
        ('ride', 'Ride'),
        ('booking', 'Booking'),
        ('subscription', 'Subscription'),
        ('other', 'Other'),
    )

    REFUND_STATUS_CHOICES = (
        ('none', 'No Refund'),
        ('partial', 'Partial Refund'),
        ('full', 'Full Refund'),
    )

    # Rule used
    rule = models.ForeignKey(
        CommissionRule,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='commissions'
    )

    # Who is involved
    business = models.ForeignKey(
        'marketplace.Business',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='commissions'
    )
    vendor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='vendor_commissions'
    )
    driver = models.ForeignKey(
        'drivers.DriverProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='driver_commissions'
    )

    # Transaction linking
    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPE_CHOICES,
        default='order'
    )
    order = models.OneToOneField(
        'orders.Order',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='commission'
    )
    # Generic transaction linking for other types
    transaction_id = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )
    transaction_reference = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    # Payment link
    payment = models.ForeignKey(
        'payments.Payment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='commissions'
    )
    payment_reference = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )
    payment_gateway = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )  # paystack, flutterwave, wallet

    reference = models.CharField(
        max_length=100,
        unique=True
    )

    # Currency
    currency = models.CharField(
        max_length=10,
        default='NGN'
    )
    currency_symbol = models.CharField(
        max_length=5,
        default='₦'
    )
    exchange_rate = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=1.0000
    )  # for multi-currency support

    # Amounts
    gross_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )
    delivery_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    # Tax fields
    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )
    tax_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    tax_inclusive = models.BooleanField(default=False)

    # Commission splits
    platform_commission = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    vendor_earnings = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    driver_earnings = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    # Rates used
    platform_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )
    vendor_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )
    driver_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )

    # Refund tracking
    refund_status = models.CharField(
        max_length=10,
        choices=REFUND_STATUS_CHOICES,
        default='none'
    )
    refund_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    refunded_platform = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    refunded_vendor = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    refunded_driver = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    refunded_at = models.DateTimeField(
        null=True,
        blank=True
    )
    refund_reason = models.TextField(
        blank=True,
        null=True
    )

    # Settlement
    settlement_due_date = models.DateTimeField(
        null=True,
        blank=True
    )
    settled_at = models.DateTimeField(
        null=True,
        blank=True
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    # Payout tracking
    vendor_paid_at = models.DateTimeField(
        null=True,
        blank=True
    )
    driver_paid_at = models.DateTimeField(
        null=True,
        blank=True
    )

    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Commission {self.reference} - {self.currency_symbol}{self.platform_commission}"

    @property
    def net_platform_revenue(self):
        return self.platform_commission - self.refunded_platform

    @property
    def net_vendor_earnings(self):
        return self.vendor_earnings - self.refunded_vendor

    @property
    def net_driver_earnings(self):
        return self.driver_earnings - self.refunded_driver

    @property
    def total_payouts(self):
        return self.vendor_earnings + self.driver_earnings

    @property
    def is_settled(self):
        return self.status in ['settled', 'paid']

    def process_refund(self, refund_amount, reason=''):
        """Process a refund and adjust commission splits"""
        from decimal import Decimal
        from django.utils import timezone

        refund_amount = Decimal(str(refund_amount))

        if refund_amount >= self.gross_amount:
            # Full refund
            self.refund_status = 'full'
            self.refunded_platform = self.platform_commission
            self.refunded_vendor = self.vendor_earnings
            self.refunded_driver = self.driver_earnings
        else:
            # Partial refund
            self.refund_status = 'partial'
            ratio = refund_amount / self.gross_amount
            self.refunded_platform = round(
                self.platform_commission * ratio, 2
            )
            self.refunded_vendor = round(
                self.vendor_earnings * ratio, 2
            )
            self.refunded_driver = round(
                self.driver_earnings * ratio, 2
            )

        self.refund_amount = refund_amount
        self.refunded_at = timezone.now()
        self.refund_reason = reason
        self.status = 'reversed'
        self.save()


class CommissionAdjustment(TimeStampedModel):
    """
    Manual adjustments to commission records
    e.g bonus, penalty, correction
    """
    ADJUSTMENT_TYPE_CHOICES = (
        ('bonus', 'Bonus'),
        ('penalty', 'Penalty'),
        ('correction', 'Correction'),
        ('refund_adjustment', 'Refund Adjustment'),
        ('dispute_resolution', 'Dispute Resolution'),
        ('promotional', 'Promotional'),
        ('other', 'Other'),
    )

    APPLIES_TO_CHOICES = (
        ('platform', 'Platform'),
        ('vendor', 'Vendor'),
        ('driver', 'Driver'),
        ('all', 'All Parties'),
    )

    commission = models.ForeignKey(
        Commission,
        on_delete=models.CASCADE,
        related_name='adjustments'
    )
    adjustment_type = models.CharField(
        max_length=25,
        choices=ADJUSTMENT_TYPE_CHOICES
    )
    applies_to = models.CharField(
        max_length=10,
        choices=APPLIES_TO_CHOICES,
        default='vendor'
    )

    # Adjustment amounts
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    # positive = credit, negative = debit
    platform_adjustment = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    vendor_adjustment = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    driver_adjustment = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    reason = models.TextField()
    reference = models.CharField(
        max_length=100,
        unique=True
    )

    # Who approved
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='requested_adjustments'
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_adjustments'
    )
    approved_at = models.DateTimeField(
        null=True,
        blank=True
    )
    is_approved = models.BooleanField(default=False)

    # Applied
    is_applied = models.BooleanField(default=False)
    applied_at = models.DateTimeField(
        null=True,
        blank=True
    )

    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.adjustment_type} on {self.commission.reference} - {self.amount}"

    def apply(self):
        """Apply adjustment to commission"""
        from django.utils import timezone

        if self.is_applied:
            return False

        commission = self.commission

        # Apply adjustments
        commission.platform_commission += self.platform_adjustment
        commission.vendor_earnings += self.vendor_adjustment
        commission.driver_earnings += self.driver_adjustment
        commission.status = 'adjusted'
        commission.save()

        self.is_applied = True
        self.applied_at = timezone.now()
        self.save()

        return True


class CommissionPayout(TimeStampedModel):
    """
    Track payouts to vendors and drivers
    """
    PAYOUT_TYPE_CHOICES = (
        ('vendor', 'Vendor'),
        ('driver', 'Driver'),
    )

    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('reversed', 'Reversed'),
    )

    payout_type = models.CharField(
        max_length=10,
        choices=PAYOUT_TYPE_CHOICES
    )

    # Recipient
    vendor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='commission_payouts'
    )
    driver = models.ForeignKey(
        'drivers.DriverProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='commission_payouts'
    )
    business = models.ForeignKey(
        'marketplace.Business',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payouts'
    )

    # Commissions included
    commissions = models.ManyToManyField(
        Commission,
        blank=True,
        related_name='payouts'
    )

    # Currency
    currency = models.CharField(
        max_length=10,
        default='NGN'
    )

    # Amount
    total_amount = models.DecimalField(
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

    # Settlement period
    settlement_period_start = models.DateTimeField(
        null=True,
        blank=True
    )
    settlement_period_end = models.DateTimeField(
        null=True,
        blank=True
    )

    # Bank details
    bank_name = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )
    account_number = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )
    account_name = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    # Reference
    reference = models.CharField(
        max_length=100,
        unique=True
    )
    gateway_reference = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='processed_payouts'
    )
    processed_at = models.DateTimeField(
        null=True,
        blank=True
    )
    failure_reason = models.TextField(
        blank=True,
        null=True
    )
    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Payout {self.reference} - {self.currency} {self.net_amount}"


class CommissionDispute(TimeStampedModel):
    """
    Disputes raised by vendors or drivers
    """
    STATUS_CHOICES = (
        ('open', 'Open'),
        ('under_review', 'Under Review'),
        ('resolved', 'Resolved'),
        ('rejected', 'Rejected'),
    )

    commission = models.ForeignKey(
        Commission,
        on_delete=models.CASCADE,
        related_name='disputes'
    )
    raised_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='commission_disputes'
    )
    reason = models.TextField()
    expected_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='open'
    )
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_disputes'
    )
    resolution_notes = models.TextField(
        blank=True,
        null=True
    )
    resolved_at = models.DateTimeField(
        null=True,
        blank=True
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Dispute on {self.commission.reference}"