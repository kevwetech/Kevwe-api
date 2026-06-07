from django.db import models
from django.conf import settings
from apps.common.models import TimeStampedModel



class VehicleType(TimeStampedModel):
    """
    Manageable vehicle types with pricing
    Admin can add/edit/remove anytime
    """
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(unique=True)
    description = models.CharField(max_length=255, blank=True)
    icon = models.ImageField(
        upload_to='vehicle_type_icons/',
        null=True,
        blank=True
    )

    # Pricing
    base_price_standard = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=500
    )
    base_price_express = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=1000
    )
    per_km_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=100
    )
    per_kg_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=30
    )
    minimum_fare_standard = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=800
    )
    minimum_fare_express = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=1500
    )
    max_weight_kg = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=50
    )
    max_passengers = models.IntegerField(default=1)
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class Vehicle(TimeStampedModel):
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('maintenance', 'Maintenance'),
    )

    driver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='vehicles'
    )
    
    vehicle_type = models.ForeignKey(
        VehicleType,
        on_delete=models.SET_NULL,
        null=True,
        related_name='vehicles'
    )

    plate_number = models.CharField(max_length=20, unique=True)
    model = models.CharField(max_length=100)
    brand = models.CharField(max_length=100)
    color = models.CharField(max_length=50)
    year = models.IntegerField()
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active'
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.plate_number} - {self.brand} {self.model}"





class DriverProfile(TimeStampedModel):
    STATUS_CHOICES = (
        ('pending', 'Pending Verification'),
        ('verified', 'Verified'),
        ('suspended', 'Suspended'),
        ('rejected', 'Rejected'),
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='driver_profile'
    )
    license_number = models.CharField(max_length=50, unique=True)
    license_expiry = models.DateField()
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    zone_name = models.ForeignKey(
    'deliveries.DeliveryZone',
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name='drivers'
    )
    is_available = models.BooleanField(default=False)
    is_online = models.BooleanField(default=False)

    # Current location
    current_lat = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )
    current_lng = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )
    last_location_update = models.DateTimeField(
        null=True,
        blank=True
    )

    # Stats
    total_rides = models.IntegerField(default=0)
    total_deliveries = models.IntegerField(default=0)
    rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=5.00
    )
    total_ratings = models.IntegerField(default=0)

    delivery = models.ForeignKey(
        'deliveries.DeliveryRequest', 
        on_delete=models.SET_NULL,   # Changed from CASCADE
        null=True, 
        blank=True,
        related_name='current_driver'
    )

    # Active vehicle
    active_vehicle = models.ForeignKey(
        'drivers.Vehicle',           # Use string reference too
        on_delete=models.SET_NULL,
        null=True, 
        blank=True,
        related_name='active_driver'
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Driver: {self.user.full_name}"

    @property
    def is_verified(self):
        return self.status == 'verified'


class DriverDocument(TimeStampedModel):
    DOCUMENT_TYPE_CHOICES = (
        ('license', 'Driver License'),
        ('insurance', 'Insurance'),
        ('vehicle_registration', 'Vehicle Registration'),
        ('background_check', 'Background Check'),
    )

    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )

    driver = models.ForeignKey(
        DriverProfile,
        on_delete=models.CASCADE,
        related_name='documents'
    )
    document_type = models.CharField(
        max_length=30,
        choices=DOCUMENT_TYPE_CHOICES
    )
    document_file = models.FileField(
        upload_to='driver_documents/'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.driver.user.full_name} - {self.document_type}"


class DriverEarnings(TimeStampedModel):
    EARNING_TYPE_CHOICES = (
        ('ride', 'Ride'),
        ('delivery', 'Delivery'),
        ('bonus', 'Bonus'),
        ('penalty', 'Penalty'),
    )

    driver = models.ForeignKey(
        DriverProfile,
        on_delete=models.CASCADE,
        related_name='earnings'
    )
    earning_type = models.CharField(
        max_length=20,
        choices=EARNING_TYPE_CHOICES
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reference = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    is_paid = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.driver.user.full_name} - {self.amount}"