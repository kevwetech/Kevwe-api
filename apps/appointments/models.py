from django.db import models
from django.conf import settings
from django.utils import timezone
from apps.common.models import TimeStampedModel
import uuid


class AppointmentCategory(models.Model):
    business = models.ForeignKey(
        'marketplace.Business',
        on_delete=models.CASCADE,
        related_name='appointment_categories'
    )
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, blank=True)
    description = models.TextField(blank=True, null=True)
    icon = models.CharField(max_length=8, blank=True, null=True)   # emoji
    image = models.ImageField(upload_to='appointments/categories/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'name']
        unique_together = [('business', 'name')]
        verbose_name_plural = 'Appointment categories'

    def __str__(self):
        return f'{self.business.name} — {self.name}'



class AppointmentService(TimeStampedModel):
    """
    A specific service offered by a business.
    e.g. Haircut, Facial, Massage, Consultation
    """
    business = models.ForeignKey(
        'marketplace.Business',
        on_delete=models.CASCADE,
        related_name='appointment_services',
    )
    category = models.ForeignKey(
        AppointmentCategory,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='services'
    )
    
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    duration_minutes = models.IntegerField(
        default=30,
        help_text='How long this service takes'
    )
    # Buffer time around appointment
    buffer_before_minutes = models.IntegerField(
        default=0,
        help_text='Prep time before appointment starts'
    )
    buffer_after_minutes = models.IntegerField(
        default=0,
        help_text='Cleanup time after appointment ends'
    )
    price = models.DecimalField(max_digits=10, decimal_places=2)
    deposit_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    max_bookings_per_slot = models.IntegerField(
        default=1,
        help_text='Max concurrent bookings for this service'
    )
    # Booking rules
    requires_staff = models.BooleanField(
        default=True,
        help_text='Can customer choose a staff member?'
    )
    requires_confirmation = models.BooleanField(
        default=False,
        help_text='Business must manually confirm bookings'
    )
    # Payments
    allow_online_payment = models.BooleanField(default=True)
    allow_cash_payment = models.BooleanField(default=True)
    # Media
    image = models.ImageField(
        upload_to='appointments/services/',
        null=True, blank=True
    )
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return f"{self.business.name} — {self.name}"

    @property
    def total_duration_minutes(self):
        """Total slot needed including buffers."""
        return (
            self.buffer_before_minutes +
            self.duration_minutes +
            self.buffer_after_minutes
        )




class AppointmentCustomField(TimeStampedModel):
    """A question a specific service asks, not the whole business.
    Bridal makeup asks for wedding date + venue; a haircut on the
    same salon doesn't — scoping to the service (not the business)
    is what keeps each customer's form relevant to what they picked."""

    FIELD_TYPES = [
        ('text',     'Text'),
        ('number',   'Number'),
        ('dropdown', 'Dropdown'),
        ('checkbox', 'Checkbox'),
        ('date',     'Date'),
        ('file',     'File upload'),
    ]

    service = models.ForeignKey(
        'AppointmentService', on_delete=models.CASCADE,
        related_name='custom_fields')
    label = models.CharField(max_length=150)
    field_type = models.CharField(max_length=20, choices=FIELD_TYPES)
    options = models.JSONField(
        blank=True, null=True,
        help_text='Dropdown choices only, e.g. ["Short", "Medium", "Long"]')
    is_required = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f'{self.service.name} — {self.label}'



class AppointmentStaff(TimeStampedModel):
    """Staff member who performs services."""
    business = models.ForeignKey(
        'marketplace.Business',
        on_delete=models.CASCADE,
        related_name='appointment_staff',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='staff_profiles',
    )
    name = models.CharField(max_length=255)
    title = models.CharField(
        max_length=100, blank=True, null=True,
        help_text='e.g. Senior Stylist, Therapist'
    )
    bio = models.TextField(blank=True, null=True)
    photo = models.ImageField(
        upload_to='appointments/staff/',
        null=True, blank=True
    )
    employee_code = models.CharField(
        max_length=50, blank=True, null=True
    )
    commission_percentage = models.DecimalField(
        max_digits=5, decimal_places=2,
        null=True, blank=True,
        help_text='Staff commission percentage per appointment'
    )
    services = models.ManyToManyField(
        AppointmentService,
        related_name='staff',
        blank=True,
    )
    is_online_bookable = models.BooleanField(
        default=True,
        help_text='Customers can choose this staff when booking online'
    )
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return f"{self.business.name} — {self.name}"

    def get_rating(self):
        """Compute rating from AppointmentRating."""
        ratings = AppointmentRating.objects.filter(
            appointment__staff=self,
            staff_rating__isnull=False
        )
        if not ratings.exists():
            return None
        return ratings.aggregate(
            models.Avg('staff_rating')
        )['staff_rating__avg']


class AppointmentSlot(TimeStampedModel):
    """
    Weekly recurring availability for a business or staff.
    """
    DAY_CHOICES = (
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    )

    business = models.ForeignKey(
        'marketplace.Business',
        on_delete=models.CASCADE,
        related_name='appointment_slots',
    )
    staff = models.ForeignKey(
        AppointmentStaff,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='slots',
    )
    day = models.IntegerField(choices=DAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    # Break time within slot
    break_start = models.TimeField(
        null=True, blank=True,
        help_text='e.g. Lunch break start'
    )
    break_end = models.TimeField(
        null=True, blank=True,
        help_text='e.g. Lunch break end'
    )
    max_bookings = models.IntegerField(
        default=1,
        help_text='Max concurrent bookings in this slot'
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['day', 'start_time']

    def __str__(self):
        return (
            f"{self.business.name} — "
            f"{self.get_day_display()} "
            f"{self.start_time}–{self.end_time}"
        )


class AppointmentAvailabilityException(TimeStampedModel):
    """
    Override normal slot availability for specific dates.
    e.g. holiday closure, extra hours, partial day
    """
    EXCEPTION_TYPE_CHOICES = (
        ('closed',      'Closed — not available'),
        ('modified',    'Modified hours'),
        ('extra',       'Extra hours added'),
    )

    business = models.ForeignKey(
        'marketplace.Business',
        on_delete=models.CASCADE,
        related_name='availability_exceptions',
    )
    staff = models.ForeignKey(
        AppointmentStaff,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='availability_exceptions',
    )
    date = models.DateField()
    exception_type = models.CharField(
        max_length=20,
        choices=EXCEPTION_TYPE_CHOICES,
        default='closed',
    )
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    reason = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        ordering = ['date']

    def __str__(self):
        return f"{self.business.name} — {self.date} ({self.exception_type})"


class AppointmentBlock(TimeStampedModel):
    """
    Block specific dates/times from being booked.
    e.g. staff leave, public holidays
    """
    business = models.ForeignKey(
        'marketplace.Business',
        on_delete=models.CASCADE,
        related_name='appointment_blocks',
    )
    staff = models.ForeignKey(
        AppointmentStaff,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='blocks',
    )
    date = models.DateField()
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    all_day = models.BooleanField(default=False)
    reason = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        ordering = ['date', 'start_time']

    def __str__(self):
        return f"{self.business.name} — Blocked {self.date}"


class Appointment(TimeStampedModel):
    """
    A customer's booked appointment.
    Stores snapshots of service/staff/price at booking time
    so history is preserved even if records change later.
    """
    STATUS_CHOICES = (
        ('pending',     'Pending Confirmation'),
        ('confirmed',   'Confirmed'),
        ('checked_in',  'Checked In'),
        ('in_progress', 'In Progress'),
        ('completed',   'Completed'),
        ('cancelled',   'Cancelled'),
        ('no_show',     'No Show'),
        ('rescheduled', 'Rescheduled'),
    )
    PAYMENT_STATUS_CHOICES = (
        ('unpaid',   'Unpaid'),
        ('deposit',  'Deposit Paid'),
        ('paid',     'Fully Paid'),
        ('refunded', 'Refunded'),
    )
    PAYMENT_METHOD_CHOICES = (
        ('card',     'Card'),
        ('wallet',   'Wallet'),
        ('cash',     'Cash'),
        ('transfer', 'Transfer'),
    )

    # Core relations
    business = models.ForeignKey(
        'marketplace.Business',
        on_delete=models.CASCADE,
        related_name='appointments',
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='appointments',
    )
    service = models.ForeignKey(
        AppointmentService,
        on_delete=models.PROTECT,
        related_name='appointments',
    )
    staff = models.ForeignKey(
        AppointmentStaff,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='appointments',
    )

    # Reference
    reference = models.CharField(max_length=100, unique=True)
    check_in_code = models.CharField(
        max_length=10, blank=True, null=True,
        help_text='Customer shows this at reception for check-in'
    )

    # Scheduling — store start_time + duration, compute end_time
    date = models.DateField()
    start_time = models.TimeField()
    duration_minutes = models.IntegerField()
    end_time = models.TimeField(
        help_text='Computed from start_time + duration'
    )

    # Snapshots — preserve history even if service/staff changes
    service_name = models.CharField(max_length=255)
    service_price = models.DecimalField(max_digits=10, decimal_places=2)
    staff_name = models.CharField(max_length=255, blank=True, null=True)
    customer_name = models.CharField(max_length=255)
    customer_phone = models.CharField(max_length=20, blank=True, null=True)
    customer_email = models.EmailField(blank=True, null=True)

    # Pricing
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    deposit_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    platform_commission = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    business_earnings = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    staff_commission = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='unpaid',
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        null=True, blank=True,
    )
    payment_reference = models.CharField(
        max_length=100, blank=True, null=True
    )

    # Notes
    customer_note = models.TextField(blank=True, null=True)
    staff_note = models.TextField(blank=True, null=True)

    # Rescheduling
    rescheduled_from = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='rescheduled_to',
    )

    # Completed by
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='completed_appointments',
    )

    # Key timestamps
    confirmed_at = models.DateTimeField(null=True, blank=True)
    checked_in_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    deposit_paid_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-date', '-start_time']

    def __str__(self):
        return f"Appointment {self.reference} — {self.customer_name}"

    def save(self, *args, **kwargs):
        # Auto-generate reference
        if not self.reference:
            self.reference = f"APT-{uuid.uuid4().hex[:8].upper()}"
        # Auto-generate check-in code
        if not self.check_in_code:
            self.check_in_code = uuid.uuid4().hex[:6].upper()
        # Snapshot customer details
        if not self.customer_name and self.customer_id:
            self.customer_name = getattr(
                self.customer, 'full_name', '') or ''
            self.customer_phone = getattr(
                self.customer, 'phone', '') or ''
            self.customer_email = getattr(
                self.customer, 'email', '') or ''
        # Snapshot service details
        if not self.service_name and self.service_id:
            self.service_name = self.service.name
            self.service_price = self.service.price
        # Snapshot staff name
        if not self.staff_name and self.staff_id:
            self.staff_name = self.staff.name
        super().save(*args, **kwargs)

    @classmethod
    def check_overlap(cls, business, staff, date, start_time, end_time, exclude_id=None):
        """
        Returns True if a conflicting appointment exists.
        Call this before saving to prevent double-booking.
        """
        qs = cls.objects.filter(
            business=business,
            date=date,
            status__in=['pending', 'confirmed', 'checked_in', 'in_progress'],
        ).exclude(pk=exclude_id)

        if staff:
            qs = qs.filter(staff=staff)

        for appt in qs:
            # Check if times overlap
            if appt.start_time < end_time and appt.end_time > start_time:
                return True
        return False


