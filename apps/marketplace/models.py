from django.db import models
from django.conf import settings
from apps.common.models import TimeStampedModel


class Industry(TimeStampedModel):
    """
    Top-level industry grouping.
    e.g. Hospitality, Food & Beverage, Auto Services,
    Home Services, Health & Beauty, Retail, Logistics
    """
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('coming_soon', 'Coming Soon'),
        ('inactive', 'Inactive'),
    )
    INTERACTION_TYPE_CHOICES = (
        ('orders', 'Orders (delivery/pickup)'),
        ('bookings', 'Bookings (reservations)'),
        ('service_requests', 'Service Requests (on-demand)'),
        ('rides', 'Rides (transport)'),
        ('mixed', 'Mixed (multiple interaction types)'),
    )

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True, null=True)
    icon = models.CharField(
        max_length=100, blank=True, null=True,
        help_text='Icon name or emoji'
    )
    image = models.ImageField(
        upload_to='marketplace/industries/',
        null=True, blank=True
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active'
    )
    # Default interaction type for this industry
    # BusinessCategory can override this per category
    default_interaction_type = models.CharField(
        max_length=20,
        choices=INTERACTION_TYPE_CHOICES,
        default='orders',
    )
    # Platform-wide commission defaults for this industry
    platform_commission = models.DecimalField(
        max_digits=5, decimal_places=2, default=10.00
    )
    driver_commission = models.DecimalField(
        max_digits=5, decimal_places=2, default=20.00
    )
    vendor_commission = models.DecimalField(
        max_digits=5, decimal_places=2, default=70.00
    )
    is_featured = models.BooleanField(default=False)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']
        verbose_name_plural = 'Industries'

    def __str__(self):
        return self.name


class BusinessCategory(TimeStampedModel):
    industry = models.ForeignKey(
        Industry,
        on_delete=models.CASCADE,
        related_name='categories'
    )
    name = models.CharField(max_length=100)
    slug = models.SlugField()
    description = models.TextField(blank=True, null=True)
    icon = models.CharField(
        max_length=100, blank=True, null=True
    )
    image = models.ImageField(
        upload_to='marketplace/categories/',
        null=True, blank=True
    )
    # Matches existing DB column name
    interaction_type = models.CharField(
        max_length=20,
        choices=Industry.INTERACTION_TYPE_CHOICES,
        blank=True, null=True,
        help_text='Override industry interaction type'
    )
    platform_commission = models.DecimalField(
        max_digits=5, decimal_places=2,
        null=True, blank=True
    )
    has_order_settings = models.BooleanField(default=False)
    has_booking_settings = models.BooleanField(default=False)
    has_service_settings = models.BooleanField(default=False)
    requires_certification = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']
        unique_together = ('industry', 'slug')
        verbose_name_plural = 'Business Categories'

    def __str__(self):
        return f"{self.industry.name} → {self.name}"

    @property
    def effective_interaction_type(self):
        return (
            self.interaction_type
            or self.industry.default_interaction_type
        )


