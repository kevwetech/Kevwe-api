
from django.conf import settings
from django.db import models
from apps.common.models import TimeStampedModel


class Promotion(TimeStampedModel):
    PROMOTION_TYPE_CHOICES = (
        ('discount',       'Discount Code'),
        ('flash_sale',     'Flash Sale'),
        ('bundle',         'Bundle Deal'),
        ('free_delivery',  'Free Delivery'),
        ('referral',       'Referral'),
        ('loyalty',        'Loyalty Reward'),
        ('first_order',    'First Order'),
        ('booking_coupon', 'Booking Coupon'),
    )
    DISCOUNT_TYPE_CHOICES = (
        ('percentage', 'Percentage'),
        ('fixed',      'Fixed Amount'),
    )
    STATUS_CHOICES = (
        ('active',   'Active'),
        ('inactive', 'Inactive'),
        ('expired',  'Expired'),
    )

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    promotion_type = models.CharField(max_length=20, choices=PROMOTION_TYPE_CHOICES)
    code = models.CharField(max_length=50, blank=True, null=True, db_index=True)

    business = models.ForeignKey(
        'marketplace.Business', on_delete=models.CASCADE,
        null=True, blank=True, related_name='promotions',
        help_text='Blank = platform-wide promotion')

    item = models.ForeignKey(
        'bookings.BookableItem', on_delete=models.CASCADE,
        null=True, blank=True, related_name='promotions',
        help_text='Restrict to one bookable item. Blank = business-wide.')
    min_nights = models.PositiveIntegerField(null=True, blank=True)

    discount_type = models.CharField(
        max_length=20, choices=DISCOUNT_TYPE_CHOICES, default='percentage')
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_discount_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True)
    min_order_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    usage_limit = models.IntegerField(default=0)       # 0 = unlimited
    per_user_limit = models.IntegerField(default=1)
    total_uses = models.IntegerField(default=0)
    total_discount_given = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField(null=True, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    is_active = models.BooleanField(default=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='created_promotions')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} ({self.promotion_type})'

    @property
    def is_valid_now(self):
        from django.utils import timezone
        now = timezone.now()
        if not self.is_active or self.status != 'active':
            return False
        if now < self.starts_at:
            return False
        if self.ends_at and now > self.ends_at:
            return False
        if self.usage_limit > 0 and self.total_uses >= self.usage_limit:
            return False
        return True

    @property
    def usage_percentage(self):
        if self.usage_limit > 0:
            return round(self.total_uses / self.usage_limit * 100, 1)
        return 0

    def redeem(self, order_amount=None):
        '''Call at the point of use — after validating eligibility,
        not before. Raises if the code can no longer be used.'''
        from django.core.exceptions import ValidationError
        from django.db.models import F

        if not self.is_valid_now:
            raise ValidationError('This promotion is no longer valid.')
        if order_amount is not None and self.min_order_amount and order_amount < self.min_order_amount:
            raise ValidationError(
                f'Minimum order amount for this promotion is {self.min_order_amount}.')

        Promotion.objects.filter(pk=self.pk).update(total_uses=F('total_uses') + 1)
        self.refresh_from_db(fields=['total_uses'])

    def compute_discount(self, order_amount):
        '''Amount to take off, given an order total. Does not
        record usage — call redeem() separately once the order
        actually completes.'''
        from decimal import Decimal
        order_amount = Decimal(order_amount)
        if self.discount_type == 'percentage':
            amount = order_amount * (self.discount_value / Decimal('100'))
        else:
            amount = self.discount_value
        if self.max_discount_amount:
            amount = min(amount, self.max_discount_amount)
        return min(amount, order_amount)