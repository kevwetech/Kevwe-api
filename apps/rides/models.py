from django.db import models
from django.conf import settings
from apps.common.models import TimeStampedModel
from apps.drivers.models import DriverProfile


# ── Ride-hailing (existing, unchanged) ───────────

class RideVehicleType(TimeStampedModel):
    business = models.ForeignKey(
        'marketplace.Business',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='vehicle_types',
        help_text='None = platform-wide default available to all'
    )
    vehicle_category = models.CharField(
        max_length=20,
        choices=(
            ('bike',  'Bike'),
            ('car',   'Car'),
            ('van',   'Van'),
            ('bus',   'Bus'),
            ('truck', 'Truck'),
            ('boat',  'Boat'),
        ),
        default='car',
        help_text='Global category for marketplace filtering'
    )
    name = models.CharField(max_length=50)
    description = models.CharField(max_length=255)
    base_fare = models.DecimalField(max_digits=10, decimal_places=2, default=500)
    per_km_rate = models.DecimalField(max_digits=10, decimal_places=2, default=100)
    per_minute_rate = models.DecimalField(max_digits=10, decimal_places=2, default=10)
    minimum_fare = models.DecimalField(max_digits=10, decimal_places=2, default=800)
    max_passengers = models.IntegerField(default=4)
    icon = models.ImageField(upload_to='vehicle_types/', null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['base_fare']

    def __str__(self):
        return self.name


class Ride(TimeStampedModel):
    STATUS_CHOICES = (
        ('requested',      'Requested'),
        ('searching',      'Searching Driver'),
        ('accepted',       'Accepted'),
        ('driver_arriving','Driver Arriving'),
        ('in_progress',    'In Progress'),
        ('completed',      'Completed'),
        ('cancelled',      'Cancelled'),
        ('no_driver',      'No Driver Found'),
    )
    PAYMENT_METHOD_CHOICES = (
        ('card',     'Card'),
        ('wallet',   'Wallet'),
        ('transfer', 'Transfer'),
    )
    PAYMENT_STATUS_CHOICES = (
        ('unpaid', 'Unpaid'),
        ('paid',   'Paid'),
    )

    business = models.ForeignKey(
        'marketplace.Business',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='rides',
        help_text='Company page the ride was booked from. '
                  'Null = marketplace-wide booking.'
    )

    rider        = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='rides')
    driver       = models.ForeignKey(DriverProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='rides')
    vehicle_type = models.ForeignKey(RideVehicleType, on_delete=models.SET_NULL, null=True, blank=True)
    reference    = models.CharField(max_length=100, unique=True)

    pickup_address   = models.TextField()
    pickup_lat       = models.DecimalField(max_digits=9, decimal_places=6)
    pickup_lng       = models.DecimalField(max_digits=9, decimal_places=6)
    destination_address = models.TextField()
    destination_lat  = models.DecimalField(max_digits=9, decimal_places=6)
    destination_lng  = models.DecimalField(max_digits=9, decimal_places=6)
    driver_current_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    driver_current_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    estimated_fare   = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    actual_fare      = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    distance_km      = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    duration_minutes = models.IntegerField(null=True, blank=True)

    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='wallet')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='unpaid')
    status         = models.CharField(max_length=20, choices=STATUS_CHOICES, default='requested')

    rider_rating  = models.IntegerField(null=True, blank=True)
    driver_rating = models.IntegerField(null=True, blank=True)
    rider_review  = models.TextField(blank=True, null=True)
    driver_review = models.TextField(blank=True, null=True)

    accepted_at  = models.DateTimeField(null=True, blank=True)
    started_at   = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    # Verification
    start_code = models.CharField(
        max_length=6, blank=True, null=True,
        help_text='Customer gives this code to driver before trip starts'
    )
    start_code_verified = models.BooleanField(default=False)
    start_code_verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Ride {self.reference}"
    
    def save(self, *args, **kwargs):
        import uuid
        if not self.reference:
            self.reference = f'RIDE-{uuid.uuid4().hex[:6].upper()}'
        if not self.start_code:
            self.start_code = uuid.uuid4().hex[:4].upper()
        super().save(*args, **kwargs)


class RideTracking(TimeStampedModel):
    ride       = models.ForeignKey(Ride, on_delete=models.CASCADE, related_name='tracking')
    driver_lat = models.DecimalField(max_digits=9, decimal_places=6)
    driver_lng = models.DecimalField(max_digits=9, decimal_places=6)
    status      = models.CharField(max_length=20)
    description = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Ride {self.ride.reference} tracking"


# ══════════════════════════════════════════════════
# TRANSPORT MODULE
# Covers: bus, ferry, airline, train, shuttle
# ══════════════════════════════════════════════════

