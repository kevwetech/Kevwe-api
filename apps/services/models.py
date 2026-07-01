from django.db import models
from django.conf import settings
from apps.common.models import TimeStampedModel


class ServiceCategory(TimeStampedModel):
    """Top-level grouping e.g. Home Services, Auto, Beauty"""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    icon = models.ImageField(
        upload_to='service_category_icons/',
        null=True, blank=True
    )
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']
        verbose_name_plural = 'Service Categories'

    def __str__(self):
        return self.name


class Service(TimeStampedModel):
    """A specific service e.g. Mechanic, Plumber, Electrician"""
    PRICING_TYPE_CHOICES = (
        ('fixed_price', 'Fixed Price'),
        ('inspection_quote', 'Inspection → Quote'),
        ('custom_quote', 'Custom Quote'),
        ('hourly', 'Hourly Rate'),
        ('daily', 'Daily Rate'),
    )
    DISPATCH_TYPE_CHOICES = (
        ('on_demand', 'On-Demand (location-based)'),
        ('scheduled', 'Scheduled (appointment-based)'),
    )

    category = models.ForeignKey(
        ServiceCategory,
        on_delete=models.CASCADE,
        related_name='services'
    )
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    icon = models.ImageField(
        upload_to='service_icons/',
        null=True, blank=True
    )
    default_pricing_type = models.CharField(
        max_length=20,
        choices=PRICING_TYPE_CHOICES,
        default='inspection_quote'
    )
    allowed_pricing_types = models.JSONField(
        default=list,
        help_text='Pricing types providers can choose'
    )
    dispatch_type = models.CharField(
        max_length=20,
        choices=DISPATCH_TYPE_CHOICES,
        default='on_demand'
    )
    inspection_fee_required = models.BooleanField(default=True)
    default_inspection_fee = models.DecimalField(
        max_digits=10, decimal_places=2, default=5000
    )
    commission_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=15.00
    )

    requires_certification = models.BooleanField(
        default=False,
        help_text=(
            'Provider must have at least one verified '
            'certification before auto-verification'
        )
    )
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return f"{self.name} ({self.category.name})"


class ServiceProvider(TimeStampedModel):
    """
    A business or individual offering services.
    ForeignKey (not OneToOne) — one user can have
    multiple provider profiles e.g. Mechanic + Plumber.
    """
    STATUS_CHOICES = (
        ('pending', 'Pending Verification'),
        ('verified', 'Verified'),
        ('suspended', 'Suspended'),
        ('rejected', 'Rejected'),
    )
    PROVIDER_TYPE_CHOICES = (
        ('individual', 'Individual / Freelancer'),
        ('business', 'Registered Business'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='service_provider_profiles'
    )
    business = models.ForeignKey(
        'marketplace.Business',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='service_provider_profiles'
    )
    provider_type = models.CharField(
        max_length=20,
        choices=PROVIDER_TYPE_CHOICES,
        default='individual'
    )
    services = models.ManyToManyField(
        Service,
        related_name='providers',
        blank=True
    )
    business_name = models.CharField(
        max_length=255, blank=True, null=True
    )
    bio = models.TextField(blank=True)
    years_experience = models.IntegerField(default=0)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    # Location
    current_lat = models.DecimalField(
        max_digits=9, decimal_places=6,
        null=True, blank=True
    )
    current_lng = models.DecimalField(
        max_digits=9, decimal_places=6,
        null=True, blank=True
    )
    last_location_update = models.DateTimeField(
        null=True, blank=True
    )
    operating_address = models.TextField(blank=True)
    operating_radius_km = models.DecimalField(
        max_digits=6, decimal_places=2, default=15.00
    )
    is_available = models.BooleanField(default=False)
    is_online = models.BooleanField(default=False)
    is_emergency_available = models.BooleanField(
        default=False,
        help_text='Provider handles emergency requests'
    )

    # Insurance
    insurance_provider = models.CharField(
        max_length=255, blank=True, null=True
    )
    insurance_policy_number = models.CharField(
        max_length=100, blank=True, null=True
    )
    insurance_expires_at = models.DateField(
        null=True, blank=True
    )

    # Stats
    rating = models.DecimalField(
        max_digits=3, decimal_places=2, default=5.00
    )
    total_ratings = models.IntegerField(default=0)
    total_jobs_completed = models.IntegerField(default=0)
    total_earnings = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )

    class Meta:
        ordering = ['-rating', '-total_jobs_completed']

    def __str__(self):
        return (
            f"{self.business_name or self.user.full_name} "
            f"({self.status})"
        )

    @property
    def is_verified(self):
        return self.status == 'verified'


