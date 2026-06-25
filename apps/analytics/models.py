from django.db import models
from django.conf import settings
from apps.common.models import TimeStampedModel


class BusinessAnalytics(TimeStampedModel):
    """
    Daily analytics snapshot per business
    Auto generated every day
    """
    business = models.ForeignKey(
        'marketplace.Business',
        on_delete=models.CASCADE,
        related_name='analytics'
    )
    date = models.DateField()

    # Orders
    total_orders = models.IntegerField(default=0)
    completed_orders = models.IntegerField(default=0)
    cancelled_orders = models.IntegerField(default=0)
    pending_orders = models.IntegerField(default=0)
    completion_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )

    # Revenue
    gross_revenue = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )
    net_revenue = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )  # after commission
    delivery_revenue = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    refunds = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    # Commission
    platform_commission = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    # Customers
    total_customers = models.IntegerField(default=0)
    new_customers = models.IntegerField(default=0)
    returning_customers = models.IntegerField(default=0)

    # Products
    total_items_sold = models.IntegerField(default=0)
    top_products = models.JSONField(
        default=list,
        blank=True
    )
    # e.g [{"product_id": 1, "name": "...", "qty": 10, "revenue": 5000}]

    # Average
    avg_order_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    avg_preparation_time = models.IntegerField(default=0)
    avg_delivery_time = models.IntegerField(default=0)

    # Ratings
    avg_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0
    )
    total_reviews = models.IntegerField(default=0)

    # Views/Traffic
    profile_views = models.IntegerField(default=0)
    catalog_views = models.IntegerField(default=0)

    class Meta:
        ordering = ['-date']
        unique_together = ('business', 'date')

    def __str__(self):
        return f"{self.business.name} - {self.date}"


class ProductAnalytics(TimeStampedModel):
    """
    Daily analytics per product
    """
    product = models.ForeignKey(
        'catalog.Product',
        on_delete=models.CASCADE,
        related_name='analytics'
    )
    business = models.ForeignKey(
        'marketplace.Business',
        on_delete=models.CASCADE,
        related_name='product_analytics'
    )
    date = models.DateField()

    # Sales
    units_sold = models.IntegerField(default=0)
    revenue = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    refunds = models.IntegerField(default=0)

    # Cart
    cart_adds = models.IntegerField(default=0)
    cart_removals = models.IntegerField(default=0)
    conversion_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )  # cart adds / purchases

    # Views
    views = models.IntegerField(default=0)

    # Rating
    avg_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0
    )
    new_reviews = models.IntegerField(default=0)

    class Meta:
        ordering = ['-date']
        unique_together = ('product', 'date')

    def __str__(self):
        return f"{self.product.name} - {self.date}"


class PlatformAnalytics(TimeStampedModel):
    """
    Daily platform-wide analytics
    Admin overview
    """
    date = models.DateField(unique=True)

    # Businesses
    total_businesses = models.IntegerField(default=0)
    new_businesses = models.IntegerField(default=0)
    active_businesses = models.IntegerField(default=0)

    # Users
    total_users = models.IntegerField(default=0)
    new_users = models.IntegerField(default=0)
    active_users = models.IntegerField(default=0)
    total_customers = models.IntegerField(default=0)
    total_vendors = models.IntegerField(default=0)
    total_drivers = models.IntegerField(default=0)

    # Orders
    total_orders = models.IntegerField(default=0)
    completed_orders = models.IntegerField(default=0)
    cancelled_orders = models.IntegerField(default=0)

    # Revenue
    gross_volume = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )
    platform_revenue = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )
    vendor_payouts = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )
    driver_payouts = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    # Deliveries
    total_deliveries = models.IntegerField(default=0)
    completed_deliveries = models.IntegerField(default=0)

    # Reviews
    total_reviews = models.IntegerField(default=0)
    avg_platform_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0
    )

    # By industry
    industry_breakdown = models.JSONField(
        default=dict,
        blank=True
    )
    # e.g {"restaurant": {"orders": 50, "revenue": 250000},
    #      "logistics": {"orders": 30, "revenue": 150000}}

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"Platform Analytics - {self.date}"


