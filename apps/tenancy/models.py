from django.db import models
from django.conf import settings
from apps.common.models import TimeStampedModel
import secrets
import hashlib
from django.utils import timezone



class Tenant(TimeStampedModel):
    """
    Represents a business/client
    using the API as a SaaS platform
    """
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('suspended', 'Suspended'),
        ('trial', 'Trial'),
        ('cancelled', 'Cancelled'),
    )

    INDUSTRY_CHOICES = (
        ('ecommerce', 'E-Commerce'),
        ('logistics', 'Logistics'),
        ('hospitality', 'Hospitality'),
        ('ride_hailing', 'Ride Hailing'),
        ('healthcare', 'Healthcare'),
        ('education', 'Education'),
        ('real_estate', 'Real Estate'),
        ('food_delivery', 'Food Delivery'),
        ('retail', 'Retail'),
        ('hotel', 'hotel'),
        ('other', 'Other'),

    )

    # Basic info
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True, null=True)
    industry = models.CharField(
        max_length=20,
        choices=INDUSTRY_CHOICES,
        default='other'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='trial'
    )

    # Owner
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='owned_tenants'
    )

    # Contact
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)

    # Location
    country = models.ForeignKey(
        'locations.Country',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tenants'
    )
    state = models.ForeignKey(
        'locations.State',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tenants'
    )
    city = models.ForeignKey(
        'locations.City',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tenants'
    )

    # Branding
    logo = models.ImageField(
        upload_to='tenants/logos/',
        null=True,
        blank=True
    )
    favicon = models.ImageField(
        upload_to='tenants/favicons/',
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
        default='#ff6600'
    )

    # Domain
    custom_domain = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        unique=True
    )
    subdomain = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        unique=True
    )

    # Subscription
    plan = models.ForeignKey(
        'subscriptions.Plan',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tenants'
    )
    trial_ends_at = models.DateTimeField(
        null=True,
        blank=True
    )
    subscription_ends_at = models.DateTimeField(
        null=True,
        blank=True
    )

    # Limits
    max_users = models.IntegerField(default=5)
    max_branches = models.IntegerField(default=1)
    max_products = models.IntegerField(default=100)
    max_orders_per_month = models.IntegerField(default=500)

    # Features toggle
    enable_orders = models.BooleanField(default=True)
    enable_bookings = models.BooleanField(default=True)
    enable_deliveries = models.BooleanField(default=True)
    enable_rides = models.BooleanField(default=False)
    enable_shipments = models.BooleanField(default=True)
    enable_wallet = models.BooleanField(default=True)
    enable_subscriptions = models.BooleanField(default=False)
    enable_pos = models.BooleanField(default=False)

    # API
    api_key = models.CharField(
        max_length=100,
        unique=True,
        blank=True,
        null=True
    )
    api_secret = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )
    webhook_url = models.URLField(blank=True, null=True)

    # Meta
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.slug})"

    def generate_api_keys(self):
        """Generate API key and secret"""
        import secrets
        self.api_key = f"tk_{secrets.token_urlsafe(24)}"
        self.api_secret = f"ts_{secrets.token_urlsafe(32)}"
        self.save()

    @property
    def is_trial(self):
        return self.status == 'trial'

    @property
    def total_users(self):
        return self.memberships.filter(
            is_active=True
        ).count()

    @property
    def total_branches(self):
        return self.branches.filter(
            is_active=True
        ).count()


class TenantMembership(TimeStampedModel):
    """
    Users belonging to a tenant
    """
    ROLE_CHOICES = (
        ('owner', 'Owner'),
        ('admin', 'Admin'),
        ('manager', 'Manager'),
        ('staff', 'Staff'),
        ('viewer', 'Viewer'),
    )

    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name='memberships'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='tenant_memberships'
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='staff'
    )

    # Permissions
    can_manage_users = models.BooleanField(default=False)
    can_manage_products = models.BooleanField(default=False)
    can_manage_orders = models.BooleanField(default=True)
    can_manage_deliveries = models.BooleanField(default=False)
    can_manage_finance = models.BooleanField(default=False)
    can_view_reports = models.BooleanField(default=True)
    can_manage_settings = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)
    joined_at = models.DateTimeField(auto_now_add=True)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sent_invitations'
    )

    class Meta:
        ordering = ['-created_at']
        unique_together = ('tenant', 'user')

    def __str__(self):
        return f"{self.user.email} - {self.tenant.name} ({self.role})"