class ServiceProviderAvailability(TimeStampedModel):
    """
    Weekly availability schedule for a provider.
    """
    DAY_CHOICES = (
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
        ('sunday', 'Sunday'),
    )

    provider = models.ForeignKey(
        ServiceProvider,
        on_delete=models.CASCADE,
        related_name='availability_schedule'
    )
    day = models.CharField(max_length=10, choices=DAY_CHOICES)
    is_available = models.BooleanField(default=True)
    is_24_hours = models.BooleanField(default=False)
    opening_time = models.TimeField(null=True, blank=True)
    closing_time = models.TimeField(null=True, blank=True)

    class Meta:
        unique_together = ('provider', 'day')
        ordering = ['day']

    def __str__(self):
        return (
            f"{self.provider.business_name} — "
            f"{self.day}: "
            f"{'24hr' if self.is_24_hours else 'closed' if not self.is_available else f'{self.opening_time}-{self.closing_time}'}"
        )


class ProviderSkill(TimeStampedModel):
    """
    Specific skills/specializations a provider has.
    e.g. Toyota, Honda, BMW for a mechanic.
    """
    provider = models.ForeignKey(
        ServiceProvider,
        on_delete=models.CASCADE,
        related_name='skills'
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_verified = models.BooleanField(default=False)

    class Meta:
        unique_together = ('provider', 'name')
        ordering = ['name']

    def __str__(self):
        return f"{self.provider.business_name} — {self.name}"


class ProviderCertification(TimeStampedModel):
    """
    Professional certifications held by the provider.
    """
    STATUS_CHOICES = (
        ('pending', 'Pending Review'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
        ('expired', 'Expired'),
    )

    provider = models.ForeignKey(
        ServiceProvider,
        on_delete=models.CASCADE,
        related_name='certifications'
    )
    name = models.CharField(
        max_length=255,
        help_text='e.g. NEMSA Certificate, ASE Mechanic'
    )
    issuing_body = models.CharField(
        max_length=255, blank=True
    )
    certificate_number = models.CharField(
        max_length=100, blank=True, null=True
    )
    document = models.FileField(
        upload_to='provider_certifications/'
    )
    issued_at = models.DateField(null=True, blank=True)
    expires_at = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='verified_certifications'
    )
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-issued_at']

    def __str__(self):
        return (
            f"{self.provider.business_name} — "
            f"{self.name} ({self.status})"
        )


class ProviderVehicle(TimeStampedModel):
    """
    Vehicle used by the provider for mobile services.
    """
    provider = models.ForeignKey(
        ServiceProvider,
        on_delete=models.CASCADE,
        related_name='vehicles'
    )
    vehicle_type = models.CharField(max_length=50)
    brand = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    color = models.CharField(max_length=50)
    year = models.IntegerField()
    plate_number = models.CharField(max_length=20)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return (
            f"{self.provider.business_name} — "
            f"{self.color} {self.brand} {self.model} "
            f"({self.plate_number})"
        )


class ServiceRequest(TimeStampedModel):
    """
    Customer's request for a service.
    One request can be dispatched to multiple providers via
    ServiceRequestOffer before one accepts.
    """
    STATUS_CHOICES = (
        ('pending', 'Pending — Searching for Provider'),
        ('offers_sent', 'Offers Sent to Providers'),
        ('accepted', 'Accepted by Provider'),
        ('provider_en_route', 'Provider En Route'),
        ('inspecting', 'Inspecting'),
        ('quote_sent', 'Quote Sent'),
        ('quote_approved', 'Quote Approved'),
        ('quote_rejected', 'Quote Rejected'),
        ('in_progress', 'Job In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('no_provider_found', 'No Provider Found'),
    )
    URGENCY_CHOICES = (
        ('low', 'Low — Can wait'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('emergency', 'Emergency'),
    )

    reference = models.CharField(max_length=100, unique=True)
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='service_requests'
    )
    service = models.ForeignKey(
        Service,
        on_delete=models.SET_NULL,
        null=True,
        related_name='requests'
    )
    provider = models.ForeignKey(
        ServiceProvider,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='requests',
        help_text='Set when a provider accepts the request'
    )

    description = models.TextField()
    urgency = models.CharField(
        max_length=20,
        choices=URGENCY_CHOICES,
        default='medium'
    )
    budget = models.DecimalField(
        max_digits=12, decimal_places=2,
        null=True, blank=True
    )

    # Location
    location_address = models.TextField()
    location_lat = models.DecimalField(
        max_digits=9, decimal_places=6
    )
    location_lng = models.DecimalField(
        max_digits=9, decimal_places=6
    )

    # Scheduled
    scheduled_date = models.DateField(null=True, blank=True)
    scheduled_time = models.TimeField(null=True, blank=True)

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default='pending'
    )

    # Pricing
    pricing_type = models.CharField(
        max_length=20,
        choices=Service.PRICING_TYPE_CHOICES,
        default='inspection_quote'
    )
    inspection_fee = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    inspection_fee_paid = models.BooleanField(default=False)

    # Timestamps
    accepted_at = models.DateTimeField(null=True, blank=True)
    provider_arrived_at = models.DateTimeField(
        null=True, blank=True
    )
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(
        blank=True, null=True
    )

    # Financials
    final_total = models.DecimalField(
        max_digits=12, decimal_places=2,
        null=True, blank=True
    )
    platform_commission = models.DecimalField(
        max_digits=12, decimal_places=2,
        null=True, blank=True
    )
    provider_earnings = models.DecimalField(
        max_digits=12, decimal_places=2,
        null=True, blank=True
    )
    payment_status = models.CharField(
        max_length=20,
        choices=(
            ('unpaid', 'Unpaid'),
            ('inspection_paid', 'Inspection Fee Paid'),
            ('paid', 'Fully Paid'),
            ('refunded', 'Refunded'),
        ),
        default='unpaid'
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return (
            f"ServiceRequest {self.reference} — {self.status}"
        )


class ServiceRequestAttachment(TimeStampedModel):
    """
    Photos/videos attached to a service request.
    Replaces the JSONField photos approach.
    """
    service_request = models.ForeignKey(
        ServiceRequest,
        on_delete=models.CASCADE,
        related_name='attachments'
    )
    file = models.FileField(
        upload_to='service_request_attachments/'
    )
    file_type = models.CharField(
        max_length=10,
        choices=(
            ('image', 'Image'),
            ('video', 'Video'),
            ('document', 'Document'),
        ),
        default='image'
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True
    )
    caption = models.CharField(
        max_length=255, blank=True
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return (
            f"{self.service_request.reference} — "
            f"{self.file_type}"
        )


class ServiceRequestOffer(TimeStampedModel):
    """
    Offer sent to a nearby provider for a service request.
    Tracks which providers were notified, accepted, or declined.
    One request → many offers → first accept wins.
    """
    STATUS_CHOICES = (
        ('pending', 'Pending Response'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled — Another Provider Accepted'),
    )

    service_request = models.ForeignKey(
        ServiceRequest,
        on_delete=models.CASCADE,
        related_name='offers'
    )
    provider = models.ForeignKey(
        ServiceProvider,
        on_delete=models.CASCADE,
        related_name='offers'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    distance_km = models.DecimalField(
        max_digits=6, decimal_places=2,
        null=True, blank=True
    )
    sent_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    decline_reason = models.TextField(blank=True, null=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('service_request', 'provider')
        ordering = ['distance_km', 'sent_at']

    def __str__(self):
        return (
            f"Offer: {self.service_request.reference} → "
            f"{self.provider.business_name} ({self.status})"
        )


class ServiceQuote(TimeStampedModel):
    """
    Quote sent by provider after inspection.
    Supports revision history via parent_quote.
    """
    STATUS_CHOICES = (
        ('pending', 'Pending Customer Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('superseded', 'Superseded by Revision'),
        ('expired', 'Expired'),
    )

    service_request = models.ForeignKey(
        ServiceRequest,
        on_delete=models.CASCADE,
        related_name='quotes'
    )
    parent_quote = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='revisions',
        help_text='Previous quote this revises'
    )
    revision_number = models.PositiveIntegerField(default=1)
    diagnosis = models.TextField(blank=True)
    labour_cost = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )
    parts_cost = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )
    other_costs = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )
    total = models.DecimalField(
        max_digits=12, decimal_places=2
    )
    line_items = models.JSONField(default=list)
    estimated_duration_hours = models.DecimalField(
        max_digits=5, decimal_places=2,
        null=True, blank=True
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    expires_at = models.DateTimeField(null=True, blank=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, null=True)
    revision_note = models.TextField(
        blank=True,
        help_text='Why this revision was submitted'
    )

    class Meta:
        ordering = ['-revision_number', '-created_at']

    def __str__(self):
        return (
            f"Quote v{self.revision_number} for "
            f"{self.service_request.reference} — "
            f"₦{self.total} ({self.status})"
        )


class ServicePart(TimeStampedModel):
    """
    Parts purchased/needed for a job.
    Linked to a quote for accurate costing.
    """
    quote = models.ForeignKey(
        ServiceQuote,
        on_delete=models.CASCADE,
        related_name='parts'
    )
    name = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(
        max_digits=10, decimal_places=2
    )
    total_price = models.DecimalField(
        max_digits=12, decimal_places=2
    )
    supplier = models.CharField(
        max_length=255, blank=True, null=True
    )
    warranty_days = models.IntegerField(
        default=0,
        help_text='Warranty in days (0 = no warranty)'
    )
    part_number = models.CharField(
        max_length=100, blank=True, null=True
    )
    is_genuine = models.BooleanField(
        default=True,
        help_text='Genuine vs. aftermarket part'
    )

    def save(self, *args, **kwargs):
        from decimal import Decimal
        self.total_price = (
            Decimal(str(self.quantity))
            * Decimal(str(self.unit_price))
        )
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} x{self.quantity} — ₦{self.total_price}"


class CompletionEvidence(TimeStampedModel):
    """
    Proof of job completion — before/after photos,
    customer OTP confirmation, signature.
    """
    service_request = models.OneToOneField(
        ServiceRequest,
        on_delete=models.CASCADE,
        related_name='completion_evidence'
    )
    before_photos = models.JSONField(
        default=list,
        help_text='List of before-job photo URLs'
    )
    after_photos = models.JSONField(
        default=list,
        help_text='List of after-job photo URLs'
    )
    completion_otp = models.CharField(
        max_length=6, null=True, blank=True
    )
    otp_verified = models.BooleanField(default=False)
    otp_verified_at = models.DateTimeField(
        null=True, blank=True
    )
    customer_signature = models.ImageField(
        upload_to='completion_signatures/',
        null=True, blank=True
    )
    notes = models.TextField(blank=True)

    def __str__(self):
        return (
            f"Evidence for "
            f"{self.service_request.reference}"
        )


class ServiceRequestTracking(TimeStampedModel):
    """Status change history for a service request."""
    service_request = models.ForeignKey(
        ServiceRequest,
        on_delete=models.CASCADE,
        related_name='tracking'
    )
    status = models.CharField(max_length=30)
    description = models.TextField()
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6,
        null=True, blank=True
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6,
        null=True, blank=True
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True
    )

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return (
            f"{self.service_request.reference} — {self.status}"
        )


class ServiceRating(TimeStampedModel):
    """Two-way rating after job completion."""
    service_request = models.OneToOneField(
        ServiceRequest,
        on_delete=models.CASCADE,
        related_name='detailed_rating'
    )
    customer_rating = models.IntegerField(
        null=True, blank=True
    )
    customer_review = models.TextField(blank=True, null=True)
    provider_rating_of_customer = models.IntegerField(
        null=True, blank=True
    )
    provider_notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return (
            f"Rating for {self.service_request.reference}"
        )