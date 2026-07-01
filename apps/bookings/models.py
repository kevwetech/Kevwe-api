from django.db import models
from django.conf import settings
from apps.common.models import TimeStampedModel


class BookableItem(TimeStampedModel):
    """
    Generic bookable item
    Now linked to marketplace business
    e.g hotel room, appointment slot,
    event ticket, car rental, service
    """
    ITEM_TYPE_CHOICES = (
        ('room', 'Room'),
        ('appointment', 'Appointment'),
        ('event', 'Event'),
        ('vehicle', 'Vehicle'),
        ('service', 'Service'),
        ('table', 'Table Reservation'),
        ('slot', 'Time Slot'),
        ('other', 'Other'),
    )

    STATUS_CHOICES = (
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('maintenance', 'Under Maintenance'),
    )

    # Link to marketplace business
    business = models.ForeignKey(
        'marketplace.Business',
        on_delete=models.CASCADE,
        related_name='bookable_items',
        null=True,
        blank=True
    )

    # Category from catalog
    category = models.ForeignKey(
        'catalog.ProductCategory',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bookable_items'
    )

    name = models.CharField(max_length=255)
    slug = models.SlugField(
        blank=True,
        null=True
    )
    description = models.TextField(blank=True, null=True)
    short_description = models.CharField(
        max_length=500,
        blank=True,
        null=True
    )
    item_type = models.CharField(
        max_length=20,
        choices=ITEM_TYPE_CHOICES,
        default='room'
    )

    # Pricing
    price_per_unit = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    unit_label = models.CharField(
        max_length=50,
        default='night'
    )  # night, hour, session, person
    min_units = models.IntegerField(default=1)
    max_units = models.IntegerField(
        null=True,
        blank=True
    )

    # Capacity
    capacity = models.IntegerField(default=1)
    # max guests/persons per booking

    # Media
    image = models.ImageField(
        upload_to='bookable_items/',
        blank=True,
        null=True
    )
    images = models.JSONField(
        default=list,
        blank=True
    )  # additional image URLs

    # Availability
    is_available = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active'
    )

    # Booking rules
    advance_booking_days = models.IntegerField(
        default=0
    )  # min days in advance
    max_advance_booking_days = models.IntegerField(
        default=365
    )  # max days in advance
    cancellation_hours = models.IntegerField(
        default=24
    ) 
    requires_kyc = models.BooleanField(
        default=False,
        help_text='Require guest identity verification before booking'
    )
     # free cancellation window
    auto_confirm = models.BooleanField(default=True)

    # Location
    location = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )
    floor = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )

    # Commission
    commission_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )  # override business commission

    # Stats
    total_bookings = models.IntegerField(default=0)
    total_revenue = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )
    rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0
    )
    total_ratings = models.IntegerField(default=0)

    # Tags
    tags = models.JSONField(default=list, blank=True)
    amenities = models.JSONField(
        default=list,
        blank=True
    )  # e.g ['WiFi', 'AC', 'TV', 'Breakfast']

    is_featured = models.BooleanField(default=False)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['-is_featured', 'order', 'name']

    def __str__(self):
        return f"{self.name} - {self.business.name if self.business else 'No Business'}"

    @property
    def effective_commission_rate(self):
        if self.commission_rate:
            return self.commission_rate
        if self.business:
            return self.business.commission_rate
        return 10

    def check_subscription(self):
        """
        Check if business has valid subscription
        to list this item type
        Returns (can_list, reason)
        """
        if not self.business:
            return True, 'No business attached'

        try:
            subscription = self.business.subscription
            policy = self.policy

            can_list, reason = subscription.can_accept_bookings(
                policy.booking_mode
            )
            return can_list, reason

        except Exception:
            # No subscription or no policy
            # Default: exclusive requires subscription
            if self.item_type in ['room', 'vehicle', 'event', 'table']:
                return False, (
                    'Exclusive items require an active subscription. '
                    'Please subscribe to a plan that supports '
                    'exclusive bookings.'
                )
            return True, 'Allowed'


class BookableItemAvailability(TimeStampedModel):
    """
    Availability slots for bookable items
    Marks specific dates as unavailable or
    with custom pricing
    """
    item = models.ForeignKey(
        BookableItem,
        on_delete=models.CASCADE,
        related_name='availability'
    )
    date = models.DateField()
    is_available = models.BooleanField(default=True)
    custom_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )  # override default price
    notes = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    class Meta:
        ordering = ['date']
        unique_together = ('item', 'date')

    def __str__(self):
        return f"{self.item.name} - {self.date}"