class AppointmentTracking(TimeStampedModel):
    """Status change history for an appointment."""
    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.CASCADE,
        related_name='tracking',
    )
    status = models.CharField(max_length=20)
    note = models.TextField(blank=True, null=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
    )

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.appointment.reference} — {self.status}"


class AppointmentPayment(TimeStampedModel):
    """
    Payment record for an appointment.
    Links to the central Payment model.
    """
    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.CASCADE,
        related_name='payments',
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_type = models.CharField(
        max_length=20,
        choices=(
            ('deposit', 'Deposit'),
            ('full',    'Full Payment'),
            ('balance', 'Balance Payment'),
            ('refund',  'Refund'),
        ),
        default='full',
    )
    payment_method = models.CharField(max_length=20)
    reference = models.CharField(max_length=100, unique=True)
    status = models.CharField(
        max_length=20,
        choices=(
            ('pending',  'Pending'),
            ('success',  'Success'),
            ('failed',   'Failed'),
            ('refunded', 'Refunded'),
        ),
        default='pending',
    )
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.appointment.reference} — {self.payment_type} ₦{self.amount}"


class AppointmentRating(TimeStampedModel):
    """Customer rating after appointment completion."""
    appointment = models.OneToOneField(
        Appointment,
        on_delete=models.CASCADE,
        related_name='rating',
    )
    overall_rating = models.IntegerField()
    staff_rating = models.IntegerField(null=True, blank=True)
    cleanliness_rating = models.IntegerField(null=True, blank=True)
    value_rating = models.IntegerField(null=True, blank=True)
    review = models.TextField(blank=True, null=True)
    is_public = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.appointment.reference} — {self.overall_rating}★"


