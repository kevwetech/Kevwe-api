from django.db import models
from django.conf import settings
from apps.common.models import TimeStampedModel


class Industry(TimeStampedModel):
    """
    Types of businesses on the platform
    e.g Restaurant, Logistics, Pharmacy, Grocery
    """
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('coming_soon', 'Coming Soon'),
        ('inactive', 'Inactive'),
    )

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True, null=True)
    icon = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )
    image = models.ImageField(
        upload_to='marketplace/industries/',
        null=True,
        blank=True
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active'
    )

    # Commission rates for this industry
    platform_commission = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=10.00
    )  # percentage
    driver_commission = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=20.00
    )  # percentage
    vendor_commission = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=70.00
    )  # percentage

    # Display
    is_featured = models.BooleanField(default=False)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']
        verbose_name_plural = 'Industries'

    def __str__(self):
        return self.name


class Business(TimeStampedModel):
    """
    A vendor/business on the marketplace
    e.g a restaurant, logistics company
    """
    STATUS_CHOICES = (
        ('pending', 'Pending Approval'),
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('rejected', 'Rejected'),
        ('closed', 'Closed'),
    )

    # Owner
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='businesses'
    )

    # Industry
    industry = models.ForeignKey(
        Industry,
        on_delete=models.CASCADE,
        related_name='businesses'
    )

    # Basic info
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True, null=True)
    tagline = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    # Media
    logo = models.ImageField(
        upload_to='marketplace/businesses/logos/',
        null=True,
        blank=True
    )
    cover_image = models.ImageField(
        upload_to='marketplace/businesses/covers/',
        null=True,
        blank=True
    )

    # Contact
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )
    whatsapp = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )
    website = models.URLField(blank=True, null=True)

    # Location
    address = models.TextField()
    country = models.ForeignKey(
        'locations.Country',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='businesses'
    )
    state = models.ForeignKey(
        'locations.State',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='businesses'
    )
    city = models.ForeignKey(
        'locations.City',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='businesses'
    )
    zone = models.ForeignKey(
        'locations.Zone',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='businesses'
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

    # Operations
    opening_time = models.TimeField(
        null=True,
        blank=True
    )
    closing_time = models.TimeField(
        null=True,
        blank=True
    )
    working_days = models.JSONField(
        default=list,
        blank=True
    )
    is_open_now = models.BooleanField(default=True)
    accepts_orders = models.BooleanField(default=True)

    # Delivery settings
    delivery_available = models.BooleanField(default=True)
    pickup_available = models.BooleanField(default=True)
    min_order_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    delivery_time_minutes = models.IntegerField(
        default=30
    )
    delivery_radius_km = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=5.00
    )
    delivery_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    # Commission override
    custom_commission = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    rejection_reason = models.TextField(
        blank=True,
        null=True
    )
    approved_at = models.DateTimeField(
        null=True,
        blank=True
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_businesses'
    )

    # Stats
    total_orders = models.IntegerField(default=0)
    total_revenue = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )
    rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.00
    )
    total_ratings = models.IntegerField(default=0)

    # Features
    is_featured = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    # Metadata
    tags = models.JSONField(default=list, blank=True)
    meta_title = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )
    meta_description = models.TextField(
        blank=True,
        null=True
    )

    class Meta:
        ordering = ['-is_featured', '-rating', '-created_at']
        verbose_name_plural = 'Businesses'

    def __str__(self):
        return f"{self.name} ({self.industry.name})"

    @property
    def commission_rate(self):
        """Get effective commission rate"""
        if self.custom_commission:
            return self.custom_commission
        return self.industry.platform_commission


class BusinessHours(TimeStampedModel):
    """
    Detailed business hours per day
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
        Business,
        on_delete=models.CASCADE,
        related_name='hours'
    )
    day = models.IntegerField(choices=DAY_CHOICES)
    is_open = models.BooleanField(default=True)
    opening_time = models.TimeField()
    closing_time = models.TimeField()

    class Meta:
        ordering = ['day']
        unique_together = ('business', 'day')

    def __str__(self):
        return f"{self.business.name} - {self.get_day_display()}"


class BusinessImage(TimeStampedModel):
    """Additional images for business"""
    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name='images'
    )
    image = models.ImageField(
        upload_to='marketplace/businesses/gallery/'
    )
    caption = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )
    is_primary = models.BooleanField(default=False)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.business.name} image"


class BusinessDocument(TimeStampedModel):
    """
    Business verification documents
    CAC, food license etc
    """
    DOCUMENT_TYPE_CHOICES = (
        ('cac', 'CAC Registration'),
        ('food_license', 'Food License'),
        ('tax_id', 'Tax ID'),
        ('id_card', 'ID Card'),
        ('other', 'Other'),
    )

    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )

    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name='documents'
    )
    document_type = models.CharField(
        max_length=20,
        choices=DOCUMENT_TYPE_CHOICES
    )
    document_file = models.FileField(
        upload_to='marketplace/documents/'
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
        return f"{self.business.name} - {self.document_type}"


class Permission(TimeStampedModel):
    """
    Granular permissions assignable to roles
    Admin can add new permissions anytime from dashboard
    """
    name = models.CharField(max_length=100, unique=True)
    codename = models.CharField(max_length=100, unique=True)  # e.g 'can_manage_menu'
    description = models.TextField(blank=True, null=True)
    category = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )  # e.g 'orders', 'staff', 'reports' — for grouping in dashboard

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['category', 'name']

    def __str__(self):
        return f"{self.category} → {self.name}"


class BusinessRole(TimeStampedModel):
    """
    Dynamic roles for business staff
    """
    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name='roles',
        null=True,
        blank=True,  # null = platform-wide default
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    permissions = models.ManyToManyField(
        Permission,
        blank=True,
        related_name='roles'
    )
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)

    class Meta:
        ordering = ['name']
        unique_together = ('business', 'name')

    def __str__(self):
        return f"{self.name} ({self.business.name if self.business else 'Platform Default'})"

    def has_permission(self, codename):
        return self.permissions.filter(codename=codename, is_active=True).exists()


class BusinessStaff(TimeStampedModel):
    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name='staff'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='business_staff'
    )
    role = models.ForeignKey(
        BusinessRole,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='staff_members'
    )
    status = models.CharField(
        max_length=20,
        choices=(
            ('active', 'Active'),
            ('inactive', 'Inactive'),
            ('suspended', 'Suspended'),
        ),
        default='active'
    )

    # Invitation
    invitation_token      = models.CharField(max_length=100, blank=True, null=True, unique=True)
    invitation_status     = models.CharField(
        max_length=20,
        choices=(
            ('pending', 'Pending'),
            ('accepted', 'Accepted'),
            ('expired', 'Expired'),
            ('revoked', 'Revoked'),
        ),
        default='pending'
    )
    invited_by            = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='sent_staff_invitations'
    )
    invitation_expires_at = models.DateTimeField(null=True, blank=True)
    joined_at             = models.DateTimeField(null=True, blank=True)
    notes                 = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('business', 'user')

    def __str__(self):
        role_name = self.role.name if self.role else 'No Role'
        return f"{self.user.full_name} - {self.business.name} ({role_name})"

    @property
    def is_active(self):
        return self.status == 'active'

    def has_permission(self, codename):
        """Check if staff member has a specific permission via their role"""
        if not self.role:
            return False
        return self.role.has_permission(codename)