class Booking(TimeStampedModel):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('checked_in', 'Checked In'),
        ('checked_out', 'Checked Out'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show'),
        ('refunded', 'Refunded'),
    )

    PAYMENT_STATUS_CHOICES = (
        ('unpaid', 'Unpaid'),
        ('partially_paid', 'Partially Paid'),
        ('paid', 'Paid'),
        ('refunded', 'Refunded'),
    )

    PAYMENT_METHOD_CHOICES = (
        ('wallet', 'Wallet'),
        ('paystack', 'Paystack'),
        ('flutterwave', 'Flutterwave'),
        ('cash', 'Cash'),
        ('transfer', 'Bank Transfer'),
    )

    # Users
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='bookings'
    )

    # Business
    business = models.ForeignKey(
        'marketplace.Business',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bookings'
    )

    # Item being booked
    item = models.ForeignKey(
        BookableItem,
        on_delete=models.CASCADE,
        related_name='bookings'
    )

    # Reference
    reference = models.CharField(
        max_length=100,
        unique=True
    )
    checkin_code = models.CharField(
        max_length=10,
        null=True, blank=True,
        unique=True
    )

    booking_number = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        null=True
    )

    # Status
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
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default='wallet'
    )

    # Booking dates
    check_in = models.DateField()
    check_out = models.DateField()
    check_in_time = models.TimeField(
        null=True,
        blank=True
    )
    check_out_time = models.TimeField(
        null=True,
        blank=True
    )
    duration = models.IntegerField(default=1)
    # number of nights/hours/sessions

    # Actual check in/out timestamps
    actual_check_in = models.DateTimeField(
        null=True,
        blank=True
    )
    actual_check_out = models.DateTimeField(
        null=True,
        blank=True
    )

    # Guest info
    guests = models.IntegerField(default=1)
    guest_name = models.CharField(max_length=255)
    guest_email = models.EmailField()
    guest_phone = models.CharField(max_length=20)
    guest_id_type = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )  # passport, NIN, drivers license
    guest_id_number = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    # Pricing
    price_per_unit = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    tax_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    total = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    # Commission splits
    platform_commission = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    business_earnings = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    # Location FKs (Option C)
    delivery_address_ref = models.ForeignKey(
        'locations.Address',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bookings'
    )

    special_requests = models.TextField(
        blank=True,
        null=True
    )
    notes = models.TextField(blank=True, null=True)

    # Cancellation
    cancelled_at = models.DateTimeField(
        null=True,
        blank=True
    )
    cancellation_reason = models.TextField(
        blank=True,
        null=True
    )
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cancelled_bookings'
    )

    # Rating
    rating = models.IntegerField(null=True, blank=True)
    review = models.TextField(blank=True, null=True)
    rated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Booking {self.reference}"

    def validate_availability(self):
        """
        Check availability before saving
        Raises ValueError if not available
        """
        try:
            policy = self.item.policy
            is_available, reason = policy.check_availability(
                self.check_in,
                self.check_out,
                exclude_booking_id=self.pk
            )
            if not is_available:
                raise ValueError(reason)
        except BookingPolicy.DoesNotExist:
            # No policy set - check exclusive by default
            overlapping = Booking.objects.filter(
                item=self.item,
                status__in=['pending', 'confirmed', 'checked_in'],
                check_in__lt=self.check_out,
                check_out__gt=self.check_in,
            )
            if self.pk:
                overlapping = overlapping.exclude(pk=self.pk)
            if overlapping.exists():
                raise ValueError(
                    'Item is not available for selected dates'
                )

    def calculate_totals(self):
        """Calculate booking totals and commission"""
        from decimal import Decimal
        self.subtotal = (
            Decimal(str(self.price_per_unit)) *
            self.duration
        )
        self.total = (
            self.subtotal +
            self.tax_amount -
            self.discount_amount
        )

        # Commission splits
        if self.business:
            rate = Decimal(
                str(self.item.effective_commission_rate)
            ) / 100
            vendor_rate = Decimal(
                str(self.business.industry.vendor_commission)
            ) / 100
            self.platform_commission = self.subtotal * rate
            self.business_earnings = self.subtotal * vendor_rate

        self.save()


