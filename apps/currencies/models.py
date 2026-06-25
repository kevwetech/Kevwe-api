from django.db import models
from apps.common.models import TimeStampedModel


class Currency(TimeStampedModel):
    """
    Supported currencies with exchange rates to NGN.
    NGN is the base currency (rate=1).
    """
    RATE_SOURCE_CHOICES = (
        ('manual', 'Manual'),
        ('api', 'Auto API'),
        ('override', 'Manual Override'),
    )

    code = models.CharField(
        max_length=3, unique=True
    )  # e.g. NGN, USD, GBP
    name = models.CharField(
        max_length=100, blank=True, default=''
    )
    symbol = models.CharField(
        max_length=5, blank=True, default=''
    )
    country = models.CharField(
        max_length=100, blank=True, default='',
        help_text='Country this currency belongs to e.g. Nigeria'
    )
    rate_to_ngn = models.DecimalField(
        max_digits=18,
        decimal_places=8,
        default=1.0,
        help_text='How many NGN does 1 unit of this currency equal?'
    )
    convert_from_ngn = models.DecimalField(
        max_digits=18,
        decimal_places=8,
        default=1.0,
        help_text='How many units of this currency equals 1 NGN?'
    )
    preferred_currency = models.BooleanField(
        default=False,
        help_text=(
            'Mark as a preferred/featured currency '
            'shown prominently in the UI'
        )
    )
    rate_source = models.CharField(
        max_length=20,
        choices=RATE_SOURCE_CHOICES,
        default='manual',
        help_text='How the exchange rate was last set'
    )
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(
        default=False,
        help_text='Only one currency should be default (NGN)'
    )
    rate_updated_at = models.DateTimeField(null=True, blank=True)
    auto_update = models.BooleanField(
        default=True,
        help_text='Auto-fetch rate from exchange rate API'
    )
    manual_override = models.BooleanField(
        default=False,
        help_text='If True, auto-fetch is skipped for this currency'
    )

    class Meta:
        ordering = ['-is_default', '-preferred_currency', 'code']
        verbose_name_plural = 'Currencies'

    def __str__(self):
        return f"{self.code} ({self.symbol})"

    def to_ngn(self, amount):
        """Convert amount in this currency to NGN."""
        from decimal import Decimal
        return Decimal(str(amount)) * self.rate_to_ngn

    def from_ngn(self, amount_ngn):
        """Convert NGN amount to this currency."""
        from decimal import Decimal
        if self.rate_to_ngn == 0:
            return Decimal('0')
        return Decimal(str(amount_ngn)) / self.rate_to_ngn

    def save(self, *args, **kwargs):
        # Auto-calculate convert_from_ngn whenever rate_to_ngn changes
        from decimal import Decimal
        if self.rate_to_ngn and self.rate_to_ngn != 0:
            self.convert_from_ngn = (
                Decimal('1') / Decimal(str(self.rate_to_ngn))
            ).quantize(Decimal('0.00000001'))
        super().save(*args, **kwargs)


class CurrencyRateHistory(TimeStampedModel):
    """
    Tracks historical exchange rate changes per currency.
    Useful for auditing, analytics, and rate trend displays.
    """
    SOURCE_CHOICES = (
        ('manual', 'Manual'),
        ('api', 'Auto API'),
        ('override', 'Manual Override'),
    )

    currency = models.ForeignKey(
        Currency,
        on_delete=models.CASCADE,
        related_name='rate_history'
    )
    rate_to_ngn = models.DecimalField(
        max_digits=18,
        decimal_places=8
    )
    convert_from_ngn = models.DecimalField(
        max_digits=18,
        decimal_places=8,
        default=1.0
    )
    source = models.CharField(
        max_length=20,
        choices=SOURCE_CHOICES,
        default='api'
    )
    recorded_by = models.ForeignKey(
        'users.CustomUser',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='rate_updates',
        help_text='Admin who set this rate (null if auto)'
    )
    note = models.TextField(
        blank=True, null=True,
        help_text='Optional note about why rate was changed'
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Currency Rate History'

    def __str__(self):
        return (
            f"{self.currency.code} → {self.rate_to_ngn} NGN "
            f"({self.source})"
        )