class Business(TimeStampedModel):
    """
    Core business identity model — lean and focused.
    Industry-specific behaviour lives in separate
    settings models (OrderSettings, BookingSettings,
    ServiceSettings).
    """
    STATUS_CHOICES = (
        ('draft', 'Draft — setup incomplete'),
        ('pending', 'Pending Approval'),
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('rejected', 'Rejected'),
        ('closed', 'Closed Permanently'),
    )

    # ── Ownership ──────────────────────────────────────
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='businesses'
    )

    # ── Classification ────────────────────────────────
    industry = models.ForeignKey(
        Industry,
        on_delete=models.PROTECT,
        related_name='businesses'
    )
    category = models.ForeignKey(
        BusinessCategory,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='businesses',
        help_text='Sub-category within the industry'
    )

    # ── Identity ──────────────────────────────────────
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True, null=True)
    tagline = models.CharField(
        max_length=255, blank=True, null=True
    )

    # ── Media ─────────────────────────────────────────
    logo = models.ImageField(
        upload_to='marketplace/businesses/logos/',
        null=True, blank=True
    )
    cover_image = models.ImageField(
        upload_to='marketplace/businesses/covers/',
        null=True, blank=True
    )

    # ── Contact ───────────────────────────────────────
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(
        max_length=20, blank=True, null=True
    )
    whatsapp = models.CharField(
        max_length=20, blank=True, null=True
    )
    website = models.URLField(blank=True, null=True)

    # ── Location ──────────────────────────────────────
    address = models.TextField(blank=True, null=True)
    country = models.ForeignKey(
        'locations.Country',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='businesses'
    )
    state = models.ForeignKey(
        'locations.State',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='businesses'
    )
    city = models.ForeignKey(
        'locations.City',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='businesses'
    )
    zone = models.ForeignKey(
        'locations.Zone',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='businesses'
    )
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6,
        null=True, blank=True
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6,
        null=True, blank=True
    )

    # ── Commission override ───────────────────────────
    custom_commission = models.DecimalField(
        max_digits=5, decimal_places=2,
        null=True, blank=True,
        help_text=(
            'Override industry/category commission rate '
            'for this specific business'
        )
    )

    # ── Verification & Status ─────────────────────────
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft'
    )
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    is_open = models.BooleanField(
        default=True,
        help_text='Owner manually toggles open/closed'
    )

    rejection_reason = models.TextField(
        blank=True, null=True
    )
    approved_at = models.DateTimeField(
        null=True, blank=True
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='approved_businesses'
    )

    # ── SEO / Discovery ───────────────────────────────
    tags = models.JSONField(default=list, blank=True)
    meta_title = models.CharField(
        max_length=255, blank=True, null=True
    )
    meta_description = models.TextField(
        blank=True, null=True
    )

    class Meta:
        ordering = ['-is_featured', '-created_at']
        verbose_name_plural = 'Businesses'
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['is_verified']),
            models.Index(fields=['industry']),
            models.Index(fields=['city']),
        ]

    def __str__(self):
        return f"{self.name} ({self.industry.name})"

    @property
    def interaction_type(self):
        if self.category:
            return self.category.effective_interaction_type
        return self.industry.default_interaction_type


    @property
    def commission_rate(self):
        """Effective commission — business > category > industry."""
        if self.custom_commission:
            return self.custom_commission
        if self.category:
            return self.category.effective_commission
        return self.industry.platform_commission

    @property
    def accepts_orders(self):
        return self.interaction_type == 'orders'

    @property
    def accepts_bookings(self):
        return self.interaction_type == 'bookings'

    @property
    def accepts_service_requests(self):
        return self.interaction_type == 'service_requests'


class BusinessSettings(TimeStampedModel):
    """
    Common operational settings for all businesses.
    One per business — created automatically on business creation.
    """
    business = models.OneToOneField(
        Business,
        on_delete=models.CASCADE,
        related_name='settings'
    )
    # Hours
    opening_time = models.TimeField(null=True, blank=True)
    closing_time = models.TimeField(null=True, blank=True)
    is_24_hours = models.BooleanField(default=False)
    # Availability
    accepts_online_orders = models.BooleanField(default=True)
    accepts_walk_ins = models.BooleanField(default=True)
    accepts_reservations = models.BooleanField(default=False)
    # Notifications
    notify_owner_on_order = models.BooleanField(default=True)
    notify_owner_on_booking = models.BooleanField(default=True)
    notify_owner_sms = models.BooleanField(default=False)
    notify_owner_whatsapp = models.BooleanField(default=True)
    # Auto-accept
    auto_accept_orders = models.BooleanField(
        default=False,
        help_text='Automatically confirm incoming orders'
    )
    auto_accept_bookings = models.BooleanField(
        default=False,
        help_text='Automatically confirm incoming bookings'
    )
    # Ratings
    show_rating = models.BooleanField(default=True)
    allow_reviews = models.BooleanField(default=True)
    # Payout
    settlement_period_days = models.IntegerField(
        default=1,
        help_text='Days before earnings are released'
    )

    class Meta:
        verbose_name_plural = 'Business Settings'

    def __str__(self):
        return f"Settings — {self.business.name}"


