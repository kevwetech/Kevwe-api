from django.db import models
from django.conf import settings
from apps.common.models import TimeStampedModel


class SiteSettings(TimeStampedModel):
    """
    Global site settings
    Only one instance should exist
    """
    # Basic info
    site_name = models.CharField(max_length=255, default='Kevwe API')
    site_tagline = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )
    site_description = models.TextField(blank=True, null=True)
    site_email = models.EmailField(blank=True, null=True)
    site_phone = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )
    site_address = models.TextField(blank=True, null=True)
    site_url = models.URLField(blank=True, null=True)

    # Branding
    logo = models.ImageField(
        upload_to='site/logo/',
        null=True,
        blank=True
    )
    favicon = models.ImageField(
        upload_to='site/favicon/',
        null=True,
        blank=True
    )
    primary_color = models.CharField(
        max_length=10,
        default='#000000'
    )
    secondary_color = models.CharField(
        max_length=10,
        default='#ffffff'
    )
    accent_color = models.CharField(
        max_length=10,
        default='#ff0000'
    )

    # Social media
    facebook = models.URLField(blank=True, null=True)
    twitter = models.URLField(blank=True, null=True)
    instagram = models.URLField(blank=True, null=True)
    linkedin = models.URLField(blank=True, null=True)
    youtube = models.URLField(blank=True, null=True)
    whatsapp = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )

    # SEO
    meta_title = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )
    meta_description = models.TextField(blank=True, null=True)
    meta_keywords = models.TextField(blank=True, null=True)

    # Features toggle
    enable_registration = models.BooleanField(default=True)
    enable_orders = models.BooleanField(default=True)
    enable_bookings = models.BooleanField(default=True)
    enable_deliveries = models.BooleanField(default=True)
    enable_rides = models.BooleanField(default=True)
    enable_wallet = models.BooleanField(default=True)
    enable_subscriptions = models.BooleanField(default=True)
    maintenance_mode = models.BooleanField(default=False)
    maintenance_message = models.TextField(blank=True, null=True)

    # Currency
    currency = models.CharField(max_length=10, default='NGN')
    currency_symbol = models.CharField(max_length=5, default='₦')

    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Site Settings'
        verbose_name_plural = 'Site Settings'

    def __str__(self):
        return self.site_name

    @classmethod
    def get_settings(cls):
        """Get or create site settings"""
        settings, created = cls.objects.get_or_create(pk=1)
        return settings


class HomePage(TimeStampedModel):
    """Homepage content"""
    # Hero section
    hero_title = models.CharField(max_length=255)
    hero_subtitle = models.TextField(blank=True, null=True)
    hero_description = models.TextField(blank=True, null=True)
    hero_image = models.ImageField(
        upload_to='cms/hero/',
        null=True,
        blank=True
    )
    hero_video_url = models.URLField(blank=True, null=True)
    hero_cta_text = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )
    hero_cta_url = models.URLField(blank=True, null=True)
    hero_secondary_cta_text = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )
    hero_secondary_cta_url = models.URLField(blank=True, null=True)

    # Stats section
    show_stats = models.BooleanField(default=True)
    stat_1_label = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )
    stat_1_value = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )
    stat_2_label = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )
    stat_2_value = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )
    stat_3_label = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )
    stat_3_value = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )
    stat_4_label = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )
    stat_4_value = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    # Features section
    features_title = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )
    features_subtitle = models.TextField(blank=True, null=True)

    # CTA section
    cta_title = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )
    cta_description = models.TextField(blank=True, null=True)
    cta_button_text = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )
    cta_button_url = models.URLField(blank=True, null=True)

    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Home Page'
        verbose_name_plural = 'Home Page'

    def __str__(self):
        return f"Homepage - {self.hero_title}"


class AboutPage(TimeStampedModel):
    """About page content"""
    # Main section
    title = models.CharField(max_length=255)
    subtitle = models.TextField(blank=True, null=True)
    description = models.TextField()
    image = models.ImageField(
        upload_to='cms/about/',
        null=True,
        blank=True
    )
    video_url = models.URLField(blank=True, null=True)

    # Mission & Vision
    mission_title = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )
    mission_description = models.TextField(blank=True, null=True)
    vision_title = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )
    vision_description = models.TextField(blank=True, null=True)

    # Values
    values_title = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    # Team section
    show_team = models.BooleanField(default=True)
    team_title = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )
    team_subtitle = models.TextField(blank=True, null=True)

    # History
    founded_year = models.IntegerField(null=True, blank=True)
    history = models.TextField(blank=True, null=True)

    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'About Page'
        verbose_name_plural = 'About Page'

    def __str__(self):
        return f"About - {self.title}"