class BookingTracking(TimeStampedModel):
    """Track booking status changes"""
    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name='tracking'
    )
    status = models.CharField(max_length=20)
    description = models.TextField()
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='booking_tracking'
    )

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.booking.reference} - {self.status}"


class BookingAddOn(TimeStampedModel):
    """
    Additional services added to a booking
    e.g breakfast, airport transfer, extra bed
    """
    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name='addons'
    )
    name = models.CharField(max_length=255)
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    quantity = models.IntegerField(default=1)
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    notes = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    def save(self, *args, **kwargs):
        self.subtotal = self.price * self.quantity
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.booking.reference} + {self.name}"


class BookingPolicy(TimeStampedModel):
    """
    Defines booking rules per item type
    Controls whether double booking is allowed
    """
    BOOKING_MODE_CHOICES = (
        ('exclusive', 'Exclusive'),
        # One booking per date range
        # e.g hotel room, car, event center
        ('slot_based', 'Slot Based'),
        # Multiple bookings up to capacity
        # e.g barber, spa, appointments
        ('seat_based', 'Seat Based'),
        # Multiple bookings up to seats
        # e.g event tickets, class
    )

    item = models.OneToOneField(
        BookableItem,
        on_delete=models.CASCADE,
        related_name='policy'
    )
    booking_mode = models.CharField(
        max_length=20,
        choices=BOOKING_MODE_CHOICES,
        default='exclusive'
    )

    # Slot based settings
    slots_per_day = models.IntegerField(
        default=1
    )  # max bookings per day
    slot_duration_minutes = models.IntegerField(
        default=60
    )  # how long each slot is
    slots_start_time = models.TimeField(
        null=True,
        blank=True
    )  # e.g 09:00
    slots_end_time = models.TimeField(
        null=True,
        blank=True
    )  # e.g 18:00
    break_between_slots = models.IntegerField(
        default=0
    )  # minutes between slots

    # Seat based settings
    total_seats = models.IntegerField(default=1)

    # Overlap rules
    allow_same_day_checkout_checkin = models.BooleanField(
        default=True
    )
    # e.g room checked out at 12pm can be booked
    # from 2pm same day

    buffer_hours = models.IntegerField(
        default=0
    )
    # hours needed between bookings
    # e.g car needs 2hrs for cleaning

    # Cancellation
    free_cancellation_hours = models.IntegerField(
        default=24
    )
    cancellation_fee_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.item.name} Policy ({self.booking_mode})"

    def check_availability(
        self,
        check_in,
        check_out,
        exclude_booking_id=None
    ):
        """
        Check if item is available for given dates
        Returns (is_available, reason)
        """
        from django.db.models import Q

        # Get active bookings
        bookings = Booking.objects.filter(
            item=self.item,
            status__in=[
                'pending', 'confirmed',
                'checked_in'
            ]
        )

        if exclude_booking_id:
            bookings = bookings.exclude(
                pk=exclude_booking_id
            )

        if self.booking_mode == 'exclusive':
            return self._check_exclusive(
                bookings, check_in, check_out
            )

        elif self.booking_mode == 'slot_based':
            return self._check_slot_based(
                bookings, check_in, check_out
            )

        elif self.booking_mode == 'seat_based':
            return self._check_seat_based(
                bookings, check_in, check_out
            )

        return True, 'Available'

    def _check_exclusive(
        self, bookings, check_in, check_out
    ):
        """
        No overlap allowed at all
        For hotels, cars, event centers
        """
        from django.db.models import Q

        # Check for any date overlap
        if self.allow_same_day_checkout_checkin:
            # Allow checkout and checkin on same day
            overlapping = bookings.filter(
                Q(check_in__lt=check_out) &
                Q(check_out__gt=check_in) &
                ~Q(check_out=check_in) &
                ~Q(check_in=check_out)
            )
        else:
            # Strict - no same day transitions
            overlapping = bookings.filter(
                Q(check_in__lt=check_out) &
                Q(check_out__gt=check_in)
            )

        # Apply buffer
        if self.buffer_hours > 0:
            from datetime import timedelta
            buffered_check_in = (
                check_in -
                timedelta(hours=self.buffer_hours)
            )
            buffered_check_out = (
                check_out +
                timedelta(hours=self.buffer_hours)
            )
            overlapping = bookings.filter(
                check_in__lt=buffered_check_out,
                check_out__gt=buffered_check_in,
            )

        if overlapping.exists():
            conflicting = overlapping.first()
            return False, (
                f'Already booked from '
                f'{conflicting.check_in} to '
                f'{conflicting.check_out}'
            )

        return True, 'Available'

    def _check_slot_based(
        self, bookings, check_in, check_out
    ):
        """
        Multiple bookings allowed up to slots_per_day
        For barbers, spas, appointments
        """
        # Count bookings on the same day
        same_day_bookings = bookings.filter(
            check_in=check_in
        ).count()

        if same_day_bookings >= self.slots_per_day:
            return False, (
                f'All {self.slots_per_day} slots for '
                f'{check_in} are booked'
            )

        return True, (
            f'{self.slots_per_day - same_day_bookings} '
            f'slots available'
        )

    def _check_seat_based(
        self, bookings, check_in, check_out
    ):
        """
        Multiple bookings allowed up to total_seats
        For events, classes, screenings
        """
        from django.db.models import Q, Sum

        # Count seats booked for overlapping dates
        seats_booked = bookings.filter(
            Q(check_in__lt=check_out) &
            Q(check_out__gt=check_in)
        ).aggregate(
            total=Sum('guests')
        )['total'] or 0

        available_seats = self.total_seats - seats_booked

        if available_seats <= 0:
            return False, (
                f'No seats available. '
                f'{self.total_seats} seats all booked.'
            )

        return True, f'{available_seats} seats available'

    def get_available_slots(self, date):
        """
        Get available time slots for a date
        For slot-based bookings
        """
        if self.booking_mode != 'slot_based':
            return []

        if not self.slots_start_time or not self.slots_end_time:
            return []

        from datetime import datetime, timedelta

        slots = []
        current = datetime.combine(
            date,
            self.slots_start_time
        )
        end = datetime.combine(
            date,
            self.slots_end_time
        )

        slot_duration = timedelta(
            minutes=self.slot_duration_minutes
        )
        break_duration = timedelta(
            minutes=self.break_between_slots
        )

        # Get booked slots
        booked = Booking.objects.filter(
            item=self.item,
            check_in=date,
            status__in=['pending', 'confirmed']
        ).values_list('check_in_time', flat=True)

        slot_num = 0
        while current + slot_duration <= end:
            slot_time = current.time()
            is_booked = slot_time in booked
            slots.append({
                'slot': slot_num + 1,
                'time': slot_time.strftime('%H:%M'),
                'end_time': (
                    current + slot_duration
                ).time().strftime('%H:%M'),
                'is_available': not is_booked,
                'duration_minutes': self.slot_duration_minutes,
            })
            current += slot_duration + break_duration
            slot_num += 1

        return slots