class TransportVehicle(TimeStampedModel):
    """Fleet vehicle owned by a transport business."""
    VEHICLE_TYPE_CHOICES = (
        ('bus',       'Bus'),
        ('minibus',   'Minibus / Sprinter'),
        ('ferry',     'Ferry / Boat'),
        ('aircraft',  'Aircraft'),
        ('train',     'Train'),
        ('shuttle',   'Shuttle'),
        ('taxi',      'Taxi'),
    )
    STATUS_CHOICES = (
        ('active',      'Active'),
        ('maintenance', 'Under Maintenance'),
        ('retired',     'Retired'),
    )

    business      = models.ForeignKey('marketplace.Business', on_delete=models.CASCADE, related_name='transport_vehicles')
    vehicle_type  = models.CharField(max_length=20, choices=VEHICLE_TYPE_CHOICES, default='bus')
    name          = models.CharField(max_length=100, help_text='e.g. Bus A, Eagle 1')
    plate_number  = models.CharField(max_length=20, blank=True, null=True)
    vehicle_number= models.CharField(max_length=50, blank=True, null=True, help_text='Flight/train/ferry number')
    manufacturer  = models.CharField(max_length=100, blank=True, null=True)
    model         = models.CharField(max_length=100, blank=True, null=True)
    year          = models.IntegerField(null=True, blank=True)
    total_capacity= models.IntegerField(default=18, help_text='Total seats')
    amenities     = models.JSONField(default=list, blank=True, help_text='e.g. ["AC","WiFi","TV","Toilet"]')
    image         = models.ImageField(upload_to='transport/vehicles/', null=True, blank=True)
    status        = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    is_active     = models.BooleanField(default=True)

    class Meta:
        ordering = ['business', 'name']

    def __str__(self):
        return f"{self.business.name} — {self.name} ({self.plate_number or self.vehicle_number or '—'})"


class TransportRoute(TimeStampedModel):
    """A fixed route operated by a transport business."""
    TRANSPORT_TYPE_CHOICES = (
        ('bus',     'Bus'),
        ('minibus', 'Minibus'),
        ('ferry',   'Ferry / Boat'),
        ('train',   'Train'),
        ('airline', 'Airline'),
        ('shuttle', 'Shuttle'),
    )

    business       = models.ForeignKey('marketplace.Business', on_delete=models.CASCADE, related_name='transport_routes')
    transport_type = models.CharField(max_length=20, choices=TRANSPORT_TYPE_CHOICES, default='bus')
    name           = models.CharField(max_length=255, help_text='e.g. Lagos Express, Morning Shuttle')
    route_code     = models.CharField(max_length=20, blank=True, null=True, help_text='e.g. LOS-ABJ, KQ101')
    origin         = models.CharField(max_length=100)
    destination    = models.CharField(max_length=100)
    origin_lat     = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    origin_lng     = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    destination_lat= models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    destination_lng= models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    distance_km    = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    estimated_duration_minutes = models.IntegerField(null=True, blank=True)
    amenities      = models.JSONField(default=list, blank=True, help_text='e.g. ["AC","WiFi","TV","Toilet"]')
    is_active      = models.BooleanField(default=True)
    is_return_available = models.BooleanField(default=False, help_text='Return trip available on same route')

    class Meta:
        ordering = ['origin', 'destination']

    def __str__(self):
        return f"{self.business.name} — {self.origin} → {self.destination}"


class TransportStop(TimeStampedModel):
    """Intermediate stops along a route."""
    route           = models.ForeignKey(TransportRoute, on_delete=models.CASCADE, related_name='stops')
    city            = models.CharField(max_length=100)
    address         = models.TextField(blank=True, null=True)
    lat             = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    lng             = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    order           = models.IntegerField(default=0, help_text='Stop order along the route')
    arrival_offset  = models.IntegerField(null=True, blank=True, help_text='Minutes from departure')
    departure_offset= models.IntegerField(null=True, blank=True, help_text='Minutes from departure')
    is_origin       = models.BooleanField(default=False)
    is_destination  = models.BooleanField(default=False)

    class Meta:
        ordering = ['route', 'order']
        unique_together = ('route', 'order')

    def __str__(self):
        return f"{self.route} — Stop {self.order}: {self.city}"


