from django.db import models
from django.conf import settings
from apps.common.models import TimeStampedModel


class Payment(TimeStampedModel):
    GATEWAY_CHOICES = (
        ('paystack', 'Paystack'),
        ('flutterwave', 'Flutterwave'),
    )

    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
        ('cancelled', 'Cancelled'),
    )

    PAYMENT_FOR_CHOICES = (
        ('order', 'Order'),
        ('booking', 'Booking'),
        ('ride', 'Ride'),
        ('shipment', 'Shipment'),
        ('wallet', 'Wallet'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='payments'
    )

    # Payment details
    reference = models.CharField(max_length=100, unique=True)
    gateway = models.CharField(
        max_length=20,
        choices=GATEWAY_CHOICES
    )
    gateway_reference = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    # What is being paid for
    payment_for = models.CharField(
        max_length=20,
        choices=PAYMENT_FOR_CHOICES
    )
    object_id = models.IntegerField(
        null=True,
        blank=True
    )

    # Amount
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    currency = models.CharField(
        max_length=10,
        default='NGN'
    )

    # Extra data
    metadata = models.JSONField(
        blank=True,
        null=True
    )
    failure_reason = models.TextField(
        blank=True,
        null=True
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.reference} - {self.status}"





class PaymentModel(TimeStampedModel):
    PAYMENT_MODEL_CHOICES = [
        ('marketplace', 'Marketplace'),
        ('logistics', 'Logistics'),
    ]

    name = models.CharField(
        max_length=20,
        choices=PAYMENT_MODEL_CHOICES,
        unique=True
    )
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class EscrowTransaction(TimeStampedModel):
    """
    Universal escrow record for ALL interaction types.
    Funds locked on payment → released on verification event.
    """
    STATUS_CHOICES = (
        ('held',      'Held in Escrow'),
        ('released',  'Released to Vendor'),
        ('refunded',  'Refunded to Customer'),
        ('disputed',  'In Dispute'),
    )
    INTERACTION_CHOICES = (
        ('order',             'Order'),
        ('booking',           'Booking'),
        ('service',           'Service'),
        ('appointment',       'Appointment'),
        ('scheduled_service', 'Scheduled Service'),
        ('ride',              'Ride'),
        ('shipment',          'Shipment'),
        ('transport',         'Transport'),
    )
    RELEASE_TRIGGER_CHOICES = (
        ('delivery_otp',        'Delivery OTP Verified'),
        ('check_in',            'Check-in Code Verified'),
        ('completion_otp',      'Completion OTP Verified'),
        ('ride_start',          'Ride Start Code Verified'),
        ('ride_completed',      'Ride Completed'),
        ('boarding',            'Passenger Boarded'),
        ('auto_release',        'Auto-released After Deadline'),
        ('manual',              'Manually Released by Admin'),
    )
    STATUS_CHOICES = (
        ('held',      'Held in Escrow'),
        ('released',  'Released to Vendor'),
        ('refunded',  'Refunded to Customer'),
        ('disputed',  'In Dispute'),
        ('cancelled', 'Cancelled'),
        ('expired',   'Expired'),
    )

    reference        = models.CharField(max_length=30, unique=True)
    interaction_type = models.CharField(max_length=30, choices=INTERACTION_CHOICES)
    interaction_id   = models.IntegerField(help_text='PK of the order/booking/ride etc.')
    interaction_ref  = models.CharField(max_length=50, blank=True, null=True)

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='escrow_payments',
    )
    business = models.ForeignKey(
        'marketplace.Business',
        on_delete=models.PROTECT,
        related_name='escrow_transactions',
        null=True, blank=True,
    )

    amount            = models.DecimalField(max_digits=12, decimal_places=2)
    commission_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    vendor_amount     = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    status          = models.CharField(max_length=20, choices=STATUS_CHOICES, default='held')
    release_trigger = models.CharField(max_length=30, choices=RELEASE_TRIGGER_CHOICES, blank=True, null=True)

    held_at      = models.DateTimeField(auto_now_add=True)
    released_at  = models.DateTimeField(null=True, blank=True)
    refunded_at  = models.DateTimeField(null=True, blank=True)
    auto_release_at = models.DateTimeField(
        null=True, blank=True,
        help_text='Funds auto-release at this time if no dispute'
    )

    payment = models.ForeignKey(
        'payments.Payment',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='escrow_transactions',
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['interaction_type', 'interaction_id']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.reference} — {self.interaction_type} #{self.interaction_id} ({self.status})"

    def save(self, *args, **kwargs):
        import uuid
        if not self.reference:
            self.reference = f'ESC-{uuid.uuid4().hex[:8].upper()}'
        super().save(*args, **kwargs)

class EscrowLog(TimeStampedModel):
    """Audit trail for every escrow state transition."""
    escrow = models.ForeignKey(
        EscrowTransaction,
        on_delete=models.CASCADE,
        related_name='logs',
    )
    from_status = models.CharField(max_length=20)
    to_status   = models.CharField(max_length=20)
    trigger     = models.CharField(max_length=30, blank=True, null=True)
    actor       = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        help_text='Who triggered the transition',
    )
    ip_address  = models.GenericIPAddressField(null=True, blank=True)
    notes       = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.escrow.reference}: {self.from_status} → {self.to_status}"