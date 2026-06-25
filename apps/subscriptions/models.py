from django.db import models
from django.conf import settings
from apps.common.models import TimeStampedModel


# ─── User/Tenant Plans ────────────────────────────

class Plan(TimeStampedModel):
    BILLING_CYCLE_CHOICES = (
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
        ('lifetime', 'Lifetime'),
    )

    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    billing_cycle = models.CharField(
        max_length=20,
        choices=BILLING_CYCLE_CHOICES,
        default='monthly'
    )
    trial_days = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    max_products = models.IntegerField(default=0)
    max_orders = models.IntegerField(default=0)
    max_users = models.IntegerField(default=1)
    max_storage_gb = models.IntegerField(default=1)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'price']

    def __str__(self):
        return f"{self.name} - ₦{self.price}/{self.billing_cycle}"

    @property
    def is_free(self):
        return self.price == 0


class PlanFeature(TimeStampedModel):
    plan = models.ForeignKey(
        Plan,
        on_delete=models.CASCADE,
        related_name='features'
    )
    feature = models.CharField(max_length=255)
    is_included = models.BooleanField(default=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.plan.name} - {self.feature}"


class Subscription(TimeStampedModel):
    STATUS_CHOICES = (
        ('trial', 'Trial'),
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
        ('past_due', 'Past Due'),
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='subscription'
    )
    plan = models.ForeignKey(
        Plan,
        on_delete=models.CASCADE,
        related_name='subscriptions'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active'
    )
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    trial_end_date = models.DateTimeField(
        null=True, blank=True
    )
    cancelled_at = models.DateTimeField(
        null=True, blank=True
    )
    payment_reference = models.CharField(
        max_length=100, blank=True, null=True
    )
    auto_renew = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} - {self.plan.name}"

    @property
    def is_active(self):
        from django.utils import timezone
        return (
            self.status in ['active', 'trial'] and
            self.end_date > timezone.now()
        )

    @property
    def days_remaining(self):
        from django.utils import timezone
        if self.end_date > timezone.now():
            return (self.end_date - timezone.now()).days
        return 0


class SubscriptionHistory(TimeStampedModel):
    ACTION_CHOICES = (
        ('subscribed', 'Subscribed'),
        ('renewed', 'Renewed'),
        ('upgraded', 'Upgraded'),
        ('downgraded', 'Downgraded'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
        ('trial_started', 'Trial Started'),
        ('trial_ended', 'Trial Ended'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='subscription_history'
    )
    plan = models.ForeignKey(
        Plan,
        on_delete=models.CASCADE,
        related_name='history'
    )
    action = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    payment_reference = models.CharField(
        max_length=100, blank=True, null=True
    )
    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} - {self.action} - {self.plan.name}"


# ─── Business Plans ───────────────────────────────

class BusinessPlan(TimeStampedModel):
    """
    Marketplace subscription plans for businesses
    """
    PLAN_TYPE_CHOICES = (
        ('commission_only', 'Commission Only'),
        ('subscription_only', 'Subscription Only'),
        ('hybrid', 'Hybrid'),
    )

    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True, null=True)
    plan_type = models.CharField(
        max_length=20,
        choices=PLAN_TYPE_CHOICES,
        default='commission_only'
    )

    # Pricing
    monthly_price = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    yearly_price = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )

    # Commission
    commission_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=0
    )
    commission_discount = models.DecimalField(
        max_digits=5, decimal_places=2, default=0
    )

    # Booking permissions
    allows_exclusive_bookings = models.BooleanField(
        default=False
    )
    allows_slot_bookings = models.BooleanField(default=True)
    allows_seat_bookings = models.BooleanField(default=True)

    # Industry restrictions (empty = all industries)
    supported_industries = models.ManyToManyField(
        'marketplace.Industry',
        blank=True,
        related_name='supported_plans'
    )

    # Limits (0 = unlimited)
    max_bookable_items = models.IntegerField(default=5)
    max_monthly_bookings = models.IntegerField(default=0)
    max_monthly_orders = models.IntegerField(default=0)
    max_products = models.IntegerField(default=10)
    max_staff = models.IntegerField(default=2)

    # Grace period after expiry before suspension
    grace_period_days = models.IntegerField(default=3)

    # Trial
    trial_days = models.IntegerField(default=14)

    # Features JSON list
    features = models.JSONField(default=list, blank=True)

    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    is_public = models.BooleanField(default=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'monthly_price']

    def __str__(self):
        return f"{self.name} - ₦{self.monthly_price}/month"

    @property
    def is_free(self):
        return self.monthly_price == 0

    @property
    def yearly_savings(self):
        monthly_total = self.monthly_price * 12
        return monthly_total - self.yearly_price

    def is_available_for_industry(self, industry):
        if not self.supported_industries.exists():
            return True
        return self.supported_industries.filter(
            pk=industry.pk
        ).exists()


