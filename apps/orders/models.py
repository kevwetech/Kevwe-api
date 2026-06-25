from django.db import models
from django.conf import settings
from apps.common.models import TimeStampedModel


class Cart(TimeStampedModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='cart'
    )
    # Link to business for marketplace orders
    business = models.ForeignKey(
        'marketplace.Business',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='carts'
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email}'s cart"

    @property
    def total(self):
        return sum(
            item.subtotal for item in self.items.all()
        )

    @property
    def total_items(self):
        return self.items.count()

    def clear(self):
        self.items.all().delete()


class CartItem(TimeStampedModel):
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name='items'
    )

    # Support both old products app and new catalog app
    product = models.ForeignKey(
        'catalog.Product',
        on_delete=models.CASCADE,
        related_name='cart_items',
        null=True,
        blank=True
    )
    variant = models.ForeignKey(
        'catalog.ProductVariant',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cart_items'
    )

    quantity = models.IntegerField(default=1)

    # Selected addons stored as JSON
    # e.g [{"group_id": 1, "group_name": "Add Protein",
    #        "items": [{"id": 1, "name": "Chicken", "price": 500}]}]
    selected_addons = models.JSONField(
        default=list,
        blank=True
    )

    # Snapshot prices at time of adding
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    addon_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    special_instructions = models.TextField(
        blank=True,
        null=True
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        name = self.product.name if self.product else 'Unknown'
        return f"{name} x {self.quantity}"

    @property
    def item_price(self):
        """Base price + variant modifier"""
        if self.variant:
            return self.variant.price
        if self.product:
            return self.product.price
        return self.unit_price

    @property
    def subtotal(self):
        return (self.item_price + self.addon_price) * self.quantity

    def calculate_addon_price(self):
        """Calculate total addon price from selected_addons"""
        total = 0
        for group in self.selected_addons:
            for item in group.get('items', []):
                total += float(item.get('price', 0))
        return total


class Order(TimeStampedModel):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('preparing', 'Preparing'),
        ('ready', 'Ready for Pickup/Delivery'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('out_for_delivery', 'Out for Delivery'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
        ('failed', 'Failed'),
    )

    PAYMENT_STATUS_CHOICES = (
        ('unpaid', 'Unpaid'),
        ('paid', 'Paid'),
        ('refunded', 'Refunded'),
        ('partially_refunded', 'Partially Refunded'),
    )

    ORDER_TYPE_CHOICES = (
        ('delivery', 'Delivery'),
        ('pickup', 'Pickup'),
        ('dine_in', 'Dine In'),
        ('service', 'Service'),
        ('digital', 'Digital'),
    )

    PAYMENT_METHOD_CHOICES = (
        ('wallet', 'Wallet'),
        ('paystack', 'Paystack'),
        ('flutterwave', 'Flutterwave'),
        ('cash', 'Cash on Delivery'),
        ('transfer', 'Bank Transfer'),
    )

    # Users
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='orders'
    )

    # Business (marketplace)
    business = models.ForeignKey(
        'marketplace.Business',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders'
    )

    # Reference
    reference = models.CharField(
        max_length=100,
        unique=True
    )
    order_number = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        null=True
    )

    # Order type
    order_type = models.CharField(
        max_length=20,
        choices=ORDER_TYPE_CHOICES,
        default='delivery'
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='unpaid'
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default='wallet'
    )

    # Delivery address (Option C — saved or manual)
    delivery_address_ref = models.ForeignKey(
        'locations.Address',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders'
    )
    delivery_name = models.CharField(
        max_length=255,
        blank=True
    )
    delivery_phone = models.CharField(
        max_length=20,
        blank=True
    )
    delivery_address = models.TextField(blank=True)
    delivery_city = models.CharField(
        max_length=100,
        blank=True
    )
    delivery_state = models.CharField(
        max_length=100,
        blank=True
    )
    delivery_lat = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )
    delivery_lng = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )
    delivery_city_ref = models.ForeignKey(
        'locations.City',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders'
    )
    delivery_zone = models.ForeignKey(
        'locations.Zone',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders'
    )

    # Assigned driver
    driver = models.ForeignKey(
        'drivers.DriverProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders'
    )

    # Pricing
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    delivery_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    tax_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    # Commission splits (auto calculated)
    platform_commission = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    business_earnings = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    driver_earnings = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    # Timing
    estimated_delivery_time = models.IntegerField(
        default=30
    )  # minutes
    scheduled_time = models.DateTimeField(
        null=True,
        blank=True
    )  # for pre-orders
    confirmed_at = models.DateTimeField(
        null=True,
        blank=True
    )
    preparing_at = models.DateTimeField(
        null=True,
        blank=True
    )
    ready_at = models.DateTimeField(
        null=True,
        blank=True
    )
    picked_up_at = models.DateTimeField(
        null=True,
        blank=True
    )
    delivered_at = models.DateTimeField(
        null=True,
        blank=True
    )
    cancelled_at = models.DateTimeField(
        null=True,
        blank=True
    )

    # Cancellation
    cancellation_reason = models.TextField(
        blank=True,
        null=True
    )
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cancelled_orders'
    )

    # Rating
    rating = models.IntegerField(null=True, blank=True)
    review = models.TextField(blank=True, null=True)
    rated_at = models.DateTimeField(null=True, blank=True)

    # Notes
    special_instructions = models.TextField(
        blank=True,
        null=True
    )
    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Order {self.reference}"

    def calculate_totals(self):
        """Auto calculate order totals and commission splits"""
        from decimal import Decimal

        items = self.items.all()
        self.subtotal = sum(item.subtotal for item in items)
        self.total = (
            self.subtotal +
            self.delivery_fee +
            self.tax_amount -
            self.discount_amount
        )

        # Commission splits
        if self.business:
            commission_rate = Decimal(
                str(self.business.commission_rate)
            ) / 100
            driver_rate = Decimal(
                str(self.business.industry.driver_commission)
            ) / 100
            vendor_rate = Decimal(
                str(self.business.industry.vendor_commission)
            ) / 100

            self.platform_commission = (
                self.subtotal * commission_rate
            )
            self.driver_earnings = (
                self.delivery_fee * Decimal('0.80')
            )  # 80% of delivery fee
            self.business_earnings = (
                self.subtotal * vendor_rate
            )

        self.save()


class OrderItem(TimeStampedModel):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items'
    )

    # Product from catalog
    product = models.ForeignKey(
        'catalog.Product',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='order_items'
    )
    variant = models.ForeignKey(
        'catalog.ProductVariant',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='order_items'
    )

    # Snapshots at time of order
    product_name = models.CharField(max_length=255)
    variant_name = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )
    product_image = models.URLField(
        blank=True,
        null=True
    )

    # Pricing snapshot
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    addon_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    quantity = models.IntegerField(default=1)
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    # Selected addons snapshot
    selected_addons = models.JSONField(
        default=list,
        blank=True
    )

    # Special instructions for this item
    special_instructions = models.TextField(
        blank=True,
        null=True
    )

    # Status (vendor can update per item)
    is_available = models.BooleanField(default=True)
    unavailability_reason = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    def __str__(self):
        return f"{self.product_name} x {self.quantity}"

    def save(self, *args, **kwargs):
        # Auto calculate subtotal
        self.subtotal = (
            (self.unit_price + self.addon_price) *
            self.quantity
        )
        super().save(*args, **kwargs)


class OrderTracking(TimeStampedModel):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='tracking'
    )
    status = models.CharField(max_length=20)
    description = models.TextField()
    location = models.CharField(
        max_length=255,
        blank=True,
        null=True
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
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.order.reference} - {self.status}"