class OrderSettings(TimeStampedModel):
    """
    Settings for businesses that accept orders
    (restaurants, grocery, pharmacy, laundry, retail).
    Only created for businesses whose category has
    has_order_settings=True.
    """
    business = models.OneToOneField(
        Business,
        on_delete=models.CASCADE,
        related_name='order_settings'
    )
    # Delivery
    delivery_enabled = models.BooleanField(default=True)
    delivery_fee = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    free_delivery_above = models.DecimalField(
        max_digits=10, decimal_places=2,
        null=True, blank=True,
        help_text='Free delivery when order total exceeds this'
    )
    delivery_radius_km = models.DecimalField(
        max_digits=5, decimal_places=2, default=5.00
    )
    estimated_delivery_minutes = models.IntegerField(default=30)
    # Pickup
    pickup_enabled = models.BooleanField(default=True)
    estimated_pickup_minutes = models.IntegerField(default=15)
    # Order constraints
    min_order_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    max_order_amount = models.DecimalField(
        max_digits=10, decimal_places=2,
        null=True, blank=True
    )
    # Scheduling
    allows_scheduled_orders = models.BooleanField(
        default=False,
        help_text='Customers can place orders for a future time'
    )
    max_schedule_days_ahead = models.IntegerField(default=7)
    # Packaging
    packaging_fee = models.DecimalField(
        max_digits=8, decimal_places=2, default=0
    )
    # Payments
    accepts_cash_on_delivery = models.BooleanField(
        default=False
    )
    accepts_card = models.BooleanField(default=True)
    accepts_wallet = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = 'Order Settings'

    def __str__(self):
        return f"Order Settings — {self.business.name}"


class BookingSettings(TimeStampedModel):
    """
    Settings for businesses that accept bookings
    (hotels, apartments, salons, event centers,
    photographers, etc).
    Only created for businesses whose category has
    has_booking_settings=True.
    """
    business = models.OneToOneField(
        Business,
        on_delete=models.CASCADE,
        related_name='booking_settings'
    )
    # Check-in / check-out (hotels, apartments)
    check_in_time = models.TimeField(
        null=True, blank=True,
        help_text='e.g. 14:00 for hotels'
    )
    check_out_time = models.TimeField(
        null=True, blank=True,
        help_text='e.g. 12:00 for hotels'
    )
    min_stay_nights = models.IntegerField(
        default=1,
        help_text='Minimum nights per booking (hotels)'
    )
    max_stay_nights = models.IntegerField(
        null=True, blank=True,
        help_text='Maximum nights (null = no limit)'
    )
    # Advance booking
    min_advance_hours = models.IntegerField(
        default=1,
        help_text='Minimum hours in advance a booking can be made'
    )
    max_advance_days = models.IntegerField(
        default=365,
        help_text='How far ahead customers can book'
    )
    # Cancellation
    cancellation_hours = models.IntegerField(
        default=24,
        help_text=(
            'Hours before check-in that free cancellation '
            'is allowed'
        )
    )
    cancellation_fee = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text='Fee charged for late cancellation'
    )
    cancellation_fee_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        help_text='Percentage of booking total charged for late cancellation'
    )
    # Deposits
    requires_deposit = models.BooleanField(default=False)
    deposit_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        help_text='Percentage of total required as deposit'
    )
    # KYC
    requires_guest_kyc = models.BooleanField(
        default=False,
        help_text='Guests must complete identity verification before booking'
    )
    # Capacity
    max_guests_per_booking = models.IntegerField(
        null=True, blank=True
    )
    # Availability
    instant_booking = models.BooleanField(
        default=True,
        help_text='Book immediately without host approval'
    )

    class Meta:
        verbose_name_plural = 'Booking Settings'

    def __str__(self):
        return f"Booking Settings — {self.business.name}"