class BookingPayment(TimeStampedModel):
    """
    Track all payments for a booking
    Supports partial payments and multiple
    payment attempts
    """
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
        ('cancelled', 'Cancelled'),
    )

    PAYMENT_TYPE_CHOICES = (
        ('full', 'Full Payment'),
        ('deposit', 'Deposit'),
        ('balance', 'Balance Payment'),
        ('refund', 'Refund'),
        ('partial_refund', 'Partial Refund'),
    )

    GATEWAY_CHOICES = (
        ('wallet', 'Wallet'),
        ('paystack', 'Paystack'),
        ('flutterwave', 'Flutterwave'),
        ('cash', 'Cash'),
        ('transfer', 'Bank Transfer'),
    )

    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name='payments'
    )
    payment_type = models.CharField(
        max_length=20,
        choices=PAYMENT_TYPE_CHOICES,
        default='full'
    )
    gateway = models.CharField(
        max_length=20,
        choices=GATEWAY_CHOICES,
        default='wallet'
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

    # References
    reference = models.CharField(
        max_length=100,
        unique=True
    )
    gateway_reference = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )
    gateway_response = models.JSONField(
        default=dict,
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    # Payer
    paid_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='booking_payments'
    )
    paid_at = models.DateTimeField(
        null=True,
        blank=True
    )

    # Refund
    refunded_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    refunded_at = models.DateTimeField(
        null=True,
        blank=True
    )
    refund_reason = models.TextField(
        blank=True,
        null=True
    )

    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.booking.booking_number} - {self.payment_type} - {self.amount}"

    @property
    def is_successful(self):
        return self.status == 'success'

    @property
    def net_amount(self):
        return self.amount - self.refunded_amount


