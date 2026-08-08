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
    INTERACTION_TYPE_CHOICES = [
        ('orders',             'Orders (delivery/pickup)'),
        ('bookings',           'Bookings (hotels/apartments)'),
        ('services',           'Service Requests (quote-based)'),
        ('appointments',       'Appointments (fixed time slots)'),
        ('scheduled_services', 'Scheduled Services (provider visits customer)'),
        ('rides',              'Rides (on-demand hailing)'),
        ('transport',          'Transport (scheduled routes & seats)'),   # NEW
        ('shipments',          'Shipments (package delivery)'),           # NEW
        ('mixed',              'Mixed'),
    ]
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
    industry = models.ForeignKey(Industry, on_delete=models.CASCADE, related_name='categories')
    name = models.CharField(max_length=100)
    slug = models.SlugField()
    description = models.TextField(blank=True, null=True)
    icon = models.CharField(max_length=100, blank=True, null=True)
    image = models.ImageField(upload_to='marketplace/categories/', null=True, blank=True)
    platform_commission = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    requires_certification = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)
    

    interaction_type = models.CharField(
        max_length=32, choices=Industry.INTERACTION_TYPE_CHOICES,
        null=True, blank=True,
        verbose_name='Primary interaction',
        help_text='The DEFAULT experience — first tab and main CTA. '
                  'Blank inherits the industry default. This is not the '
                  'only capability; tick everything offered below.',
    )

    # ── Enabled interactions ──
    has_order_settings = models.BooleanField(
        default=False, verbose_name='Orders',
        help_text='Delivery / pickup of products')
    has_booking_settings = models.BooleanField(
        default=False, verbose_name='Bookings',
        help_text='Rooms, tables, halls — reserving time and space')
    has_appointment_settings = models.BooleanField(
        default=False, verbose_name='Appointments',
        help_text='Fixed time slots with a staff member')
    has_service_settings = models.BooleanField(
        default=False, verbose_name='Services',
        help_text='Quote-based service requests')
    has_scheduled_service_settings = models.BooleanField(
        default=False, verbose_name='Scheduled services',
        help_text='Provider travels to the customer')
    has_ride_settings = models.BooleanField(
        default=False, verbose_name='Rides',
        help_text='On-demand vehicle hailing')
    has_transport_settings = models.BooleanField(
        default=False, verbose_name='Transport',
        help_text='Scheduled routes and seat booking')
    has_shipment_settings = models.BooleanField(
        default=False, verbose_name='Shipments',
        help_text='Package delivery and tracking')

    INTERACTION_FLAGS = {
        'orders':             'has_order_settings',
        'bookings':           'has_booking_settings',
        'appointments':       'has_appointment_settings',
        'services':           'has_service_settings',
        'scheduled_services': 'has_scheduled_service_settings',
        'rides':              'has_ride_settings',
        'transport':          'has_transport_settings',
        'shipments':          'has_shipment_settings',
    }

    class Meta:
        ordering = ['order', 'name']
        unique_together = ('industry', 'slug')
        verbose_name_plural = 'Business Categories'

    def __str__(self):
        return f"{self.industry.name} → {self.name}"

    @property
    def effective_interaction_type(self):
        """Explicit primary, else the industry's default."""
        return self.interaction_type or self.industry.default_interaction_type

    @property
    def enabled_interactions(self):
        """Capabilities this category permits — primary first."""
        types = [t for t, flag in self.INTERACTION_FLAGS.items()
                 if getattr(self, flag, False)]
        primary = self.effective_interaction_type
        if primary and primary != 'mixed':
            if primary in types:
                types.remove(primary)
            types.insert(0, primary)
        return types

    def clean(self):
        """Primary must be one of the enabled capabilities."""
        from django.core.exceptions import ValidationError
        primary = self.interaction_type
        if primary and primary != 'mixed':
            flag = self.INTERACTION_FLAGS.get(primary)
            if flag and not getattr(self, flag, False):
                raise ValidationError({'interaction_type':
                    f'"{primary}" is set as primary but is not ticked under '
                    f'Enabled interactions.'})



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
    CREDENTIAL_BADGES = {
        'cac_certificate':  'CAC Registered',
        'business_license': 'Licensed Business',
        'tax_clearance':    'Tax Cleared',
        'tin_certificate':  'Tax Registered',
        'director_id':      'ID Verified',
    }

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
    story = models.TextField(
        blank=True, null=True,
        help_text="The business's own account of itself — how it started, "
                  "what it does. Shown on the About tab.")
    mission = models.TextField(
        blank=True, null=True,
        help_text='What the business is trying to do. Optional.'
    )
    services_overview = models.TextField(
        blank=True, null=True,
        help_text="For service-type businesses — what you do and how you "
                  "work. Shown on the About tab. E.g. a mechanic's specialties, "
                  "a salon's approach, a cleaner's process."
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
    def interaction_types(self):
        """Capabilities this business operates: what the category
        permits, narrowed to what's actually configured."""
        permitted = self.category.enabled_interactions if self.category else []
        primary = self.interaction_type
        if not permitted:
            return [primary] if primary else []

        SETTINGS_ATTR = {
            'orders':             'order_settings',
            'bookings':           'booking_settings',
            'appointments':       'appointment_settings',
            'services':           'service_settings',
            'scheduled_services': 'service_settings',   # shared with services
            'rides':              'ride_settings',
            'transport':          'ride_settings',      # shared with rides
            'shipments':          'shipment_settings',
        }

        active = []
        for t in permitted:
            attr = SETTINGS_ATTR.get(t)
            if attr is None or hasattr(self, attr):
                active.append(t)

        if primary and primary not in active:
            active.insert(0, primary)      # primary always renders
        return active

    @property
    def commission_rate(self):
        """Effective commission — business > category > industry."""
        if self.custom_commission is not None:
            return self.custom_commission
        if self.category and self.category.platform_commission is not None:
            return self.category.platform_commission
        if self.industry and self.industry.platform_commission is not None:
            return self.industry.platform_commission
        return 0

        
    @property
    def accepts_orders(self):
        return self.interaction_type == 'orders'

    @property
    def accepts_bookings(self):
        return self.interaction_type == 'bookings'

    @property
    def accepts_service_requests(self):
        return self.interaction_type == 'services'
    
    @property
    def verified_badges(self):
        """Credential chips, derived entirely from approved KYC —
        never typed by the business owner. business_kyc must ALSO be
        approved (not just the individual document) so a business
        mid-review with one lucky approved doc doesn't show a badge."""
        from apps.kyc.models import BusinessKYCDocument
        doc_types = set(BusinessKYCDocument.objects.filter(
            business_kyc__business_id=self.id,
            business_kyc__status='approved',
            status='approved',
        ).values_list('document_type', flat=True))

        badges = [
            {'type': t, 'label': label}
            for t, label in self.CREDENTIAL_BADGES.items() if t in doc_types
        ]
        # CAC/license make "ID Verified" redundant noise
        if any(b['type'] in ('cac_certificate', 'business_license') for b in badges):
            badges = [b for b in badges if b['type'] != 'director_id']
        return badges

    @property
    def interaction_forms(self):
        """{ 'bookings': { 'form_key': 'hotel_booking', 'page_url': 'hotel-booking.html' }, ... }
        Falls back silently when nothing's configured — renderers
        default to today's page names, so this ships with zero
        business-breaking risk before any InteractionForm rows exist."""
        out = {}
        for t in self.interaction_types:
            row = InteractionForm.resolve(t, self)
            if row:
                out[t] = {'form_key': row.form_key, 'page_url': row.page_url}
        return out


class BusinessFAQ(TimeStampedModel):
    """Questions a business answers about itself.

    Distinct from cms.FAQ, which answers questions about Kevwe.
    "Do you allow pets?" is this. "How do I sign up?" is cms.FAQ.
    """
    business = models.ForeignKey(
        'Business', on_delete=models.CASCADE, related_name='faqs')
    question = models.CharField(max_length=200)
    answer = models.TextField()
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order', 'id']
        verbose_name = 'Business FAQ'
        verbose_name_plural = 'Business FAQs'

    def __str__(self):
        return f'{self.business.name} — {self.question[:60]}'


class BusinessPromotion(TimeStampedModel):
    """Something a business wants pinned above its catalog.

    Offers and notices are merged deliberately: both render as the
    same strip and differ only in whether money is attached.
    "20% off this weekend" is an OFFER; "Closed Dec 25" is a NOTICE.
    Two near-identical tables would drift.
    """
    KIND_OFFER  = 'offer'
    KIND_NOTICE = 'notice'
    KIND_CHOICES = [
        (KIND_OFFER,  'Offer — a deal, discount or bonus'),
        (KIND_NOTICE, 'Notice — an announcement with no offer attached'),
    ]

    business = models.ForeignKey(
        'Business', on_delete=models.CASCADE, related_name='page_promotions')
    kind = models.CharField(max_length=10, choices=KIND_CHOICES, default=KIND_OFFER)

    title = models.CharField(
        max_length=80,
        help_text='Short and scannable — "20% off this weekend", "Free delivery"')
    description = models.TextField(blank=True, null=True)
    icon = models.CharField(
        max_length=8, blank=True, null=True,
        help_text='Emoji shown on the strip')
    image = models.ImageField(
        upload_to='marketplace/promotions/', blank=True, null=True)

    # Time bounds are not optional in spirit: a weekend promo still
    # showing in March is worse than no promo at all. Filtered
    # server-side in the queryset, never trusted to the client.
    starts_at = models.DateTimeField(
        null=True, blank=True,
        help_text='Blank = live immediately')
    ends_at = models.DateTimeField(
        null=True, blank=True,
        help_text='Blank = runs until switched off. Set this.')

    cta_label = models.CharField(
        max_length=40, blank=True, null=True,
        help_text='Optional button text — "Order now", "See rooms"')
    cta_url = models.CharField(
        max_length=300, blank=True, null=True,
        help_text='Where the button goes. Relative paths allowed.')

    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order', '-created_at']
        verbose_name = 'Business promotion'
        verbose_name_plural = 'Business promotions'

    def __str__(self):
        return f'{self.business.name} — {self.title}'

    @property
    def is_live(self):
        from django.utils import timezone
        now = timezone.now()
        if not self.is_active:
            return False
        if self.starts_at and self.starts_at > now:
            return False
        if self.ends_at and self.ends_at < now:
            return False
        return True

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            raise ValidationError({'ends_at': 'Must be after the start.'})


class BusinessPolicy(TimeStampedModel):
    """House rules — refunds, cancellation, check-in.

    These are the business's own terms, published immediately. They
    are not verified claims and carry no badge. Escrow dispute terms
    surface here too.
    """
    TYPE_CHOICES = [
        ('cancellation', 'Cancellation'),
        ('refund',       'Refund'),
        ('checkin',      'Check-in / Check-out'),
        ('delivery',     'Delivery'),
        ('warranty',     'Warranty'),
        ('house_rules',  'House rules'),
        ('privacy',      'Privacy'),
        ('other',        'Other'),
    ]

    business = models.ForeignKey(
        'Business', on_delete=models.CASCADE, related_name='policies')
    policy_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='other')
    title = models.CharField(
        max_length=100,
        help_text='Blank-ish titles help nobody — "Free cancellation up to 24h"')
    content = models.TextField()
    icon = models.CharField(max_length=8, blank=True, null=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order', 'id']
        verbose_name = 'Business policy'
        verbose_name_plural = 'Business policies'

    def __str__(self):
        return f'{self.business.name} — {self.title}'


class BusinessContentBlock(TimeStampedModel):
    """The single escape hatch.

    Everything a business commonly needs has a structured model, so
    the page stays predictable across industries. This exists for the
    genuinely unusual — and stays one flat title+content pair on
    purpose. The moment it grows a `block_type` enum, every business
    page becomes a different shape and the marketplace loses the
    consistency that makes it navigable.
    """
    business = models.ForeignKey(
        'Business', on_delete=models.CASCADE, related_name='content_blocks')
    title = models.CharField(max_length=120)
    content = models.TextField()
    image = models.ImageField(
        upload_to='marketplace/blocks/', blank=True, null=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order', 'id']
        verbose_name = 'Business content block'
        verbose_name_plural = 'Business content blocks'

    def __str__(self):
        return f'{self.business.name} — {self.title}'


class BusinessSubtype(models.Model):
    INTERACTION_TYPE_CHOICES = [
        ('orders',             'Orders (delivery/pickup)'),
        ('bookings',           'Bookings (hotels/apartments)'),
        ('services',           'Service Requests (quote-based)'),
        ('appointments',       'Appointments (fixed time slots)'),
        ('scheduled_services', 'Scheduled Services (provider visits customer)'),
        ('rides',              'Rides (on-demand hailing)'),
        ('transport',          'Transport (scheduled routes & seats)'),
        ('shipments',          'Shipments (package delivery)'),
        ('mixed',              'Mixed'),
    ]
    interaction_type = models.CharField(
        max_length=30,
        choices=INTERACTION_TYPE_CHOICES,
    )
    name   = models.CharField(max_length=100)
    slug   = models.SlugField(unique=True)
    icon   = models.CharField(max_length=10, blank=True)
    description = models.TextField(blank=True)
    is_active   = models.BooleanField(default=True)
    order       = models.IntegerField(default=0)

    class Meta:
        ordering = ['interaction_type', 'order', 'name']
        verbose_name = 'Business Subtype'
        verbose_name_plural = 'Business Subtypes'

    def __str__(self):
        return f"{self.get_interaction_type_display()} → {self.name}"


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
    # In OrderSettings — replace order_type CharField with:
    subtype = models.ForeignKey(
        'BusinessSubtype',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        limit_choices_to={'interaction_type': 'orders'},
        related_name='order_businesses',
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
    # In BookingSettings — replace booking_type CharField with:
    subtype = models.ForeignKey(
        'BusinessSubtype',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        limit_choices_to={'interaction_type': 'bookings'},
        related_name='booking_businesses',
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
    # In ServiceSettings — add:
    subtype = models.ForeignKey(
        'BusinessSubtype',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        limit_choices_to={'interaction_type': 'services'},
        related_name='service_businesses',
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

class AppointmentSettings(TimeStampedModel):
    business = models.OneToOneField(
        Business,
        on_delete=models.CASCADE,
        related_name='appointment_settings',
    )
    subtype = models.ForeignKey(
        'BusinessSubtype',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        limit_choices_to={'interaction_type': 'appointments'},
        related_name='appointment_businesses',
    )
    slot_duration_minutes = models.IntegerField(default=30)
    advance_booking_days  = models.IntegerField(default=30)
    buffer_minutes        = models.IntegerField(default=0)
    max_concurrent        = models.IntegerField(default=1)
    requires_deposit      = models.BooleanField(default=False)
    deposit_amount        = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    cancellation_hours    = models.IntegerField(default=2)
    

    def __str__(self):
        return f"Appointment Settings — {self.business.name}"

class RideSettings(TimeStampedModel):
    """
    Settings for businesses that offer rides or transport.
    Covers: taxi, ride-hailing, bus, ferry, airline, shuttle.
    """
    RIDE_TYPE_CHOICES = (
        ('ride_hailing',  'Ride Hailing (Uber-style)'),
        ('bus',           'Bus / Coach'),
        ('minibus',       'Minibus / Sprinter'),
        ('ferry',         'Ferry / Boat'),
        ('airline',       'Airline'),
        ('train',         'Train'),
        ('shuttle',       'Shuttle Service'),
        ('charter',       'Charter / Hire'),
    )

    business = models.OneToOneField(
        Business,
        on_delete=models.CASCADE,
        related_name='ride_settings',
    )
    subtype = models.ForeignKey(
        'BusinessSubtype',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        limit_choices_to={'interaction_type': 'rides'},
        related_name='ride_businesses',
    )
    ride_type = models.CharField(
        max_length=20,
        choices=RIDE_TYPE_CHOICES,
        default='ride_hailing',
    )
    # Fleet info
    fleet_size = models.IntegerField(
        default=1,
        help_text='Number of vehicles in fleet'
    )
    # Operating area
    operating_cities = models.JSONField(
        default=list, blank=True,
        help_text='Cities where service is available'
    )
    operating_radius_km = models.DecimalField(
        max_digits=8, decimal_places=2,
        null=True, blank=True,
        help_text='Radius for ride-hailing'
    )
    # Booking
    allows_advance_booking = models.BooleanField(default=True)
    advance_booking_days   = models.IntegerField(default=30)
    min_advance_hours      = models.IntegerField(default=1)
    allows_instant_booking = models.BooleanField(default=True)
    # Pricing
    base_fare = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    per_km_rate = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    # Cancellation
    free_cancellation_minutes = models.IntegerField(
        default=10,
        help_text='Minutes after booking that cancellation is free'
    )
    cancellation_fee = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    # Payments
    accepts_cash    = models.BooleanField(default=True)
    accepts_card    = models.BooleanField(default=True)
    accepts_wallet  = models.BooleanField(default=True)
    accepts_transfer = models.BooleanField(default=False)
    # Features
    has_ac          = models.BooleanField(default=False)
    has_wifi        = models.BooleanField(default=False)
    allows_luggage  = models.BooleanField(default=True)
    max_luggage_kg  = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True
    )
    luggage_fee_per_kg = models.DecimalField(
        max_digits=8, decimal_places=2, default=0
    )
    # Safety
    has_tracking    = models.BooleanField(default=False)
    is_insured      = models.BooleanField(default=False)
    requires_driver_kyc = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = 'Ride Settings'

    def __str__(self):
        return f"Ride Settings — {self.business.name}"


class ShipmentSettings(TimeStampedModel):
    """
    Settings for logistics businesses on the marketplace.
    e.g. DHL, GIG Logistics, Kevwe Logistics
    """
    SHIPMENT_TYPE_CHOICES = (
        ('local',        'Local (same city)'),
        ('interstate',   'Interstate'),
        ('international','International'),
        ('all',          'All'),
    )

    business = models.OneToOneField(
        Business,
        on_delete=models.CASCADE,
        related_name='shipment_settings',
    )
    subtype = models.ForeignKey(
        'BusinessSubtype',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        limit_choices_to={'interaction_type': 'scheduled_services'},
        related_name='shipment_businesses',
    )
    shipment_type = models.CharField(
        max_length=20,
        choices=SHIPMENT_TYPE_CHOICES,
        default='local',
    )
    # Coverage
    operating_cities = models.JSONField(
        default=list, blank=True,
        help_text='Cities covered'
    )
    operating_states = models.JSONField(
        default=list, blank=True,
        help_text='States covered'
    )
    # Pricing
    base_fee = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    per_kg_rate = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    per_km_rate = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    express_multiplier = models.DecimalField(
        max_digits=4, decimal_places=2, default=1.5,
        help_text='Express delivery price multiplier'
    )
    # Pickup
    offers_pickup = models.BooleanField(default=True)
    pickup_fee = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    # Insurance
    offers_insurance = models.BooleanField(default=False)
    insurance_rate_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=1.0,
        help_text='% of declared value charged as insurance fee'
    )
    # Limits
    max_weight_kg = models.DecimalField(
        max_digits=8, decimal_places=2, default=50
    )
    max_length_cm = models.DecimalField(
        max_digits=8, decimal_places=2,
        null=True, blank=True
    )
    max_width_cm = models.DecimalField(
        max_digits=8, decimal_places=2,
        null=True, blank=True
    )
    max_height_cm = models.DecimalField(
        max_digits=8, decimal_places=2,
        null=True, blank=True
    )
    # Delivery time
    standard_days = models.IntegerField(
        default=3, help_text='Standard delivery days'
    )
    express_days = models.IntegerField(
        default=1, help_text='Express delivery days'
    )
    # Payments
    accepts_cash_on_delivery = models.BooleanField(default=False)
    accepts_card   = models.BooleanField(default=True)
    accepts_wallet = models.BooleanField(default=True)
    # Proof of delivery
    requires_signature = models.BooleanField(default=False)
    requires_photo     = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = 'Shipment Settings'

    def __str__(self):
        return f"Shipment Settings — {self.business.name}"




class InteractionForm(TimeStampedModel):
    """Which dedicated page handles a business's workflow for a
    given interaction type, plus the field contract that page must
    satisfy — used for server-side validation, not rendering.
    Hotels get hotel-booking.html; car rentals get
    rental-booking.html; both create a Booking through the same
    engine underneath."""

    interaction_type = models.CharField(max_length=32, choices=Industry.INTERACTION_TYPE_CHOICES)

    industry = models.ForeignKey(Industry, on_delete=models.CASCADE, null=True, blank=True,
        related_name='interaction_forms')
    category = models.ForeignKey(BusinessCategory, on_delete=models.CASCADE, null=True, blank=True,
        related_name='interaction_forms')
    business = models.ForeignKey('Business', on_delete=models.CASCADE, null=True, blank=True,
        related_name='interaction_forms')

    form_key = models.SlugField(max_length=60, unique=True,
        help_text='hotel_booking, rental_booking, salon_appointment...')
    name = models.CharField(max_length=100)

    # The page the business page's CTA routes to for this workflow.
    page_url = models.CharField(max_length=200,
        help_text='e.g. hotel-booking.html, rental-booking.html')

    # Field contract — validation only. The dedicated page's own
    # markup is the actual UI; this just tells the backend what
    # a valid submission looks like.
    schema = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['interaction_type', 'form_key']

    def clean(self):
        from django.core.exceptions import ValidationError
        scopes = [bool(self.industry_id), bool(self.category_id), bool(self.business_id)]
        if sum(scopes) != 1:
            raise ValidationError('Set exactly one of industry, category or business.')

    @classmethod
    def resolve(cls, interaction_type, business):
        """Same precedence as InteractionVocabulary — business wins,
        then category, then industry."""
        rows = list(cls.objects.filter(interaction_type=interaction_type).filter(
            models.Q(business_id=business.id)
            | models.Q(category_id=business.category_id)
            | models.Q(industry_id=business.industry_id)
        ))
        for r in rows:
            if r.business_id == business.id: return r
        for r in rows:
            if r.category_id and r.category_id == business.category_id: return r
        for r in rows:
            if r.industry_id and r.industry_id == business.industry_id: return r
        return None