class BusinessPlanFeature(TimeStampedModel):
    """Detailed feature list per plan"""
    FEATURE_TYPE_CHOICES = (
        ('included', 'Included'),
        ('excluded', 'Excluded'),
        ('limited', 'Limited'),
        ('addon', 'Available as Add-on'),
    )

    plan = models.ForeignKey(
        BusinessPlan,
        on_delete=models.CASCADE,
        related_name='plan_features'
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    feature_type = models.CharField(
        max_length=10,
        choices=FEATURE_TYPE_CHOICES,
        default='included'
    )
    limit_value = models.CharField(
        max_length=100, blank=True, null=True
    )
    icon = models.CharField(
        max_length=50, blank=True, null=True
    )
    is_highlight = models.BooleanField(default=False)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f"{self.plan.name} - {self.name} ({self.feature_type})"


class BusinessSubscription(TimeStampedModel):
    """Business-level subscription"""
    BILLING_CYCLE_CHOICES = (
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
        ('lifetime', 'Lifetime'),
    )

    STATUS_CHOICES = (
        ('trial', 'Trial'),
        ('active', 'Active'),
        ('grace_period', 'Grace Period'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
        ('past_due', 'Past Due'),
        ('suspended', 'Suspended'),
    )

    business = models.OneToOneField(
        'marketplace.Business',
        on_delete=models.CASCADE,
        related_name='subscription'
    )
    plan = models.ForeignKey(
        BusinessPlan,
        on_delete=models.CASCADE,
        related_name='business_subscriptions'
    )
    billing_cycle = models.CharField(
        max_length=20,
        choices=BILLING_CYCLE_CHOICES,
        default='monthly'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='trial'
    )
    # Custom limit overrides per business (admin set)
    # null = use plan default
    custom_max_products = models.IntegerField(
        null=True, blank=True
    )
    custom_max_staff = models.IntegerField(
        null=True, blank=True
    )
    custom_max_monthly_orders = models.IntegerField(
        null=True, blank=True
    )
    custom_max_monthly_bookings = models.IntegerField(
        null=True, blank=True
    )
    custom_max_bookable_items = models.IntegerField(
        null=True, blank=True
    )

    # Dates
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    trial_end_date = models.DateTimeField(
        null=True, blank=True
    )
    grace_period_end = models.DateTimeField(
        null=True, blank=True
    )
    cancelled_at = models.DateTimeField(
        null=True, blank=True
    )
    next_billing_date = models.DateTimeField(
        null=True, blank=True
    )
    last_renewed_at = models.DateTimeField(
        null=True, blank=True
    )

    # Payment
    amount_paid = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    payment_reference = models.CharField(
        max_length=100, blank=True, null=True
    )
    auto_renew = models.BooleanField(default=True)

    # Commission override
    commission_rate_override = models.DecimalField(
        max_digits=5, decimal_places=2,
        null=True, blank=True
    )

    # Suspension
    suspension_reason = models.TextField(
        blank=True, null=True
    )
    suspended_at = models.DateTimeField(
        null=True, blank=True
    )
    suspended_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='suspended_subscriptions'
    )

    # Usage counters (synced periodically)
    current_products = models.IntegerField(default=0)
    current_staff = models.IntegerField(default=0)
    current_monthly_orders = models.IntegerField(default=0)
    current_monthly_bookings = models.IntegerField(default=0)

    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.business.name} - {self.plan.name}"

    @property
    def is_active(self):
        from django.utils import timezone
        now = timezone.now()
        # Active and trial — check end_date
        if self.status in ['active', 'trial']:
            return self.end_date > now
        # Cancelled — still active until end_date
        if self.status == 'cancelled':
            return self.end_date > now
        # Grace period
        if self.status == 'grace_period':
            return (
                self.grace_period_end and
                self.grace_period_end > now
            )
        return False


    @property
    def is_on_trial(self):
        from django.utils import timezone
        return (
            self.status == 'trial' and
            self.trial_end_date and
            self.trial_end_date > timezone.now()
        )

    @property
    def is_in_grace_period(self):
        from django.utils import timezone
        return (
            self.status == 'grace_period' and
            self.grace_period_end and
            self.grace_period_end > timezone.now()
        )
    @property
    def effective_limits(self):
        """
        Get effective limits considering
        custom overrides and plan defaults
        """
        plan = self.plan
        return {
            'max_products': (
                self.custom_max_products
                if self.custom_max_products is not None
                else plan.max_products
            ),
            'max_staff': (
               self.custom_max_staff
               if self.custom_max_staff is not None
               else plan.max_staff
            ),
            'max_monthly_orders': (
                self.custom_max_monthly_orders
                if self.custom_max_monthly_orders is not None
                else plan.max_monthly_orders
            ),
            'max_monthly_bookings': (
                self.custom_max_monthly_bookings
                if self.custom_max_monthly_bookings is not None
                else plan.max_monthly_bookings
            ),
            'max_bookable_items': (
                self.custom_max_bookable_items
                if self.custom_max_bookable_items is not None
                else plan.max_bookable_items
            ),
        }
        
    @property
    def days_remaining(self):
        from django.utils import timezone
        if self.end_date > timezone.now():
            return (self.end_date - timezone.now()).days
        return 0

    @property
    def grace_days_remaining(self):
        from django.utils import timezone
        if (self.grace_period_end and
                self.grace_period_end > timezone.now()):
            return (
                self.grace_period_end - timezone.now()
            ).days
        return 0

    @property
    def effective_commission_rate(self):
        from decimal import Decimal
        if not self.is_active:
            return None
        if self.commission_rate_override is not None:
            return self.commission_rate_override
        plan = self.plan
        if plan.plan_type == 'subscription_only':
            return Decimal('0')
        elif plan.plan_type == 'hybrid':
           return plan.commission_rate
        elif plan.plan_type == 'commission_only':
           return plan.commission_rate  # ← return plan rate not None
        return None

    def sync_usage_counters(self):
        from django.utils import timezone
        business = self.business
        month_start = timezone.now().replace(
            day=1, hour=0, minute=0,
            second=0, microsecond=0
        )
        self.current_products = business.products.filter(
            is_active=True
        ).count() if hasattr(business, 'products') else 0

        self.current_staff = business.staff.filter(
            status='active'
        ).count() if hasattr(business, 'staff') else 0

        from apps.orders.models import Order
        self.current_monthly_orders = Order.objects.filter(
            business=business,
            created_at__gte=month_start
        ).count()

        from apps.bookings.models import Booking
        self.current_monthly_bookings = Booking.objects.filter(
            business=business,
            created_at__gte=month_start
        ).count()

        self.save()

    def check_limits(self):
        """Check usage against effective limits"""
        self.sync_usage_counters()
        limits   = self.effective_limits
        warnings = []
        exceeded = []

        # Products
        max_products = limits['max_products']
        if max_products > 0:
            if self.current_products >= max_products:
                exceeded.append(
                    f'Product limit reached '
                    f'({self.current_products}/{max_products})'
                )
            elif self.current_products >= max_products * 0.8:
                warnings.append(
                    f'Approaching product limit '
                    f'({self.current_products}/{max_products})'
                )

        # Staff
        max_staff = limits['max_staff']
        if max_staff > 0:
            if self.current_staff >= max_staff:
                exceeded.append(
                    f'Staff limit reached '
                    f'({self.current_staff}/{max_staff})'
                )
            elif self.current_staff >= max_staff * 0.8:
                warnings.append(
                    f'Approaching staff limit '
                    f'({self.current_staff}/{max_staff})'
                )

        # Monthly orders
        max_orders = limits['max_monthly_orders']
        if max_orders > 0:
            if self.current_monthly_orders >= max_orders:
                exceeded.append(
                    f'Monthly order limit reached '
                    f'({self.current_monthly_orders}/{max_orders})'
                )
            elif self.current_monthly_orders >= max_orders * 0.8:
                warnings.append(
                    f'Approaching monthly order limit '
                    f'({self.current_monthly_orders}/{max_orders})'
                )

        # Monthly bookings
        max_bookings = limits['max_monthly_bookings']
        if max_bookings > 0:
            if self.current_monthly_bookings >= max_bookings:
                exceeded.append(
                    f'Monthly booking limit reached '
                    f'({self.current_monthly_bookings}/{max_bookings})'
                )
            elif self.current_monthly_bookings >= max_bookings * 0.8:
                warnings.append(
                    f'Approaching monthly booking limit '
                    f'({self.current_monthly_bookings}/{max_bookings})'
                )

        return {
           'warnings': warnings,
            'exceeded': exceeded,
            'effective_limits': limits,
        }


    def can_accept_bookings(self, booking_mode):
        if not self.is_active:
            if self.status == 'cancelled':
                return False, (
                    'Your subscription has been cancelled '
                    'and has expired.'
                )
            return False, 'No active subscription'

        plan   = self.plan
        limits = self.effective_limits

        if (booking_mode == 'exclusive' and
                not plan.allows_exclusive_bookings):
            return False, (
                f'Your {plan.name} plan does not support '
                f'exclusive bookings. Upgrade to Pro.'
            )

        if (booking_mode == 'slot_based' and
                not plan.allows_slot_bookings):
            return False, (
                f'Your {plan.name} plan does not support '
                f'slot-based bookings.'
            )

        if (booking_mode == 'seat_based' and
                not plan.allows_seat_bookings):
            return False, (
                f'Your {plan.name} plan does not support '
                f'seat-based bookings.'
            )

        max_bookings = limits['max_monthly_bookings']
        if max_bookings > 0:
            if self.current_monthly_bookings >= max_bookings:
                return False, (
                    f'Monthly booking limit reached '
                    f'({self.current_monthly_bookings}/{max_bookings}). '
                    f'Upgrade your plan for more bookings.'
                )

        return True, 'Allowed'

    def enter_grace_period(self):
        from django.utils import timezone
        from datetime import timedelta

        self.status = 'grace_period'
        self.grace_period_end = timezone.now() + timedelta(
            days=self.plan.grace_period_days
        )
        self.save()

        from apps.notifications.utils import send_notification
        send_notification(
            user=self.business.owner,
            title='Subscription Expired ⚠️',
            message=(
                f'Your {self.plan.name} subscription has expired. '
                f'You have {self.plan.grace_period_days} days '
                f'grace period. Renew now to avoid suspension.'
            ),
            notification_type='system',
        )

    def suspend(self, admin_user, reason=''):
        from django.utils import timezone

        self.status = 'suspended'
        self.suspension_reason = reason
        self.suspended_at = timezone.now()
        self.suspended_by = admin_user
        self.save()

        from apps.notifications.utils import send_notification
        send_notification(
            user=self.business.owner,
            title='Account Suspended 🚫',
            message=(
                f'Your {self.plan.name} subscription has been '
                f'suspended. Reason: {reason}. '
                f'Contact support to reactivate.'
            ),
            notification_type='system',
        )

    def reactivate(self):
        from django.utils import timezone
        from datetime import timedelta

        self.status = 'active'
        self.suspension_reason = None
        self.suspended_at = None
        self.suspended_by = None

        if self.end_date < timezone.now():
            if self.billing_cycle == 'monthly':
                self.end_date = timezone.now() + timedelta(days=30)
            else:
                self.end_date = timezone.now() + timedelta(days=365)

        self.save()

        from apps.notifications.utils import send_notification
        send_notification(
            user=self.business.owner,
            title='Account Reactivated ✅',
            message=(
                f'Your {self.plan.name} subscription '
                f'has been reactivated.'
            ),
            notification_type='system',
        )