class Service(TimeStampedModel):
    """Services offered"""
    ICON_TYPE_CHOICES = (
        ('emoji', 'Emoji'),
        ('image', 'Image'),
        ('icon_class', 'Icon Class'),
    )

    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    short_description = models.TextField()
    description = models.TextField(blank=True, null=True)

    # Icon/Image
    icon_type = models.CharField(
        max_length=20,
        choices=ICON_TYPE_CHOICES,
        default='emoji'
    )
    icon = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )  # emoji or icon class
    image = models.ImageField(
        upload_to='cms/services/',
        null=True,
        blank=True
    )

    # Pricing display
    show_price = models.BooleanField(default=False)
    starting_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    price_label = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )  # e.g "Starting from"

    # CTA
    cta_text = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )
    cta_url = models.URLField(blank=True, null=True)

    # Display
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'title']

    def __str__(self):
        return self.title


class ContactInfo(TimeStampedModel):
    """Contact page content"""
    title = models.CharField(max_length=255, default='Contact Us')
    subtitle = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    # Contact details
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    alternate_phone = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )
    whatsapp = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )
    address = models.TextField(blank=True, null=True)

    # Location
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
    google_maps_url = models.URLField(blank=True, null=True)

    # Office hours
    office_hours = models.JSONField(
        default=dict,
        blank=True
    )

    # Support
    support_email = models.EmailField(blank=True, null=True)
    support_phone = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )
    support_hours = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Contact Info'
        verbose_name_plural = 'Contact Info'

    def __str__(self):
        return self.title


class ContactMessage(TimeStampedModel):
    """Messages from contact form"""
    STATUS_CHOICES = (
        ('new', 'New'),
        ('read', 'Read'),
        ('replied', 'Replied'),
        ('closed', 'Closed'),
    )

    name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True, null=True)
    subject = models.CharField(max_length=255)
    message = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='new'
    )
    replied_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='replied_messages'
    )
    reply = models.TextField(blank=True, null=True)
    replied_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.subject}"


class FAQ(TimeStampedModel):
    """Frequently Asked Questions"""
    CATEGORY_CHOICES = (
        ('general', 'General'),
        ('orders', 'Orders'),
        ('delivery', 'Delivery'),
        ('payment', 'Payment'),
        ('account', 'Account'),
        ('rides', 'Rides'),
        ('shipment', 'Shipment'),
        ('subscription', 'Subscription'),
        ('other', 'Other'),
    )

    question = models.TextField()
    answer = models.TextField()
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default='general'
    )
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)
    views = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'category']
        verbose_name = 'FAQ'
        verbose_name_plural = 'FAQs'

    def __str__(self):
        return self.question[:100]


class Testimonial(TimeStampedModel):
    """Customer testimonials"""
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )

    # Author
    name = models.CharField(max_length=255)
    title = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )  # e.g "CEO, Company Name"
    company = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )
    avatar = models.ImageField(
        upload_to='cms/testimonials/',
        null=True,
        blank=True
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='testimonials'
    )

    # Content
    content = models.TextField()
    rating = models.IntegerField(default=5)

    # Service reviewed
    service = models.ForeignKey(
        Service,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='testimonials'
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    is_featured = models.BooleanField(default=False)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', '-created_at']

    def __str__(self):
        return f"{self.name} - {self.rating}★"


class TeamMember(TimeStampedModel):
    """Team members for about page"""
    name = models.CharField(max_length=255)
    title = models.CharField(max_length=255)
    bio = models.TextField(blank=True, null=True)
    avatar = models.ImageField(
        upload_to='cms/team/',
        null=True,
        blank=True
    )
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)

    # Social
    linkedin = models.URLField(blank=True, null=True)
    twitter = models.URLField(blank=True, null=True)
    instagram = models.URLField(blank=True, null=True)

    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return f"{self.name} - {self.title}"


class Feature(TimeStampedModel):
    """Features/highlights for homepage"""
    title = models.CharField(max_length=255)
    description = models.TextField()
    icon = models.CharField(max_length=100, blank=True, null=True)
    image = models.ImageField(
        upload_to='cms/features/',
        null=True,
        blank=True
    )
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.title


class Gallery(TimeStampedModel):
    """Image gallery"""
    GALLERY_TYPE_CHOICES = (
        ('general', 'General'),
        ('team', 'Team'),
        ('office', 'Office'),
        ('events', 'Events'),
        ('services', 'Services'),
    )

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='cms/gallery/')
    gallery_type = models.CharField(
        max_length=20,
        choices=GALLERY_TYPE_CHOICES,
        default='general'
    )
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', '-created_at']
        verbose_name_plural = 'Gallery'

    def __str__(self):
        return self.title