class ServiceSettings(TimeStampedModel):
    """
    Settings for businesses that accept on-demand
    service requests (mechanics, plumbers, electricians,
    cleaners, etc).
    Only created for businesses whose category has
    has_service_settings=True.
    """
    business = models.OneToOneField(
        Business,
        on_delete=models.CASCADE,
        related_name='service_settings'
    )
    # Dispatch
    is_mobile = models.BooleanField(
        default=True,
        help_text='Provider travels to customer'
    )
    is_on_site = models.BooleanField(
        default=False,
        help_text='Customer visits provider location'
    )
    operating_radius_km = models.DecimalField(
        max_digits=6, decimal_places=2, default=15.00
    )
    # Inspection
    inspection_fee = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    inspection_fee_required = models.BooleanField(
        default=True,
        help_text=(
            'Customer pays inspection fee before '
            'quote is generated'
        )
    )
    # Pricing
    default_pricing_type = models.CharField(
        max_length=20,
        choices=(
            ('fixed_price', 'Fixed Price'),
            ('inspection_quote', 'Inspection → Quote'),
            ('custom_quote', 'Custom Quote'),
            ('hourly', 'Hourly Rate'),
            ('daily', 'Daily Rate'),
        ),
        default='inspection_quote'
    )
    hourly_rate = models.DecimalField(
        max_digits=10, decimal_places=2,
        null=True, blank=True
    )
    # Emergency
    accepts_emergency = models.BooleanField(
        default=False,
        help_text='Provider handles emergency requests'
    )
    emergency_surcharge_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=0
    )
    # Response
    response_time_minutes = models.IntegerField(
        default=30,
        help_text='Estimated response time in minutes'
    )
    # Insurance
    is_insured = models.BooleanField(default=False)
    insurance_provider = models.CharField(
        max_length=255, blank=True, null=True
    )
    insurance_policy_number = models.CharField(
        max_length=100, blank=True, null=True
    )
    insurance_expires_at = models.DateField(
        null=True, blank=True
    )

    class Meta:
        verbose_name_plural = 'Service Settings'

    def __str__(self):
        return f"Service Settings — {self.business.name}"


class BusinessHours(TimeStampedModel):
    """Per-day business hours."""
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
        Business,
        on_delete=models.CASCADE,
        related_name='hours'
    )
    day = models.IntegerField(choices=DAY_CHOICES)
    is_open = models.BooleanField(default=True)
    opening_time = models.TimeField()
    closing_time = models.TimeField()
    is_24_hours = models.BooleanField(default=False)

    class Meta:
        ordering = ['day']
        unique_together = ('business', 'day')

    def __str__(self):
        return (
            f"{self.business.name} — "
            f"{self.get_day_display()}"
        )


class BusinessImage(TimeStampedModel):
    """Gallery images for a business."""
    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name='images'
    )
    image = models.ImageField(
        upload_to='marketplace/businesses/gallery/'
    )
    caption = models.CharField(
        max_length=255, blank=True, null=True
    )
    is_primary = models.BooleanField(default=False)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.business.name} — image"


class BusinessDocument(TimeStampedModel):
    """
    Business verification documents.
    CAC, food license, professional certificates, etc.
    """
    DOCUMENT_TYPE_CHOICES = (
        ('cac_certificate', 'CAC Certificate'),
        ('cac_status_report', 'CAC Status Report'),
        ('tin_certificate', 'TIN Certificate'),
        ('tax_clearance', 'Tax Clearance'),
        ('food_license', 'Food Handler License'),
        ('health_license', 'Health Facility License'),
        ('business_permit', 'Business Permit'),
        ('professional_license', 'Professional License'),
        ('id_card', 'Owner ID Card'),
        ('utility_bill', 'Utility Bill'),
        ('other', 'Other'),
    )
    STATUS_CHOICES = (
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('expired', 'Expired'),
    )

    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name='documents'
    )
    document_type = models.CharField(
        max_length=30,
        choices=DOCUMENT_TYPE_CHOICES
    )
    document_file = models.FileField(
        upload_to='marketplace/documents/'
    )
    document_number = models.CharField(
        max_length=100, blank=True, null=True,
        help_text='CAC number, TIN, license number, etc.'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    notes = models.TextField(blank=True, null=True)
    expiry_date = models.DateField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='reviewed_business_docs'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('business', 'document_type')

    def __str__(self):
        return (
            f"{self.business.name} — "
            f"{self.document_type}"
        )