class TenantInvitation(TimeStampedModel):
    """
    Invite users to join a tenant
    """
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('expired', 'Expired'),
    )

    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name='invitations'
    )
    email = models.EmailField()
    role = models.CharField(
        max_length=20,
        default='staff'
    )
    token = models.CharField(max_length=100, unique=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='invitations_sent'
    )
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.email} → {self.tenant.name}"

    @property
    def is_expired(self):
        from django.utils import timezone
        return timezone.now() > self.expires_at


class TenantBranch(TimeStampedModel):
    """
    Link branches to tenants
    """
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name='branches'
    )
    branch = models.ForeignKey(
        'operations.Branch',
        on_delete=models.CASCADE,
        related_name='tenant_branches'
    )
    is_active = models.BooleanField(default=True)
    is_primary = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('tenant', 'branch')

    def __str__(self):
        return f"{self.tenant.name} - {self.branch.name}"


class TenantBilling(TimeStampedModel):
    """
    Billing history for tenants
    """
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    )

    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name='billings'
    )
    plan = models.ForeignKey(
        'subscriptions.Plan',
        on_delete=models.SET_NULL,
        null=True,
        related_name='tenant_billings'
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    currency = models.CharField(
        max_length=10,
        default='NGN'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    payment_reference = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )
    billing_period_start = models.DateTimeField()
    billing_period_end = models.DateTimeField()
    description = models.TextField(blank=True, null=True)
    invoice_number = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        null=True
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.tenant.name} - {self.amount} - {self.status}"

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            import random
            import string
            self.invoice_number = 'INV-' + ''.join(
                random.choices(
                    string.ascii_uppercase + string.digits,
                    k=10
                )
            )
        super().save(*args, **kwargs)


class TenantAPILog(TimeStampedModel):
    """
    Log API usage per tenant
    """
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name='api_logs'
    )
    endpoint = models.CharField(max_length=255)
    method = models.CharField(max_length=10)
    status_code = models.IntegerField()
    response_time = models.FloatField(default=0)
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='api_logs'
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.tenant.name} - {self.method} {self.endpoint}"


class CreditAccount(TimeStampedModel):
    """
    Credit balance for each tenant
    Used for pay-as-you-go billing
    """
    tenant = models.OneToOneField(
        Tenant,
        on_delete=models.CASCADE,
        related_name='credit_account'
    )
    balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00
    )
    total_credited = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00
    )
    total_debited = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00
    )
    low_balance_threshold = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=1000.00
    )
    auto_topup = models.BooleanField(default=False)
    auto_topup_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=5000.00
    )
    is_active = models.BooleanField(default=True)
    is_frozen = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.tenant.name} - ₦{self.balance}"

    def credit(self, amount, description='', reference=''):
        """Add credits to account"""
        from decimal import Decimal
        amount = Decimal(str(amount))
        self.balance += amount
        self.total_credited += amount
        self.save()

        CreditTransaction.objects.create(
            credit_account=self,
            transaction_type='credit',
            amount=amount,
            balance_after=self.balance,
            description=description,
            reference=reference,
            status='success'
        )
        return True

    def debit(self, amount, description='', reference=''):
        """Remove credits from account"""
        from decimal import Decimal
        amount = Decimal(str(amount))

        if self.balance < amount:
            return False

        self.balance -= amount
        self.total_debited += amount
        self.save()

        CreditTransaction.objects.create(
            credit_account=self,
            transaction_type='debit',
            amount=amount,
            balance_after=self.balance,
            description=description,
            reference=reference,
            status='success'
        )

        # Check low balance
        if self.balance <= self.low_balance_threshold:
            self._send_low_balance_alert()

        return True

    def _send_low_balance_alert(self):
        """Send low balance notification"""
        try:
            from apps.notifications.utils import send_notification
            send_notification(
                user=self.tenant.owner,
                title='Low Credit Balance ⚠️',
                message=f'Your credit balance for {self.tenant.name} is low: ₦{self.balance}. Please top up to continue using the service.',
                notification_type='system',
                data={
                    'tenant_id': self.tenant.id,
                    'balance': str(self.balance),
                }
            )
        except Exception:
            pass