class BusinessSubscriptionHistory(TimeStampedModel):
    """Track all subscription changes"""
    ACTION_CHOICES = (
        ('subscribed', 'Subscribed'),
        ('renewed', 'Renewed'),
        ('upgraded', 'Upgraded'),
        ('downgraded', 'Downgraded'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
        ('trial_started', 'Trial Started'),
        ('trial_converted', 'Trial Converted'),
        ('suspended', 'Suspended'),
        ('reactivated', 'Reactivated'),
    )

    business = models.ForeignKey(
        'marketplace.Business',
        on_delete=models.CASCADE,
        related_name='subscription_history'
    )
    plan = models.ForeignKey(
        BusinessPlan,
        on_delete=models.CASCADE,
        related_name='history'
    )
    action = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES
    )
    billing_cycle = models.CharField(
        max_length=20, default='monthly'
    )
    amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    payment_reference = models.CharField(
        max_length=100, blank=True, null=True
    )
    previous_plan = models.ForeignKey(
        BusinessPlan,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='downgrade_history'
    )
    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.business.name} - {self.action} - {self.plan.name}"


class BusinessSubscriptionPayment(TimeStampedModel):
    """Payment records for business subscriptions"""
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
        ('cancelled', 'Cancelled'),
    )

    PAYMENT_TYPE_CHOICES = (
        ('new', 'New Subscription'),
        ('renewal', 'Renewal'),
        ('upgrade', 'Upgrade'),
        ('downgrade', 'Downgrade'),
        ('trial_conversion', 'Trial Conversion'),
        ('reactivation', 'Reactivation'),
    )

    GATEWAY_CHOICES = (
        ('wallet', 'Wallet'),
        ('paystack', 'Paystack'),
        ('flutterwave', 'Flutterwave'),
        ('bank_transfer', 'Bank Transfer'),
        ('admin', 'Admin Credit'),
    )

    subscription = models.ForeignKey(
        BusinessSubscription,
        on_delete=models.CASCADE,
        related_name='payments'
    )
    business = models.ForeignKey(
        'marketplace.Business',
        on_delete=models.CASCADE,
        related_name='subscription_payments'
    )
    plan = models.ForeignKey(
        BusinessPlan,
        on_delete=models.CASCADE,
        related_name='payments'
    )
    payment_type = models.CharField(
        max_length=20,
        choices=PAYMENT_TYPE_CHOICES,
        default='new'
    )
    gateway = models.CharField(
        max_length=20,
        choices=GATEWAY_CHOICES,
        default='wallet'
    )
    billing_cycle = models.CharField(
        max_length=20, default='monthly'
    )
    amount = models.DecimalField(
        max_digits=10, decimal_places=2
    )
    discount_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    tax_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    net_amount = models.DecimalField(
        max_digits=10, decimal_places=2
    )
    currency = models.CharField(max_length=10, default='NGN')
    reference = models.CharField(max_length=100, unique=True)
    gateway_reference = models.CharField(
        max_length=100, blank=True, null=True
    )
    gateway_response = models.JSONField(
        default=dict, blank=True
    )
    period_start = models.DateTimeField(null=True, blank=True)
    period_end = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    refunded_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    refunded_at = models.DateTimeField(null=True, blank=True)
    refund_reason = models.TextField(blank=True, null=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return (
            f"{self.business.name} - "
            f"{self.plan.name} - "
            f"₦{self.amount} - "
            f"{self.status}"
        )

    @property
    def is_successful(self):
        return self.status == 'success'