class BookingGuest(TimeStampedModel):
    """
    Additional guests on a booking
    Beyond the primary guest
    """
    GUEST_TYPE_CHOICES = (
        ('adult', 'Adult'),
        ('children', 'Children'),
        ('infant', 'Infant'),
    )

    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name='guest_list'
    )
    guest_type = models.CharField(
        max_length=10,
        choices=GUEST_TYPE_CHOICES,
        default='adult'
    )

    # Personal info
    full_name = models.CharField(max_length=255)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )
    date_of_birth = models.DateField(
        null=True,
        blank=True
    )

    # ID
    id_type = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )  # passport, NIN, drivers_license
    id_number = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )
    nationality = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    special_needs = models.TextField(
        blank=True,
        null=True
    )

    class Meta:
        ordering = ['guest_type', 'full_name']

    def __str__(self):
        return f"{self.full_name} ({self.guest_type}) - {self.booking.booking_number}"


class BookingCoupon(TimeStampedModel):
    """
    Discount coupons for bookings
    """
    DISCOUNT_TYPE_CHOICES = (
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
        ('free_night', 'Free Night'),
        ('free_delivery', 'Free Service Fee'),
    )

    STATUS_CHOICES = (
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('exhausted', 'Exhausted'),
        ('inactive', 'Inactive'),
    )

    # Scope
    business = models.ForeignKey(
        'marketplace.Business',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='booking_coupons'
    )  # null = platform wide

    item = models.ForeignKey(
        BookableItem,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='coupons'
    )  # null = applies to all items

    # Coupon details
    code = models.CharField(
        max_length=50,
        unique=True
    )
    name = models.CharField(max_length=255)
    description = models.TextField(
        blank=True,
        null=True
    )

    # Discount
    discount_type = models.CharField(
        max_length=20,
        choices=DISCOUNT_TYPE_CHOICES,
        default='percentage'
    )
    discount_value = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    max_discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    min_booking_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    min_nights = models.IntegerField(default=1)

    # Usage limits
    usage_limit = models.IntegerField(
        default=0
    )  # 0 = unlimited
    per_user_limit = models.IntegerField(default=1)
    total_uses = models.IntegerField(default=0)

    # Validity
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField(
        null=True,
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active'
    )

    # Stats
    total_discount_given = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )
    total_revenue_generated = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='booking_coupons'
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.code} - {self.discount_type}"

    @property
    def is_valid(self):
        from django.utils import timezone
        now = timezone.now()
        if self.status != 'active':
            return False
        if now < self.valid_from:
            return False
        if self.valid_until and now > self.valid_until:
            return False
        if (self.usage_limit > 0 and
                self.total_uses >= self.usage_limit):
            return False
        return True

    def calculate_discount(self, booking_amount, nights=1):
        """Calculate discount for given amount"""
        from decimal import Decimal

        if not self.is_valid:
            return Decimal('0')

        if booking_amount < self.min_booking_amount:
            return Decimal('0')

        if nights < self.min_nights:
            return Decimal('0')

        if self.discount_type == 'percentage':
            discount = (
                Decimal(str(booking_amount)) *
                Decimal(str(self.discount_value)) / 100
            )
            if self.max_discount_amount:
                discount = min(
                    discount,
                    Decimal(str(self.max_discount_amount))
                )

        elif self.discount_type == 'fixed':
            discount = Decimal(str(self.discount_value))

        elif self.discount_type == 'free_night':
            # One night free
            discount = (
                Decimal(str(booking_amount)) /
                Decimal(str(nights))
            )

        else:
            discount = Decimal('0')

        return round(discount, 2)

    def apply(self, booking, user):
        """Apply coupon to a booking"""
        from django.utils import timezone

        # Check per user limit
        user_uses = CouponUsage.objects.filter(
            coupon=self,
            user=user
        ).count()

        if user_uses >= self.per_user_limit:
            raise ValueError(
                f'You have already used this coupon '
                f'{self.per_user_limit} time(s)'
            )

        discount = self.calculate_discount(
            booking.subtotal,
            booking.duration
        )

        # Record usage
        CouponUsage.objects.create(
            coupon=self,
            booking=booking,
            user=user,
            discount_amount=discount,
        )

        # Update coupon stats
        self.total_uses += 1
        self.total_discount_given += discount
        self.total_revenue_generated += booking.subtotal
        self.save()

        return discount