class CustomerAnalytics(TimeStampedModel):
    """
    Per customer analytics
    Spending patterns, preferences
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='customer_analytics'
    )
    date = models.DateField()

    # Orders
    total_orders = models.IntegerField(default=0)
    completed_orders = models.IntegerField(default=0)
    cancelled_orders = models.IntegerField(default=0)

    # Spending
    total_spent = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )
    avg_order_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    # Favorite businesses/products
    favorite_businesses = models.JSONField(
        default=list,
        blank=True
    )
    favorite_products = models.JSONField(
        default=list,
        blank=True
    )

    class Meta:
        ordering = ['-date']
        unique_together = ('user', 'date')

    def __str__(self):
        return f"{self.user.email} - {self.date}"


class AnalyticsEvent(TimeStampedModel):
    """
    Track specific events for analytics
    e.g page views, clicks, searches
    """
    EVENT_TYPE_CHOICES = (
        ('page_view', 'Page View'),
        ('product_view', 'Product View'),
        ('business_view', 'Business View'),
        ('search', 'Search'),
        ('cart_add', 'Cart Add'),
        ('cart_remove', 'Cart Remove'),
        ('checkout', 'Checkout'),
        ('order_complete', 'Order Complete'),
        ('review_submit', 'Review Submit'),
        ('share', 'Share'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='analytics_events'
    )
    event_type = models.CharField(
        max_length=20,
        choices=EVENT_TYPE_CHOICES
    )

    # What was interacted with
    object_type = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )
    object_id = models.IntegerField(
        null=True,
        blank=True
    )

    # Session/device
    session_id = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True
    )
    user_agent = models.TextField(
        blank=True,
        null=True
    )
    device_type = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )  # mobile, tablet, desktop

    # Extra data
    metadata = models.JSONField(
        default=dict,
        blank=True
    )
    # e.g {"search_query": "jollof", "results": 5}

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['event_type', 'created_at']),
            models.Index(fields=['object_type', 'object_id']),
            models.Index(fields=['user', 'created_at']),
        ]

    def __str__(self):
        return f"{self.event_type} - {self.created_at}"


class SearchAnalytics(TimeStampedModel):
    """
    Track search queries and results
    Helps understand what customers are looking for
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='searches'
    )
    query = models.CharField(max_length=255)
    results_count = models.IntegerField(default=0)
    clicked_result_id = models.IntegerField(
        null=True,
        blank=True
    )
    clicked_result_type = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )  # product, business, category

    # Context
    business = models.ForeignKey(
        'marketplace.Business',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='searches'
    )  # if searching within a business
    industry = models.ForeignKey(
        'marketplace.Industry',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='searches'
    )

    # Result
    converted = models.BooleanField(default=False)
    # Did search lead to order?
    conversion_order = models.ForeignKey(
        'orders.Order',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='search_conversions'
    )

    # Device
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True
    )
    device_type = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )
    date = models.DateField()

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['query', 'date']),
            models.Index(fields=['date']),
        ]

    def __str__(self):
        return f'"{self.query}" - {self.results_count} results'


class CategoryAnalytics(TimeStampedModel):
    """
    Daily analytics per product category
    Track which categories perform best
    """
    category = models.ForeignKey(
        'catalog.ProductCategory',
        on_delete=models.CASCADE,
        related_name='analytics'
    )
    business = models.ForeignKey(
        'marketplace.Business',
        on_delete=models.CASCADE,
        related_name='category_analytics'
    )
    date = models.DateField()

    # Views
    views = models.IntegerField(default=0)
    unique_visitors = models.IntegerField(default=0)

    # Sales
    total_orders = models.IntegerField(default=0)
    units_sold = models.IntegerField(default=0)
    revenue = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    # Products
    total_products = models.IntegerField(default=0)
    active_products = models.IntegerField(default=0)
    top_product_id = models.IntegerField(
        null=True,
        blank=True
    )
    top_product_name = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    # Conversion
    add_to_cart_count = models.IntegerField(default=0)
    conversion_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )

    # Rating
    avg_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0
    )

    class Meta:
        ordering = ['-date']
        unique_together = ('category', 'business', 'date')

    def __str__(self):
        return f"{self.category.name} - {self.date}"


