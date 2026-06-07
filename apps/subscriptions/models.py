from django.db import models
from django.conf import settings
from apps.common.models import TimeStampedModel


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

    # Limits
    max_products = models.IntegerField(default=0)
    max_orders = models.IntegerField(default=0)
    max_users = models.IntegerField(default=1)
    max_storage_gb = models.IntegerField(default=1)

    # Order for display
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'price']

    def __str__(self):
        return f"{self.name} - ₦{self.price}/{self.billing_cycle}"

    @property
    def is_free(self):
        return self.price == 0


class PlanFeature(TimeStampedModel):
    """Features included in each plan"""
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

    # Dates
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    trial_end_date = models.DateTimeField(
        null=True,
        blank=True
    )
    cancelled_at = models.DateTimeField(
        null=True,
        blank=True
    )

    # Payment
    payment_reference = models.CharField(
        max_length=100,
        blank=True,
        null=True
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
    """Billing and subscription history"""
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
        max_length=100,
        blank=True,
        null=True
    )
    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} - {self.action} - {self.plan.name}"