class TransportSchedule(TimeStampedModel):
    """A specific departure of a route on a date/time."""
    STATUS_CHOICES = (
        ('scheduled', 'Scheduled'),
        ('boarding',  'Boarding'),
        ('departed',  'Departed'),
        ('arrived',   'Arrived'),
        ('cancelled', 'Cancelled'),
        ('delayed',   'Delayed'),
    )
    REPEAT_CHOICES = (
        ('none',     'One-time'),
        ('daily',    'Daily'),
        ('weekdays', 'Weekdays (Mon–Fri)'),
        ('weekends', 'Weekends (Sat–Sun)'),
        ('weekly',   'Weekly'),
        ('custom',   'Custom'),
    )

    route          = models.ForeignKey(TransportRoute, on_delete=models.CASCADE, related_name='schedules')
    vehicle        = models.ForeignKey(TransportVehicle, on_delete=models.SET_NULL, null=True, blank=True, related_name='schedules')
    departure_date = models.DateField()
    departure_time = models.TimeField()
    arrival_time   = models.TimeField(null=True, blank=True)
    total_seats    = models.IntegerField(default=18)
    status         = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    repeat         = models.CharField(max_length=20, choices=REPEAT_CHOICES, default='none')
    notes          = models.TextField(blank=True, null=True)
    is_active      = models.BooleanField(default=True)

    class Meta:
        ordering = ['departure_date', 'departure_time']
        unique_together = ('route', 'departure_date', 'departure_time')

    def __str__(self):
        return f"{self.route} — {self.departure_date} {self.departure_time}"

    @property
    def available_seats(self):
        """Always computed — never stored."""
        booked = self.seats.filter(status='booked').count()
        return self.total_seats - booked

    @property
    def is_available(self):
        return self.status == 'scheduled' and self.available_seats > 0


class ScheduleFare(TimeStampedModel):
    """Pricing per seat class per schedule."""
    SEAT_CLASS_CHOICES = (
        ('economy',  'Economy'),
        ('business', 'Business'),
        ('first',    'First Class'),
        ('vip',      'VIP'),
        ('child',    'Child'),
        ('student',  'Student'),
        ('senior',   'Senior'),
    )

    schedule   = models.ForeignKey(TransportSchedule, on_delete=models.CASCADE, related_name='fares')
    seat_class = models.CharField(max_length=20, choices=SEAT_CLASS_CHOICES, default='economy')
    price      = models.DecimalField(max_digits=10, decimal_places=2)
    is_active  = models.BooleanField(default=True)

    class Meta:
        unique_together = ('schedule', 'seat_class')

    def __str__(self):
        return f"{self.schedule} — {self.seat_class}: ₦{self.price}"


class TransportSeat(TimeStampedModel):
    """Individual seat on a schedule."""
    STATUS_CHOICES = (
        ('available',   'Available'),
        ('reserved',    'Reserved'),
        ('booked',      'Booked'),
        ('blocked',     'Blocked'),
        ('maintenance', 'Under Maintenance'),
    )
    SEAT_CLASS_CHOICES = (
        ('economy',  'Economy'),
        ('business', 'Business'),
        ('first',    'First Class'),
        ('vip',      'VIP'),
    )

    schedule    = models.ForeignKey(TransportSchedule, on_delete=models.CASCADE, related_name='seats')
    seat_number = models.CharField(max_length=10, help_text='e.g. 1A, 12B, 5')
    seat_class  = models.CharField(max_length=20, choices=SEAT_CLASS_CHOICES, default='economy')
    status      = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    is_window   = models.BooleanField(default=False)
    is_aisle    = models.BooleanField(default=False)
    is_disabled_friendly = models.BooleanField(default=False)

    class Meta:
        ordering = ['seat_number']
        unique_together = ('schedule', 'seat_number')

    def __str__(self):
        return f"{self.schedule} — Seat {self.seat_number} ({self.seat_class})"


class TransportBooking(TimeStampedModel):
    """A customer's purchase of one or more tickets."""
    STATUS_CHOICES = (
        ('pending',   'Pending Payment'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('refunded',  'Refunded'),
        ('completed', 'Completed'),
    )
    PAYMENT_STATUS_CHOICES = (
        ('unpaid',   'Unpaid'),
        ('paid',     'Paid'),
        ('refunded', 'Refunded'),
    )

    schedule         = models.ForeignKey(TransportSchedule, on_delete=models.PROTECT, related_name='bookings')
    customer         = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='transport_bookings')
    reference        = models.CharField(max_length=100, unique=True)
    total_amount     = models.DecimalField(max_digits=10, decimal_places=2)
    status           = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_status   = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='unpaid')
    payment_method   = models.CharField(max_length=20, blank=True, null=True)
    payment_reference= models.CharField(max_length=100, blank=True, null=True)
    cancelled_at     = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True, null=True)
    refund_amount    = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Booking {self.reference} — {self.customer}"

    @property
    def passenger_count(self):
        return self.passengers.count()