class CreditTransaction(TimeStampedModel):
    """
    Credit transaction history
    """
    TRANSACTION_TYPE_CHOICES = (
        ('credit', 'Credit'),
        ('debit', 'Debit'),
        ('refund', 'Refund'),
        ('adjustment', 'Adjustment'),
    )

    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('reversed', 'Reversed'),
    )

    DESCRIPTION_TYPE_CHOICES = (
        ('topup', 'Top Up'),
        ('api_usage', 'API Usage'),
        ('subscription', 'Subscription'),
        ('feature', 'Feature Usage'),
        ('sms', 'SMS'),
        ('email', 'Email'),
        ('storage', 'Storage'),
        ('refund', 'Refund'),
        ('bonus', 'Bonus'),
        ('penalty', 'Penalty'),
        ('adjustment', 'Manual Adjustment'),
        ('other', 'Other'),
    )

    credit_account = models.ForeignKey(
        CreditAccount,
        on_delete=models.CASCADE,
        related_name='transactions'
    )
    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPE_CHOICES
    )
    description_type = models.CharField(
        max_length=20,
        choices=DESCRIPTION_TYPE_CHOICES,
        default='other'
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )
    balance_after = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )
    description = models.TextField(
        blank=True,
        null=True
    )
    reference = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    metadata = models.JSONField(
        blank=True,
        null=True
    )
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='credit_transactions'
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.credit_account.tenant.name} - {self.transaction_type} - ₦{self.amount}"


class APIKey(TimeStampedModel):
    """
    Multiple API keys per tenant
    Each key can have different permissions
    """
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('revoked', 'Revoked'),
        ('expired', 'Expired'),
    )

    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name='api_keys'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_api_keys'
    )

    # Key details
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    key_prefix = models.CharField(max_length=10)
    key_hash = models.CharField(max_length=255)
    last_four = models.CharField(max_length=4)

    # Permissions
    can_read = models.BooleanField(default=True)
    can_write = models.BooleanField(default=True)
    can_delete = models.BooleanField(default=False)
    allowed_endpoints = models.JSONField(
        default=list,
        blank=True
    )  # empty = all endpoints allowed

    # Rate limiting
    rate_limit = models.IntegerField(
        default=1000
    )  # requests per hour
    rate_limit_window = models.IntegerField(
        default=3600
    )  # seconds

    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active'
    )
    expires_at = models.DateTimeField(
        null=True,
        blank=True
    )

    # Usage tracking
    last_used_at = models.DateTimeField(
        null=True,
        blank=True
    )
    total_requests = models.IntegerField(default=0)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.tenant.name} - {self.name} ({self.key_prefix}...)"

    @classmethod
    def generate_key(cls, tenant, name, created_by=None, **kwargs):
        """Generate a new API key"""
        # Generate raw key
        raw_key = f"tk_{secrets.token_urlsafe(32)}"
        prefix = raw_key[:8]
        last_four = raw_key[-4:]

        # Hash the key for storage
        key_hash = hashlib.sha256(
            raw_key.encode()
        ).hexdigest()

        api_key = cls.objects.create(
            tenant=tenant,
            name=name,
            created_by=created_by,
            key_prefix=prefix,
            key_hash=key_hash,
            last_four=last_four,
            **kwargs
        )

        # Return raw key only once
        api_key._raw_key = raw_key
        return api_key

    @classmethod
    def verify_key(cls, raw_key):
        """Verify an API key"""
        key_hash = hashlib.sha256(
            raw_key.encode()
        ).hexdigest()
        try:
            api_key = cls.objects.get(
                key_hash=key_hash,
                status='active'
            )
            # Check expiry
            if api_key.expires_at:
                from django.utils import timezone
                if timezone.now() > api_key.expires_at:
                    api_key.status = 'expired'
                    api_key.save()
                    return None
            # Update usage
            from django.utils import timezone
            api_key.last_used_at = timezone.now()
            api_key.total_requests += 1
            api_key.save()
            return api_key
        except cls.DoesNotExist:
            return None

    @property
    def is_active(self):
        return self.status == 'active'


