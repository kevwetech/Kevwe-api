from django.db import models
from django.conf import settings
from apps.common.models import TimeStampedModel
from apps.drivers.models import DriverProfile


class RideVehicleType(TimeStampedModel):
    name = models.CharField(max_length=50)
    description = models.CharField(max_length=255)
    base_fare = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=500
    )
    per_km_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=100
    )
    per_minute_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=10
    )
    minimum_fare = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=800
    )
    max_passengers = models.IntegerField(default=4)
    icon = models.ImageField(
        upload_to='vehicle_types/',
        null=True,
        blank=True
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['base_fare']

    def __str__(self):
        return self.name


class Ride(TimeStampedModel):
    STATUS_CHOICES = (
        ('requested', 'Requested'),
        ('searching', 'Searching Driver'),
        ('accepted', 'Accepted'),
        ('driver_arriving', 'Driver Arriving'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('no_driver', 'No Driver Found'),
    )

    PAYMENT_METHOD_CHOICES = (
        ('cash', 'Cash'),
        ('card', 'Card'),
        ('wallet', 'Wallet'),
        ('transfer', 'transfer'),
    )

    PAYMENT_STATUS_CHOICES = (
        ('unpaid', 'Unpaid'),
        ('paid', 'Paid'),
    )

    # Users
    rider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='rides'
    )
    driver = models.ForeignKey(
        DriverProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='rides'
    )
    vehicle_type = models.ForeignKey(
        RideVehicleType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    # Reference
    reference = models.CharField(max_length=100, unique=True)

    # Pickup
    pickup_address = models.TextField()
    pickup_lat = models.DecimalField(
        max_digits=9,
        decimal_places=6
    )
    pickup_lng = models.DecimalField(
        max_digits=9,
        decimal_places=6
    )

    # Destination
    destination_address = models.TextField()
    destination_lat = models.DecimalField(
        max_digits=9,
        decimal_places=6
    )
    destination_lng = models.DecimalField(
        max_digits=9,
        decimal_places=6
    )

    # Driver current location
    driver_current_lat = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )
    driver_current_lng = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )

    # Pricing
    estimated_fare = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    actual_fare = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    distance_km = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    duration_minutes = models.IntegerField(
        null=True,
        blank=True
    )

    # Payment
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default='cash'
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
        default='requested'
    )

    # Ratings
    rider_rating = models.IntegerField(null=True, blank=True)
    driver_rating = models.IntegerField(null=True, blank=True)
    rider_review = models.TextField(blank=True, null=True)
    driver_review = models.TextField(blank=True, null=True)

    # Timestamps
    accepted_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Ride {self.reference}"


class RideTracking(TimeStampedModel):
    ride = models.ForeignKey(
        Ride,
        on_delete=models.CASCADE,
        related_name='tracking'
    )
    driver_lat = models.DecimalField(
        max_digits=9,
        decimal_places=6
    )
    driver_lng = models.DecimalField(
        max_digits=9,
        decimal_places=6
    )
    status = models.CharField(max_length=20)
    description = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Ride {self.ride.reference} tracking"