class TransportPassenger(TimeStampedModel):
    """Individual passenger within a booking."""
    BOARDING_STATUS_CHOICES = (
        ('pending',    'Pending'),
        ('checked_in', 'Checked In'),
        ('boarding',   'Boarding'),
        ('boarded',    'Boarded'),
        ('no_show',    'No Show'),
    )

    booking      = models.ForeignKey(TransportBooking, on_delete=models.CASCADE, related_name='passengers')
    seat         = models.OneToOneField(TransportSeat, on_delete=models.SET_NULL, null=True, blank=True, related_name='passenger')
    name         = models.CharField(max_length=255)
    phone        = models.CharField(max_length=20, blank=True, null=True)
    email        = models.EmailField(blank=True, null=True)
    seat_class   = models.CharField(max_length=20, default='economy')
    amount       = models.DecimalField(max_digits=10, decimal_places=2)
    ticket_code  = models.CharField(max_length=20, unique=True, blank=True, null=True)
    boarding_status = models.CharField(max_length=20, choices=BOARDING_STATUS_CHOICES, default='pending')
    boarded_at   = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['booking', 'name']

    def __str__(self):
        return f"{self.name} — {self.booking.reference}"

    def generate_ticket_code(self):
        import uuid
        self.ticket_code = uuid.uuid4().hex[:8].upper()
        self.save()


class TransportBoardingLog(TimeStampedModel):
    """Audit log of boarding scan events."""
    passenger  = models.ForeignKey(TransportPassenger, on_delete=models.CASCADE, related_name='boarding_logs')
    scanned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    action     = models.CharField(max_length=20, help_text='e.g. check_in, board, reject')
    device_id  = models.CharField(max_length=100, blank=True, null=True)
    lat        = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    lng        = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    notes      = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.passenger.name} — {self.action}"


class TransportScheduleTracking(TimeStampedModel):
    """Real-time status updates for a schedule."""
    schedule    = models.ForeignKey(TransportSchedule, on_delete=models.CASCADE, related_name='tracking')
    status      = models.CharField(max_length=30)
    description = models.TextField(blank=True, null=True)
    city        = models.CharField(max_length=100, blank=True, null=True)
    lat         = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    lng         = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    reported_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.schedule} — {self.status}"


class TransportCancellationPolicy(TimeStampedModel):
    """Refund rules per business based on hours before departure."""
    business            = models.ForeignKey('marketplace.Business', on_delete=models.CASCADE, related_name='cancellation_policies')
    hours_before        = models.IntegerField(help_text='Hours before departure this rule applies')
    refund_percentage   = models.DecimalField(max_digits=5, decimal_places=2, help_text='e.g. 100 = full refund, 0 = no refund')
    description         = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        ordering = ['business', '-hours_before']

    def __str__(self):
        return f"{self.business.name} — {self.hours_before}hrs: {self.refund_percentage}% refund"


class ScheduleDriverAssignment(TimeStampedModel):
    """Audit history of driver assignments to schedules."""
    schedule    = models.ForeignKey(TransportSchedule, on_delete=models.CASCADE, related_name='driver_assignments')
    driver      = models.ForeignKey(DriverProfile, on_delete=models.CASCADE, related_name='schedule_assignments')
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    assigned_at = models.DateTimeField(auto_now_add=True)
    removed_at  = models.DateTimeField(null=True, blank=True)
    notes       = models.TextField(blank=True, null=True)
    is_active   = models.BooleanField(default=True)

    class Meta:
        ordering = ['-assigned_at']

    def __str__(self):
        return f"{self.schedule} — {self.driver}"


class TransportBaggage(TimeStampedModel):
    """Baggage registered under a passenger."""
    STATUS_CHOICES = (
        ('registered', 'Registered'),
        ('loaded',     'Loaded'),
        ('delivered',  'Delivered'),
        ('lost',       'Lost'),
        ('damaged',    'Damaged'),
    )

    passenger  = models.ForeignKey(TransportPassenger, on_delete=models.CASCADE, related_name='baggage')
    tag_number = models.CharField(max_length=50, unique=True, blank=True, null=True)
    weight_kg  = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    description= models.CharField(max_length=255, blank=True, null=True)
    fee        = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status     = models.CharField(max_length=20, choices=STATUS_CHOICES, default='registered')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.passenger.name} — Bag {self.tag_number or '—'}"


class TransportRating(TimeStampedModel):
    """Customer rating for a transport booking."""
    booking        = models.OneToOneField(TransportBooking, on_delete=models.CASCADE, related_name='rating')
    overall_rating = models.IntegerField()
    driver_rating  = models.IntegerField(null=True, blank=True)
    vehicle_rating = models.IntegerField(null=True, blank=True)
    review         = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.booking.reference} — {self.overall_rating}★"