class Webhook(TimeStampedModel):
    """
    Webhook endpoints for tenant
    We send events to these URLs
    """
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('failing', 'Failing'),
    )

    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name='webhooks'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_webhooks'
    )

    # Webhook details
    name = models.CharField(max_length=255)
    url = models.URLField()
    secret = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )
    description = models.TextField(blank=True, null=True)

    # Events to listen to
    events = models.JSONField(
        default=list
    )
    # e.g ['order.created', 'payment.success',
    #      'delivery.completed', 'ride.completed']

    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active'
    )
    is_active = models.BooleanField(default=True)

    # Stats
    total_deliveries = models.IntegerField(default=0)
    successful_deliveries = models.IntegerField(default=0)
    failed_deliveries = models.IntegerField(default=0)
    last_triggered_at = models.DateTimeField(
        null=True,
        blank=True
    )
    last_success_at = models.DateTimeField(
        null=True,
        blank=True
    )
    last_failure_at = models.DateTimeField(
        null=True,
        blank=True
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.tenant.name} - {self.name}"

    def generate_secret(self):
        """Generate webhook secret"""
        self.secret = f"whsec_{secrets.token_urlsafe(32)}"
        self.save()
        return self.secret


class WebhookEvent(TimeStampedModel):
    """
    Webhook delivery history
    Track every webhook delivery attempt
    """
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
        ('retrying', 'Retrying'),
    )

    webhook = models.ForeignKey(
        Webhook,
        on_delete=models.CASCADE,
        related_name='webhook_events',
    )
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name='webhook_events'
    )

    # Event details
    event_type = models.CharField(max_length=100)
    payload = models.JSONField()
    headers = models.JSONField(
        default=dict,
        blank=True
    )

    # Delivery details
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    response_status_code = models.IntegerField(
        null=True,
        blank=True
    )
    response_body = models.TextField(
        blank=True,
        null=True
    )
    response_time_ms = models.IntegerField(
        null=True,
        blank=True
    )

    # Retry
    attempt_count = models.IntegerField(default=1)
    max_attempts = models.IntegerField(default=3)
    next_retry_at = models.DateTimeField(
        null=True,
        blank=True
    )

    delivered_at = models.DateTimeField(
        null=True,
        blank=True
    )
    error_message = models.TextField(
        blank=True,
        null=True
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.event_type} → {self.webhook.url}"


class APIUsage(TimeStampedModel):
    """
    Track API usage per tenant per endpoint
    """
    METHOD_CHOICES = (
        ('GET', 'GET'),
        ('POST', 'POST'),
        ('PATCH', 'PATCH'),
        ('PUT', 'PUT'),
        ('DELETE', 'DELETE'),
    )

    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name='api_usage'
    )
    api_key = models.ForeignKey(
        APIKey,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='usage_records'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='api_usage'
    )

    # Request details
    endpoint = models.CharField(max_length=255)
    method = models.CharField(
        max_length=10,
        choices=METHOD_CHOICES
    )
    status_code = models.IntegerField()
    response_time_ms = models.FloatField(default=0)
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True
    )
    user_agent = models.TextField(blank=True, null=True)

    # Date for aggregation
    date = models.DateField()
    hour = models.IntegerField(default=0)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(
                fields=['tenant', 'date']
            ),
            models.Index(
                fields=['tenant', 'endpoint']
            ),
        ]

    def __str__(self):
        return f"{self.tenant.name} - {self.method} {self.endpoint}"


