from django.db import models
from django.conf import settings
from apps.common.models import TimeStampedModel
from apps.drivers.models import DriverProfile


class Shipment(TimeStampedModel):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('assigned', 'Assigned'),
        ('picked_up', 'Picked Up'),
        ('in_transit', 'In Transit'),
        ('at_hub', 'At Hub'),
        ('out_for_delivery', 'Out for Delivery'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed Delivery'),
        ('returned', 'Returned'),
        ('cancelled', 'Cancelled'),
    )

    PAYMENT_STATUS_CHOICES = (
        ('unpaid', 'Unpaid'),
        ('paid', 'Paid'),
        ('refunded', 'Refunded'),
    )

    PACKAGE_SIZE_CHOICES = (
        ('small', 'Small (0-5kg)'),
        ('medium', 'Medium (5-20kg)'),
        ('large', 'Large (20-50kg)'),
        ('extra_large', 'Extra Large (50kg+)'),
    )

    # Users
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_shipments'
    )
    driver = models.ForeignKey(
        DriverProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='shipments'
    )

    # Reference
    reference = models.CharField(max_length=100, unique=True)
    tracking_number = models.CharField(max_length=50, unique=True)

    # Package details
    package_name = models.CharField(max_length=255)
    package_description = models.TextField(blank=True, null=True)
    package_size = models.CharField(
        max_length=20,
        choices=PACKAGE_SIZE_CHOICES,
        default='small'
    )
    weight = models.DecimalField(max_digits=10, decimal_places=2)
    fragile = models.BooleanField(default=False)

    # ── Pickup ──────────────────────────────────
    # Option B: saved address
    pickup_address_ref = models.ForeignKey(
        'locations.Address',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pickup_shipments'
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
        related_name='pickup_shipments'
    )
    pickup_state_ref = models.ForeignKey(
        'locations.State',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='pickup_shipments'
    )
    pickup_zone = models.ForeignKey(
        'locations.Zone',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='pickup_shipments'
    )

    # ── Delivery ────────────────────────────────
    # Option B: saved address
    delivery_address_ref = models.ForeignKey(
        'locations.Address',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='delivery_shipments'
    )

    # Option A/C: manual entry
    receiver_name = models.CharField(max_length=255)
    receiver_phone = models.CharField(max_length=20)
    receiver_email = models.EmailField(blank=True, null=True)
    delivery_address = models.TextField()
    delivery_city = models.CharField(max_length=100, blank=True)
    delivery_state = models.CharField(max_length=100, blank=True)
    delivery_lat = models.DecimalField(
        max_digits=9, decimal_places=6,
        null=True, blank=True
    )
    delivery_lng = models.DecimalField(
        max_digits=9, decimal_places=6,
        null=True, blank=True
    )

    # Location FKs
    delivery_city_ref = models.ForeignKey(
        'locations.City',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='delivery_shipments'
    )
    delivery_state_ref = models.ForeignKey(
        'locations.State',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='delivery_shipments'
    )
    delivery_zone = models.ForeignKey(
        'locations.Zone',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='delivery_shipments'
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

    estimated_delivery = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, null=True)

    # Pricing metadata
    vehicle_type = models.CharField(max_length=50, blank=True, null=True)
    service_type = models.CharField(max_length=20, default='standard')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Shipment {self.tracking_number}"


class ShipmentTracking(TimeStampedModel):
    shipment = models.ForeignKey(
        Shipment,
        on_delete=models.CASCADE,
        related_name='tracking'
    )
    status = models.CharField(max_length=20)
    description = models.TextField()
    location = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )
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
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.shipment.tracking_number} - {self.status}"