class DriverAnalytics(TimeStampedModel):
    """
    Daily analytics per driver
    Track performance and earnings
    """
    driver = models.ForeignKey(
        'drivers.DriverProfile',
        on_delete=models.CASCADE,
        related_name='analytics'
    )
    date = models.DateField()

    # Deliveries
    total_deliveries = models.IntegerField(default=0)
    completed_deliveries = models.IntegerField(default=0)
    cancelled_deliveries = models.IntegerField(default=0)
    failed_deliveries = models.IntegerField(default=0)
    completion_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )

    # Rides
    total_rides = models.IntegerField(default=0)
    completed_rides = models.IntegerField(default=0)
    cancelled_rides = models.IntegerField(default=0)

    # Earnings
    delivery_earnings = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    ride_earnings = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    bonus_earnings = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    total_earnings = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    tips = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    # Performance
    avg_delivery_time = models.IntegerField(default=0)
    # minutes
    avg_pickup_time = models.IntegerField(default=0)
    # minutes
    total_distance_km = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    online_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )

    # Rating
    avg_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0
    )
    total_ratings = models.IntegerField(default=0)
    new_ratings = models.IntegerField(default=0)

    # Issues
    late_deliveries = models.IntegerField(default=0)
    complaints = models.IntegerField(default=0)

    class Meta:
        ordering = ['-date']
        unique_together = ('driver', 'date')

    def __str__(self):
        return f"Driver {self.driver.id} - {self.date}"

    @property
    def earnings_per_hour(self):
        if self.online_hours > 0:
            return round(
                float(self.total_earnings) /
                float(self.online_hours),
                2
            )
        return 0


class VendorPerformance(TimeStampedModel):
    """
    Weekly/Monthly vendor performance scores
    Used for ranking and rewards
    """
    PERIOD_CHOICES = (
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    )

    PERFORMANCE_TIER_CHOICES = (
        ('bronze', 'Bronze'),
        ('silver', 'Silver'),
        ('gold', 'Gold'),
        ('platinum', 'Platinum'),
    )

    business = models.ForeignKey(
        'marketplace.Business',
        on_delete=models.CASCADE,
        related_name='performance_scores'
    )
    period = models.CharField(
        max_length=10,
        choices=PERIOD_CHOICES,
        default='weekly'
    )
    period_start = models.DateField()
    period_end = models.DateField()

    # Score components (0-100 each)
    order_completion_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )  # % of orders completed
    rating_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )  # based on avg rating
    response_time_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )  # how fast vendor confirms
    cancellation_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )  # low cancellation = high score
    preparation_time_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )  # food ready on time

    # Overall score (weighted average)
    overall_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )

    # Tier
    performance_tier = models.CharField(
        max_length=10,
        choices=PERFORMANCE_TIER_CHOICES,
        default='bronze'
    )

    # Stats for the period
    total_orders = models.IntegerField(default=0)
    completed_orders = models.IntegerField(default=0)
    cancelled_orders = models.IntegerField(default=0)
    avg_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0
    )
    total_revenue = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    # Rewards
    bonus_earned = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    commission_discount = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )  # % discount on commission for high performers

    # Rank
    rank = models.IntegerField(
        null=True,
        blank=True
    )  # position among all vendors

    class Meta:
        ordering = ['-period_start']
        unique_together = ('business', 'period', 'period_start')

    def __str__(self):
        return f"{self.business.name} - {self.period} - {self.overall_score}pts"

    def calculate_score(self):
        """Calculate overall performance score"""
        from decimal import Decimal

        # Weights
        weights = {
            'order_completion': Decimal('0.30'),
            'rating': Decimal('0.25'),
            'response_time': Decimal('0.20'),
            'cancellation': Decimal('0.15'),
            'preparation_time': Decimal('0.10'),
        }

        score = (
            self.order_completion_score * weights['order_completion'] +
            self.rating_score * weights['rating'] +
            self.response_time_score * weights['response_time'] +
            self.cancellation_score * weights['cancellation'] +
            self.preparation_time_score * weights['preparation_time']
        )
        self.overall_score = round(score, 2)

        # Assign tier
        if self.overall_score >= 90:
            self.performance_tier = 'platinum'
            self.commission_discount = Decimal('5.00')
        elif self.overall_score >= 75:
            self.performance_tier = 'gold'
            self.commission_discount = Decimal('3.00')
        elif self.overall_score >= 60:
            self.performance_tier = 'silver'
            self.commission_discount = Decimal('1.00')
        else:
            self.performance_tier = 'bronze'
            self.commission_discount = Decimal('0.00')

        self.save()
        return self.overall_score