class AppointmentWaitlist(TimeStampedModel):
    """
    Customer joins waitlist when preferred slot is fully booked.
    Notified automatically when a cancellation opens the slot.
    """
    STATUS_CHOICES = (
        ('waiting',   'Waiting'),
        ('notified',  'Notified'),
        ('booked',    'Converted to Booking'),
        ('expired',   'Expired'),
        ('cancelled', 'Cancelled'),
    )

    business = models.ForeignKey(
        'marketplace.Business',
        on_delete=models.CASCADE,
        related_name='appointment_waitlist',
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='appointment_waitlist',
    )
    service = models.ForeignKey(
        AppointmentService,
        on_delete=models.CASCADE,
        related_name='waitlist',
    )
    staff = models.ForeignKey(
        AppointmentStaff,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='waitlist',
    )
    preferred_date = models.DateField()
    preferred_start_time = models.TimeField(null=True, blank=True)
    flexible_time = models.BooleanField(
        default=False,
        help_text='Customer is flexible on time'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='waiting',
    )
    notified_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='from_waitlist',
        help_text='Set when converted to booking'
    )

    class Meta:
        ordering = ['preferred_date', 'created_at']

    def __str__(self):
        return f"{self.customer} waiting for {self.service.name} on {self.preferred_date}"


class AppointmentReminder(TimeStampedModel):
    """Reminders sent to customers."""
    REMINDER_TYPE_CHOICES = (
        ('24h',    '24 Hours Before'),
        ('2h',     '2 Hours Before'),
        ('1h',     '1 Hour Before'),
        ('custom', 'Custom'),
    )
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('sent',    'Sent'),
        ('failed',  'Failed'),
    )

    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.CASCADE,
        related_name='reminders',
    )
    reminder_type = models.CharField(
        max_length=20,
        choices=REMINDER_TYPE_CHOICES,
        default='24h',
    )
    scheduled_at = models.DateTimeField()
    sent_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
    )
    channel = models.CharField(
        max_length=20,
        default='sms',
        help_text='sms, email, whatsapp, push'
    )
    message_id = models.CharField(
        max_length=100, blank=True, null=True,
        help_text='ID returned by SMS/notification provider'
    )

    class Meta:
        ordering = ['scheduled_at']

    def __str__(self):
        return f"{self.appointment.reference} — {self.reminder_type} reminder ({self.status})"