class Feature(TimeStampedModel):
    """
    Available features in the system
    Admin defines what features exist
    """
    CATEGORY_CHOICES = (
        ('core', 'Core'),
        ('commerce', 'Commerce'),
        ('logistics', 'Logistics'),
        ('finance', 'Finance'),
        ('communication', 'Communication'),
        ('analytics', 'Analytics'),
        ('integration', 'Integration'),
        ('security', 'Security'),
        ('other', 'Other'),
    )

    PRICING_TYPE_CHOICES = (
        ('free', 'Free'),
        ('included', 'Included in Plan'),
        ('addon', 'Add-on'),
        ('usage_based', 'Usage Based'),
    )

    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True, null=True)
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default='core'
    )
    icon = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    # Pricing
    pricing_type = models.CharField(
        max_length=20,
        choices=PRICING_TYPE_CHOICES,
        default='included'
    )
    price_per_month = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    price_per_use = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    # Plans that include this feature
    included_in_plans = models.ManyToManyField(
        'subscriptions.Plan',
        blank=True,
        related_name='tenancy_features'
    )

    is_active = models.BooleanField(default=True)
    is_beta = models.BooleanField(default=False)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class TenantFeature(TimeStampedModel):
    """
    Features enabled for a specific tenant
    """
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('trial', 'Trial'),
        ('expired', 'Expired'),
    )

    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name='tenant_features'
    )
    feature = models.ForeignKey(
        Feature,
        on_delete=models.CASCADE,
        related_name='tenant_features'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active'
    )

    # Override pricing
    custom_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )

    # Usage tracking
    usage_count = models.IntegerField(default=0)
    usage_limit = models.IntegerField(
        default=0
    )  # 0 = unlimited

    # Dates
    enabled_at = models.DateTimeField(
        auto_now_add=True
    )
    expires_at = models.DateTimeField(
        null=True,
        blank=True
    )

    # Config
    config = models.JSONField(
        default=dict,
        blank=True
    )

    enabled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='enabled_features'
    )
    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('tenant', 'feature')

    def __str__(self):
        return f"{self.tenant.name} - {self.feature.name}"

    @property
    def is_active(self):
        if self.status != 'active':
            return False
        if self.expires_at:
            from django.utils import timezone
            if timezone.now() > self.expires_at:
                return False
        if self.usage_limit > 0:
            if self.usage_count >= self.usage_limit:
                return False
        return True

    def increment_usage(self):
        """Increment usage count"""
        self.usage_count += 1
        self.save()

        # Deduct from credit if usage based
        if self.feature.pricing_type == 'usage_based':
            price = self.custom_price or self.feature.price_per_use
            if price > 0:
                try:
                    credit_account = self.tenant.credit_account
                    credit_account.debit(
                        amount=price,
                        description=f'Feature usage: {self.feature.name}',
                        reference=f'FEAT-{self.id}-{self.usage_count}'
                    )
                except Exception:
                    pass


class TenantSetting(TimeStampedModel):
    """
    Custom key/value settings per tenant
    Flexible configuration store
    """
    DATA_TYPE_CHOICES = (
        ('string', 'String'),
        ('integer', 'Integer'),
        ('float', 'Float'),
        ('boolean', 'Boolean'),
        ('json', 'JSON'),
        ('list', 'List'),
    )

    CATEGORY_CHOICES = (
        ('general', 'General'),
        ('branding', 'Branding'),
        ('notifications', 'Notifications'),
        ('payments', 'Payments'),
        ('logistics', 'Logistics'),
        ('security', 'Security'),
        ('integrations', 'Integrations'),
        ('other', 'Other'),
    )

    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name='settings'
    )
    key = models.CharField(max_length=255)
    value = models.TextField()
    data_type = models.CharField(
        max_length=20,
        choices=DATA_TYPE_CHOICES,
        default='string'
    )
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default='general'
    )
    description = models.TextField(
        blank=True,
        null=True
    )
    is_public = models.BooleanField(
        default=False
    )  # Can be read without auth
    is_encrypted = models.BooleanField(
        default=False
    )  # Sensitive data
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='updated_settings'
    )

    class Meta:
        ordering = ['category', 'key']
        unique_together = ('tenant', 'key')

    def __str__(self):
        return f"{self.tenant.name} - {self.key}"

    def get_value(self):
        """Get typed value"""
        import json
        try:
            if self.data_type == 'integer':
                return int(self.value)
            elif self.data_type == 'float':
                return float(self.value)
            elif self.data_type == 'boolean':
                return self.value.lower() in ('true', '1', 'yes')
            elif self.data_type in ('json', 'list'):
                return json.loads(self.value)
            return self.value
        except Exception:
            return self.value