class CouponUsage(TimeStampedModel):
    """Track coupon usage per user per booking"""
    coupon = models.ForeignKey(
        BookingCoupon,
        on_delete=models.CASCADE,
        related_name='usages'
    )
    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name='coupon_usages'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='coupon_usages'
    )
    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    class Meta:
        ordering = ['-created_at']
        unique_together = ('coupon', 'booking')

    def __str__(self):
        return f"{self.coupon.code} used on {self.booking.booking_number}"


class BookingInvoice(TimeStampedModel):
    """
    Auto generated invoice for each booking
    """
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled'),
    )

    booking = models.OneToOneField(
        Booking,
        on_delete=models.CASCADE,
        related_name='invoice'
    )

    # Invoice details
    invoice_number = models.CharField(
        max_length=50,
        unique=True
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft'
    )

    # Billing info
    billed_to_name = models.CharField(max_length=255)
    billed_to_email = models.EmailField()
    billed_to_phone = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )
    billed_to_address = models.TextField(
        blank=True,
        null=True
    )

    # Business info
    business_name = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )
    business_address = models.TextField(
        blank=True,
        null=True
    )
    business_phone = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )
    business_email = models.EmailField(
        blank=True,
        null=True
    )

    # Line items (JSON snapshot)
    line_items = models.JSONField(default=list)
    # e.g [
    #   {"description": "Room - 3 nights",
    #    "qty": 3, "unit_price": 15000, "total": 45000},
    #   {"description": "Breakfast addon",
    #    "qty": 3, "unit_price": 2000, "total": 6000},
    # ]

    # Amounts
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )
    tax_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    total = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    currency = models.CharField(
        max_length=10,
        default='NGN'
    )

    # Dates
    issue_date = models.DateField()
    due_date = models.DateField(
        null=True,
        blank=True
    )
    paid_date = models.DateField(
        null=True,
        blank=True
    )

    # PDF
    pdf_url = models.URLField(
        blank=True,
        null=True
    )

    notes = models.TextField(blank=True, null=True)
    terms = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Invoice {self.invoice_number} - {self.booking.booking_number}"

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            import random
            import string
            self.invoice_number = 'INV-BKG-' + ''.join(
                random.choices(
                    string.ascii_uppercase + string.digits,
                    k=8
                )
            )
        super().save(*args, **kwargs)

    @classmethod
    def generate_for_booking(cls, booking):
        """Auto generate invoice from booking"""
        from django.utils import timezone

        # Build line items
        line_items = [
            {
                'description': f'{booking.item.name} x {booking.duration} {booking.item.unit_label}',
                'qty': booking.duration,
                'unit_price': float(booking.price_per_unit),
                'total': float(booking.subtotal),
            }
        ]

        # Add addon line items
        for addon in booking.addons.all():
            line_items.append({
                'description': addon.name,
                'qty': addon.quantity,
                'unit_price': float(addon.price),
                'total': float(addon.subtotal),
            })

        invoice, created = cls.objects.get_or_create(
            booking=booking,
            defaults={
                'billed_to_name': booking.guest_name,
                'billed_to_email': booking.guest_email,
                'billed_to_phone': booking.guest_phone,
                'business_name': (
                    booking.business.name
                    if booking.business else ''
                ),
                'business_phone': (
                    booking.business.phone
                    if booking.business else ''
                ),
                'business_email': (
                    booking.business.email
                    if booking.business else ''
                ),
                'line_items': line_items,
                'subtotal': booking.subtotal,
                'discount_amount': booking.discount_amount,
                'tax_amount': booking.tax_amount,
                'total': booking.total,
                'issue_date': timezone.now().date(),
                'status': (
                    'paid' if booking.payment_status == 'paid'
                    else 'sent'
                ),
                'paid_date': (
                    timezone.now().date()
                    if booking.payment_status == 'paid'
                    else None
                ),
            }
        )
        return invoice