class SubscriptionAnalytics(TimeStampedModel):
    """
    Track subscription metrics
    MRR, churn, growth
    """
    date = models.DateField(unique=True)

    # Subscribers
    total_subscribers = models.IntegerField(default=0)
    new_subscribers = models.IntegerField(default=0)
    churned_subscribers = models.IntegerField(default=0)
    reactivated_subscribers = models.IntegerField(default=0)

    # Revenue
    mrr = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )  # Monthly Recurring Revenue
    arr = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )  # Annual Recurring Revenue
    new_mrr = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )  # MRR from new subscribers
    churned_mrr = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )  # MRR lost from churn
    expansion_mrr = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )  # MRR from upgrades

    # Rates
    churn_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )  # percentage
    growth_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )  # percentage

    # By plan
    plan_breakdown = models.JSONField(
        default=dict,
        blank=True
    )
    # e.g {"free": 100, "basic": 50, "pro": 20}

    # Trial
    trial_starts = models.IntegerField(default=0)
    trial_conversions = models.IntegerField(default=0)
    trial_conversion_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"Subscription Analytics - {self.date} MRR: ₦{self.mrr}"

    @property
    def net_new_mrr(self):
        return self.new_mrr + self.expansion_mrr - self.churned_mrr


class PromotionAnalytics(TimeStampedModel):
    """
    Track promotion and discount performance
    """
    PROMOTION_TYPE_CHOICES = (
        ('discount', 'Discount Code'),
        ('flash_sale', 'Flash Sale'),
        ('bundle', 'Bundle Deal'),
        ('free_delivery', 'Free Delivery'),
        ('referral', 'Referral'),
        ('loyalty', 'Loyalty Reward'),
        ('first_order', 'First Order'),
    )

    name = models.CharField(max_length=255)
    promotion_type = models.CharField(
        max_length=20,
        choices=PROMOTION_TYPE_CHOICES
    )
    code = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )

    # Scope
    business = models.ForeignKey(
        'marketplace.Business',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='promotions'
    )  # null = platform-wide

    # Discount
    discount_type = models.CharField(
        max_length=20,
        default='percentage'
    )  # percentage or fixed
    discount_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    min_order_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    max_discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )

    # Limits
    usage_limit = models.IntegerField(
        default=0
    )  # 0 = unlimited
    per_user_limit = models.IntegerField(default=1)

    # Schedule
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField(
        null=True,
        blank=True
    )

    # Performance metrics
    total_uses = models.IntegerField(default=0)
    unique_users = models.IntegerField(default=0)
    total_discount_given = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )
    total_revenue_generated = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )
    total_orders = models.IntegerField(default=0)
    avg_order_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    # ROI
    roi = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )  # revenue / discount_given

    # New vs returning customers
    new_customer_uses = models.IntegerField(default=0)
    returning_customer_uses = models.IntegerField(default=0)

    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='promotions'
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.promotion_type})"

    @property
    def is_valid_now(self):
        from django.utils import timezone
        now = timezone.now()
        if not self.is_active:
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
            return round(
                self.total_uses / self.usage_limit * 100,
                1
            )
        return 0

    def calculate_roi(self):
        """Calculate ROI"""
        from decimal import Decimal
        if self.total_discount_given > 0:
            self.roi = round(
                float(self.total_revenue_generated) /
                float(self.total_discount_given),
                2
            )
            self.save()
        return self.roi