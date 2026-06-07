from django.db import models
from django.conf import settings
from apps.common.models import TimeStampedModel


class BookableItem(TimeStampedModel):
    """
    Generic bookable item
    Can be a hotel room, appointment slot,
    event ticket, car rental etc
    """
    ITEM_TYPE_CHOICES = (
        ('room', 'Room'),
        ('appointment', 'Appointment'),
        ('event', 'Event'),
        ('vehicle', 'Vehicle'),
        ('service', 'Service'),
        ('other', 'Other'),
    )

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    item_type = models.CharField(
        max_length=20,
        choices=ITEM_TYPE_CHOICES,
        default='room'
    )
    price_per_unit = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    unit_label = models.CharField(
        max_length=50,
        default='night'
    )
    capacity = models.IntegerField(default=1)
    image = models.ImageField(
        upload_to='bookable_items/',
        blank=True,
        null=True
    )
    is_available = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class Booking(TimeStampedModel):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('checked_in', 'Checked In'),
        ('checked_out', 'Checked Out'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show'),
    )

    PAYMENT_STATUS_CHOICES = (
        ('unpaid', 'Unpaid'),
        ('partially_paid', 'Partially Paid'),
        ('paid', 'Paid'),
        ('refunded', 'Refunded'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='bookings'
    )
    item = models.ForeignKey(
        BookableItem,
        on_delete=models.CASCADE,
        related_name='bookings'
    )
    reference = models.CharField(
        max_length=100,
        unique=True
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='unpaid'
    )

    # Booking dates
    check_in = models.DateField()
    check_out = models.DateField()
    duration = models.IntegerField(default=1)

    # Guest info
    guests = models.IntegerField(default=1)
    guest_name = models.CharField(max_length=255)
    guest_email = models.EmailField()
    guest_phone = models.CharField(max_length=20)

    # Pricing
    price_per_unit = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    total = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    special_requests = models.TextField(
        blank=True,
        null=True
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Booking {self.reference}"



class BookingTracking(TimeStampedModel):
    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name='tracking'
    )
    status = models.CharField(max_length=20)
    description = models.TextField()

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.booking.reference} - {self.status}"
