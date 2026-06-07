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