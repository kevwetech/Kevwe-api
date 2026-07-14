from django.db import models
from django.conf import settings
from apps.common.models import TimeStampedModel
from apps.drivers.models import DriverProfile

class ShipmentVehicleCategory(TimeStampedModel):
    """
    Global vehicle categories for logistics filtering.
    Grouped by transport mode (land/sea/air).
    """
    TRANSPORT_MODE_CHOICES = (
        ('land', 'Land'),
        ('sea',  'Sea'),
        ('air',  'Air'),
    )
    transport_mode = models.CharField(
        max_length=10,
        choices=TRANSPORT_MODE_CHOICES,
        default='land',
    )
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True, null=True)
    icon = models.CharField(max_length=10, blank=True, null=True)
    max_weight_kg = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['transport_mode', 'order', 'name']
        verbose_name_plural = 'Shipment Vehicle Categories'

    def __str__(self):
        return f"{self.name} ({self.get_transport_mode_display()})"


class ShipmentServiceCategory(TimeStampedModel):
    """
    Business-scoped shipment service categories.
    Each logistics company defines their own service tiers.
    
    e.g. Kevwe Logistics: Same Day / Next Day / Intercity / Bulk
    e.g. DHL: Express / Economy / International
    """
    business = models.ForeignKey(
        'marketplace.Business',
        on_delete=models.CASCADE,
        related_name='shipment_service_categories',
    )
    name = models.CharField(max_length=100)
    slug = models.SlugField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    icon = models.CharField(max_length=10, blank=True, null=True)
    estimated_days_min = models.PositiveIntegerField(default=1)
    estimated_days_max = models.PositiveIntegerField(default=3)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']
        verbose_name_plural = 'Shipment Service Categories'

    def __str__(self):
        return f"{self.name} — {self.business.name}"

    def save(self, *args, **kwargs):
        if not self.slug and self.name:
            from django.utils.text import slugify
            import uuid
            self.slug = slugify(self.name) + '-' + str(uuid.uuid4())[:6]
        super().save(*args, **kwargs)


class ShipmentVehicleType(TimeStampedModel):
    """
    Business-scoped vehicle types for logistics companies.
    e.g. Kevwe Logistics: Dispatch Bike, Mini Van, 5-Ton Truck
    """
    business = models.ForeignKey(
        'marketplace.Business',
        on_delete=models.CASCADE,
        related_name='shipment_vehicle_types',
    )
    category = models.ForeignKey(
        ShipmentVehicleCategory,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='vehicle_types',
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    max_weight_kg = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True)
    base_fare = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    per_km_rate = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    icon = models.CharField(max_length=10, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']
        verbose_name_plural = 'Shipment Vehicle Types'

    def __str__(self):
        return f"{self.name} — {self.business.name}"


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
    business = models.ForeignKey(
        'marketplace.Business',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='shipments',
        help_text='Logistics business handling this shipment'
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

    # Insurance
    is_insured = models.BooleanField(default=False)
    declared_value = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    insurance_fee = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )

    # Proof of delivery
    delivery_photo = models.ImageField(
        upload_to='shipments/proof/', null=True, blank=True
    )
    delivery_signature = models.ImageField(
        upload_to='shipments/signatures/', null=True, blank=True
    )
    delivered_at = models.DateTimeField(null=True, blank=True)
    delivery_otp = models.CharField(max_length=6, blank=True, null=True)

    # Rating
    rating = models.IntegerField(null=True, blank=True)
    rating_comment = models.TextField(blank=True, null=True)
    rated_at = models.DateTimeField(null=True, blank=True)

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