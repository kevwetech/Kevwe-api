from django.db import models
from django.conf import settings
from apps.common.models import TimeStampedModel


class Country(TimeStampedModel):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=3, unique=True)  # e.g NG, US, GH
    phone_code = models.CharField(max_length=10, blank=True)  # e.g +234
    currency_code = models.CharField(
        max_length=10, blank=True
    )  # legacy/fallback e.g NGN
    currency_symbol = models.CharField(
        max_length=5, blank=True
    )  # legacy/fallback e.g ₦
    default_currency = models.ForeignKey(
        'currencies.Currency',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='countries'
    )
    flag = models.ImageField(
        upload_to='country_flags/',
        null=True,
        blank=True
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Countries'

    def __str__(self):
        return f"{self.name} ({self.code})"


class State(TimeStampedModel):
    country = models.ForeignKey(
        Country,
        on_delete=models.CASCADE,
        related_name='states'
    )
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10, blank=True)  # e.g LA, AB
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        unique_together = ('country', 'name')

    def __str__(self):
        return f"{self.name}, {self.country.name}"


class City(TimeStampedModel):
    state = models.ForeignKey(
        State,
        on_delete=models.CASCADE,
        related_name='cities'
    )
    name = models.CharField(max_length=100)
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6,
        null=True, blank=True
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6,
        null=True, blank=True
    )
    is_active = models.BooleanField(default=True)
    class Meta:
        ordering = ['name']
        unique_together = ('state', 'name')
        verbose_name_plural = 'Cities'

    def __str__(self):
        return f"{self.name}, {self.state.name}"


class Zone(TimeStampedModel):
    """
    A zone is a subdivision of a city
    Used for delivery pricing and territory management
    """
    city = models.ForeignKey(
        City,
        on_delete=models.CASCADE,
        related_name='zones'
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )
    radius_km = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=5.00
    )
    # Pricing multiplier for this zone
    price_multiplier = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=1.00
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        unique_together = ('city', 'name')

    def __str__(self):
        return f"{self.name} - {self.city.name}"


class Address(TimeStampedModel):
    """User saved addresses"""
    ADDRESS_TYPE_CHOICES = (
        ('home', 'Home'),
        ('work', 'Work'),
        ('other', 'Other'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='addresses'
    )
    address_type = models.CharField(
        max_length=20,
        choices=ADDRESS_TYPE_CHOICES,
        default='home'
    )
    label = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )  # e.g "Mom's House"

    # Location hierarchy
    country = models.ForeignKey(
        Country,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    state = models.ForeignKey(
        State,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    city = models.ForeignKey(
        City,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    zone = models.ForeignKey(
        Zone,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    # Address details
    street_address = models.TextField()
    landmark = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )
    postal_code = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )

    # Coordinates
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )

    is_default = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)

    class Meta:
        ordering = ['-is_default', '-created_at']
        verbose_name_plural = 'Addresses'

    def __str__(self):
        return f"{self.user.full_name} - {self.street_address}"

    def save(self, *args, **kwargs):
        # If setting as default remove default from others
        if self.is_default:
            Address.objects.filter(
                user=self.user,
                is_default=True
            ).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)