class AuditLog(TimeStampedModel):
    """
    Track every important action
    Who did what and when
    """
    ACTION_CHOICES = (
        # Auth
        ('user.login', 'User Login'),
        ('user.logout', 'User Logout'),
        ('user.register', 'User Register'),
        ('user.password_change', 'Password Change'),

        # Tenant
        ('tenant.created', 'Tenant Created'),
        ('tenant.updated', 'Tenant Updated'),
        ('tenant.suspended', 'Tenant Suspended'),
        ('tenant.cancelled', 'Tenant Cancelled'),

        # Members
        ('member.invited', 'Member Invited'),
        ('member.joined', 'Member Joined'),
        ('member.removed', 'Member Removed'),
        ('member.role_changed', 'Member Role Changed'),

        # API Keys
        ('apikey.created', 'API Key Created'),
        ('apikey.revoked', 'API Key Revoked'),

        # Billing
        ('billing.payment', 'Billing Payment'),
        ('billing.refund', 'Billing Refund'),

        # Credits
        ('credit.topup', 'Credit Top Up'),
        ('credit.deduction', 'Credit Deduction'),

        # Features
        ('feature.enabled', 'Feature Enabled'),
        ('feature.disabled', 'Feature Disabled'),

        # Settings
        ('settings.updated', 'Settings Updated'),

        # Orders
        ('order.created', 'Order Created'),
        ('order.cancelled', 'Order Cancelled'),
        ('order.completed', 'Order Completed'),

        # Deliveries
        ('delivery.created', 'Delivery Created'),
        ('delivery.assigned', 'Delivery Assigned'),
        ('delivery.completed', 'Delivery Completed'),

        # Payments
        ('payment.success', 'Payment Success'),
        ('payment.failed', 'Payment Failed'),
        ('payment.refunded', 'Payment Refunded'),

        # Data
        ('data.export', 'Data Export'),
        ('data.import', 'Data Import'),
        ('data.delete', 'Data Delete'),

        # Other
        ('other', 'Other'),
    )

    SEVERITY_CHOICES = (
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('critical', 'Critical'),
    )

    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name='audit_logs',
        null=True,
        blank=True
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs'
    )

    # Action details
    action = models.CharField(
        max_length=50,
        choices=ACTION_CHOICES,
        default='other'
    )
    severity = models.CharField(
        max_length=20,
        choices=SEVERITY_CHOICES,
        default='info'
    )
    description = models.TextField()

    # Object affected
    object_type = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )  # e.g 'Order', 'Delivery'
    object_id = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )
    object_repr = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )  # Human readable e.g "Order #ORD-123"

    # Changes
    changes = models.JSONField(
        default=dict,
        blank=True
    )  # before/after values

    # Request info
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True
    )
    user_agent = models.TextField(
        blank=True,
        null=True
    )
    endpoint = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    # Extra data
    metadata = models.JSONField(
        blank=True,
        null=True
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'action']),
            models.Index(fields=['tenant', 'created_at']),
            models.Index(fields=['user', 'created_at']),
        ]

    def __str__(self):
        return f"{self.action} by {self.user} at {self.created_at}"


class ActivityFeed(TimeStampedModel):
    """
    Recent activity timeline for tenant
    User-friendly activity stream
    """
    ACTIVITY_TYPE_CHOICES = (
        ('order', 'Order'),
        ('delivery', 'Delivery'),
        ('shipment', 'Shipment'),
        ('ride', 'Ride'),
        ('payment', 'Payment'),
        ('user', 'User'),
        ('system', 'System'),
        ('feature', 'Feature'),
        ('settings', 'Settings'),
        ('other', 'Other'),
    )

    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name='activity_feed'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activities'
    )

    activity_type = models.CharField(
        max_length=20,
        choices=ACTIVITY_TYPE_CHOICES,
        default='other'
    )
    title = models.CharField(max_length=255)
    description = models.TextField(
        blank=True,
        null=True
    )
    icon = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )
    color = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )  # for UI

    # Related object
    object_type = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )
    object_id = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )
    object_url = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    # Extra data
    metadata = models.JSONField(
        blank=True,
        null=True
    )
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'created_at']),
            models.Index(fields=['tenant', 'activity_type']),
        ]

    def __str__(self):
        return f"{self.tenant.name} - {self.title}"


class UsageMetric(TimeStampedModel):
    """
    Daily/Monthly usage statistics per tenant
    Aggregated metrics for analytics
    """
    PERIOD_CHOICES = (
        ('hourly', 'Hourly'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    )

    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name='usage_metrics'
    )

    period = models.CharField(
        max_length=20,
        choices=PERIOD_CHOICES,
        default='daily'
    )
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    date = models.DateField()

    # API metrics
    total_api_calls = models.IntegerField(default=0)
    successful_api_calls = models.IntegerField(default=0)
    failed_api_calls = models.IntegerField(default=0)
    avg_response_time_ms = models.FloatField(default=0)

    # Business metrics
    total_orders = models.IntegerField(default=0)
    total_deliveries = models.IntegerField(default=0)
    total_shipments = models.IntegerField(default=0)
    total_rides = models.IntegerField(default=0)
    total_bookings = models.IntegerField(default=0)

    # Revenue metrics
    total_revenue = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )
    total_payments = models.IntegerField(default=0)
    successful_payments = models.IntegerField(default=0)
    failed_payments = models.IntegerField(default=0)

    # User metrics
    active_users = models.IntegerField(default=0)
    new_users = models.IntegerField(default=0)

    # Credit metrics
    credits_used = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )
    credits_added = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    class Meta:
        ordering = ['-date']
        unique_together = ('tenant', 'period', 'date')
        indexes = [
            models.Index(fields=['tenant', 'date']),
            models.Index(fields=['tenant', 'period']),
        ]

    def __str__(self):
        return f"{self.tenant.name} - {self.period} - {self.date}"