class BookingReminder(TimeStampedModel):
    """
    Automated reminders for upcoming bookings
    """
    REMINDER_TYPE_CHOICES = (
        ('check_in', 'Check-in Reminder'),
        ('check_out', 'Check-out Reminder'),
        ('payment_due', 'Payment Due Reminder'),
        ('review_request', 'Review Request'),
        ('cancellation_deadline', 'Cancellation Deadline'),
        ('custom', 'Custom Reminder'),
    )

    CHANNEL_CHOICES = (
        ('notification', 'In-App Notification'),
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('all', 'All Channels'),
        ('whatsapp', 'whatsapp'),
    )

    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    )

    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name='reminders'
    )
    reminder_type = models.CharField(
        max_length=25,
        choices=REMINDER_TYPE_CHOICES
    )
    channel = models.CharField(
        max_length=15,
        choices=CHANNEL_CHOICES,
        default='notification'
    )

    # When to send
    send_at = models.DateTimeField()
    # e.g 24hrs before check-in

    # Content
    title = models.CharField(max_length=255)
    message = models.TextField()

    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    sent_at = models.DateTimeField(
        null=True,
        blank=True
    )
    error_message = models.TextField(
        blank=True,
        null=True
    )

    # Recipient
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='booking_reminders'
    )

    class Meta:
        ordering = ['send_at']

    def __str__(self):
        return f"{self.reminder_type} for {self.booking.booking_number} at {self.send_at}"

    def send(self):
        """Send the reminder"""
        from django.utils import timezone

        try:
            if self.channel in ['notification', 'all']:
                from apps.notifications.utils import send_notification
                send_notification(
                    user=self.recipient,
                    title=self.title,
                    message=self.message,
                    notification_type='system',
                    data={
                        'booking_id': self.booking.id,
                        'booking_number': self.booking.booking_number,
                        'reminder_type': self.reminder_type,
                    }
                )

            if self.channel in ['email', 'all']:
                from apps.common.email import send_email
                send_email(
                    to_email=self.recipient.email,
                    subject=self.title,
                    html_content=f"""
                    <div style="font-family: Arial; max-width: 600px; margin: 0 auto;">
                        <h2>{self.title}</h2>
                        <p>{self.message}</p>
                        <p>Booking: <strong>{self.booking.booking_number}</strong></p>
                        <p>Check-in: <strong>{self.booking.check_in}</strong></p>
                        <p>Check-out: <strong>{self.booking.check_out}</strong></p>
                    </div>
                    """
                )

            self.status = 'sent'
            self.sent_at = timezone.now()
            self.save()
            return True

        except Exception as e:
            self.status = 'failed'
            self.error_message = str(e)
            self.save()
            return False

    @classmethod
    def create_booking_reminders(cls, booking):
        """Auto create reminders for a new booking"""
        from django.utils import timezone
        from datetime import timedelta, datetime, time

        check_in_dt = datetime.combine(
            booking.check_in,
            time(12, 0)
        )
        check_in_dt = timezone.make_aware(check_in_dt)

        reminders = [
            # 24hr before check-in
            {
                'reminder_type': 'check_in',
                'channel': 'all',
                'send_at': check_in_dt - timedelta(hours=24),
                'title': f'Check-in Tomorrow! 🏨',
                'message': (
                    f'Your booking {booking.booking_number} '
                    f'for {booking.item.name} is tomorrow. '
                    f'Check-in: {booking.check_in}'
                ),
            },
            # 2hrs before check-in
            {
                'reminder_type': 'check_in',
                'channel': 'notification',
                'send_at': check_in_dt - timedelta(hours=2),
                'title': f'Check-in in 2 Hours! ⏰',
                'message': (
                    f'Your check-in for {booking.item.name} '
                    f'is in 2 hours. Get ready!'
                ),
            },
            # 1 day after checkout - review request
            {
                'reminder_type': 'review_request',
                'channel': 'notification',
                'send_at': datetime.combine(
                    booking.check_out,
                    time(18, 0)
                ),
                'title': 'How was your stay? ⭐',
                'message': (
                    f'We hope you enjoyed your stay at '
                    f'{booking.item.name}! Please leave a review.'
                ),
            },
        ]

        # Add cancellation deadline reminder
        try:
            policy = booking.item.policy
            free_cancel_hours = policy.free_cancellation_hours
            cancel_deadline = (
                check_in_dt - timedelta(hours=free_cancel_hours)
            )
            if cancel_deadline > timezone.now():
                reminders.append({
                    'reminder_type': 'cancellation_deadline',
                    'channel': 'notification',
                    'send_at': cancel_deadline - timedelta(hours=2),
                    'title': 'Free Cancellation Ending Soon ⚠️',
                    'message': (
                        f'Free cancellation for booking '
                        f'{booking.booking_number} ends in 2 hours.'
                    ),
                })
        except BookingPolicy.DoesNotExist:
            pass

        created = []
        for reminder_data in reminders:
            if reminder_data['send_at'] > timezone.now():
                reminder = cls.objects.create(
                    booking=booking,
                    recipient=booking.user,
                    **reminder_data
                )
                created.append(reminder)

        return created