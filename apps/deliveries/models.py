from django.db import models
from django.conf import settings
from apps.common.models import TimeStampedModel
from apps.drivers.models import DriverProfile


class DeliveryZone(TimeStampedModel):
    """Coverage areas for delivery"""
    country = models.CharField(max_length=100)
    zone_name = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    base_price = models.DecimalField(
        max_digits=10, decimal_places=2, default=1000
    )
    price_per_km = models.DecimalField(
        max_digits=10, decimal_places=2, default=100
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['city']

    def __str__(self):
        return f"{self.city}, {self.state}"


class DeliveryRequest(TimeStampedModel):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('assigned', 'Assigned'),
        ('picked_up', 'Picked Up'),
        ('in_transit', 'In Transit'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    )

    PACKAGE_SIZE_CHOICES = (
        ('small', 'Small'),
        ('medium', 'Medium'),
        ('large', 'Large'),
    )

    PAYMENT_STATUS_CHOICES = (
        ('unpaid', 'Unpaid'),
        ('paid', 'Paid'),
        ('refunded', 'Refunded'),
    )

    PAYMENT_MODEL_CHOICES = [
        ('marketplace', 'Marketplace'),
        ('logistics', 'Logistics'),
    ]  

    # Users
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='delivery_requests'
    )
    driver = models.ForeignKey(
        DriverProfile,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='deliveries'
    )
    payment_model = models.CharField(
        max_length=20,
        choices=PAYMENT_MODEL_CHOICES,
        default='marketplace',
        blank=True,
        null=True,
    )

    # Reference
    reference = models.CharField(max_length=100, unique=True)
    tracking_number = models.CharField(max_length=50, unique=True)

    # Package
    package_name = models.CharField(max_length=255)
    package_description = models.TextField(blank=True, null=True)
    package_size = models.CharField(
        max_length=20,
        choices=PACKAGE_SIZE_CHOICES,
        default='small'
    )
    fragile = models.BooleanField(default=False)
    weight = models.DecimalField(
        max_digits=10, decimal_places=2, default=1.0
    )

    # ── Pickup ──────────────────────────────────
    # Option B: saved address
    pickup_address_ref = models.ForeignKey(
        'locations.Address',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='pickup_deliveries'
    )

    # Option A/C: manual entry
    pickup_name = models.CharField(max_length=255)
    pickup_phone = models.CharField(max_length=20)
    pickup_address = models.TextField()
    pickup_city = models.CharField(max_length=100, blank=True)
    pickup_state = models.CharField(max_length=100, blank=True)
    pickup_lat = models.DecimalField(
        max_digits=9, decimal_places=6,
        null=True, blank=True
    )
    pickup_lng = models.DecimalField(
        max_digits=9, decimal_places=6,
        null=True, blank=True
    )

    # Location FKs
    pickup_city_ref = models.ForeignKey(
        'locations.City',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='pickup_deliveries'
    )
    pickup_state_ref = models.ForeignKey(
        'locations.State',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='pickup_deliveries'
    )
    pickup_zone = models.ForeignKey(
        'locations.Zone',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='pickup_deliveries'
    )

    # ── Dropoff ─────────────────────────────────
    # Option B: saved address
    dropoff_address_ref = models.ForeignKey(
        'locations.Address',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='dropoff_deliveries'
    )

    # Option A/C: manual entry
    dropoff_name = models.CharField(max_length=255)
    dropoff_phone = models.CharField(max_length=20)
    dropoff_address = models.TextField()
    dropoff_city = models.CharField(max_length=100, blank=True)
    dropoff_state = models.CharField(max_length=100, blank=True)
    dropoff_lat = models.DecimalField(
        max_digits=9, decimal_places=6,
        null=True, blank=True
    )
    dropoff_lng = models.DecimalField(
        max_digits=9, decimal_places=6,
        null=True, blank=True
    )

    # Location FKs
    dropoff_city_ref = models.ForeignKey(
        'locations.City',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='dropoff_deliveries'
    )
    dropoff_state_ref = models.ForeignKey(
        'locations.State',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='dropoff_deliveries'
    )
    dropoff_zone = models.ForeignKey(
        'locations.Zone',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='dropoff_deliveries'
    )

    # Current location
    current_lat = models.DecimalField(
        max_digits=9, decimal_places=6,
        null=True, blank=True
    )
    current_lng = models.DecimalField(
        max_digits=9, decimal_places=6,
        null=True, blank=True
    )
    current_location = models.CharField(
        max_length=255, blank=True, null=True
    )

    # Pricing
    price = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='unpaid'
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    # Timestamps
    picked_up_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    notes = models.TextField(blank=True, null=True)
    delivery_proof = models.ImageField(
        upload_to='delivery_proofs/',
        null=True, blank=True
    )

    # Rating
    rating = models.IntegerField(null=True, blank=True)
    review = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Delivery {self.tracking_number}"


class DeliveryTracking(TimeStampedModel):
    delivery = models.ForeignKey(
        DeliveryRequest,
        on_delete=models.CASCADE,
        related_name='tracking'
    )
    status = models.CharField(max_length=20)
    description = models.TextField()
    location = models.CharField(
        max_length=255, blank=True, null=True
    )
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6,
        null=True, blank=True
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6,
        null=True, blank=True
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True
    )

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.delivery.tracking_number} - {self.status}"



class CompanyEarnings(TimeStampedModel):
    EARNING_TYPE_CHOICES = [
        ('marketplace_commission', 'Marketplace Commission'),
        ('logistics_delivery', 'Logistics Delivery'),
    ]

    earning_type = models.CharField(max_length=30, choices=EARNING_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reference = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.earning_type} - {self.amount}"