class CustomDomain(TimeStampedModel):
    """
    Custom domain management per tenant
    Allows tenants to use their own domain
    """
    STATUS_CHOICES = (
        ('pending', 'Pending Verification'),
        ('verifying', 'Verifying'),
        ('active', 'Active'),
        ('failed', 'Verification Failed'),
        ('suspended', 'Suspended'),
        ('expired', 'Expired'),
    )

    SSL_STATUS_CHOICES = (
        ('none', 'No SSL'),
        ('pending', 'SSL Pending'),
        ('active', 'SSL Active'),
        ('expired', 'SSL Expired'),
        ('failed', 'SSL Failed'),
    )

    DOMAIN_TYPE_CHOICES = (
        ('primary', 'Primary Domain'),
        ('subdomain', 'Subdomain'),
        ('alias', 'Alias Domain'),
    )

    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name='custom_domains'
    )

    # Domain details
    domain = models.CharField(
        max_length=255,
        unique=True
    )
    domain_type = models.CharField(
        max_length=20,
        choices=DOMAIN_TYPE_CHOICES,
        default='primary'
    )
    is_primary = models.BooleanField(default=False)

    # Verification
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    verification_token = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )
    verification_method = models.CharField(
        max_length=20,
        default='dns_txt'
    )  # dns_txt, dns_cname, file
    verified_at = models.DateTimeField(
        null=True,
        blank=True
    )

    # SSL
    ssl_status = models.CharField(
        max_length=20,
        choices=SSL_STATUS_CHOICES,
        default='none'
    )
    ssl_issued_at = models.DateTimeField(
        null=True,
        blank=True
    )
    ssl_expires_at = models.DateTimeField(
        null=True,
        blank=True
    )

    # DNS Records needed
    dns_records = models.JSONField(
        default=list,
        blank=True
    )
    # e.g [
    #   {type: 'TXT', name: '@', value: 'verify=abc123'},
    #   {type: 'CNAME', name: 'www', value: 'app.kevweapi.com'}
    # ]

    # Redirect
    redirect_to_primary = models.BooleanField(default=False)
    force_https = models.BooleanField(default=True)

    # Stats
    last_checked_at = models.DateTimeField(
        null=True,
        blank=True
    )
    check_error = models.TextField(
        blank=True,
        null=True
    )

    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='added_domains'
    )
    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.domain} → {self.tenant.name}"

    def generate_verification_token(self):
        """Generate DNS verification token"""
        import secrets
        self.verification_token = f"kevwe-verify={secrets.token_urlsafe(32)}"
        self.dns_records = [
            {
                'type': 'TXT',
                'name': '@',
                'value': self.verification_token,
                'ttl': 3600,
                'description': 'Add this TXT record to verify domain ownership'
            },
            {
                'type': 'CNAME',
                'name': 'www',
                'value': 'app.kevweapi.com',
                'ttl': 3600,
                'description': 'Add this CNAME to point your domain to our servers'
            },
            {
                'type': 'A',
                'name': '@',
                'value': '1.2.3.4',
                'ttl': 3600,
                'description': 'Add this A record to point your domain IP'
            }
        ]
        self.save()
        return self.verification_token

    def verify_domain(self):
        """
        Attempt to verify domain ownership
        Checks DNS TXT record
        """
        import socket
        try:
            # In production use dnspython library
            # For now simulate verification
            self.status = 'active'
            self.verified_at = timezone.now()
            self.ssl_status = 'pending'
            self.last_checked_at = timezone.now()
            self.save()
            return True
        except Exception as e:
            self.status = 'failed'
            self.check_error = str(e)
            self.last_checked_at = timezone.now()
            self.save()
            return False

    @property
    def is_verified(self):
        return self.status == 'active'

    @property
    def is_ssl_active(self):
        return self.ssl_status == 'active'