from django.db import models
from django.conf import settings
from apps.common.models import TimeStampedModel


class ProductCategory(TimeStampedModel):
    """
    Hierarchical category system
    Supports unlimited nesting:
    Food → Nigerian Food → Soups → Egusi Soup
    Logistics → Express → Same Day
    """
    business = models.ForeignKey(
        'marketplace.Business',
        on_delete=models.CASCADE,
        related_name='categories',
        null=True,
        blank=True
    )  # null = platform-wide category

    # Self referential for hierarchy
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children'
    )

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255)
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(
        upload_to='catalog/categories/',
        null=True,
        blank=True
    )
    icon = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']
        verbose_name_plural = 'Product Categories'
        unique_together = ('business', 'slug')

    def __str__(self):
        if self.parent:
            return f"{self.parent} → {self.name}"
        return self.name

    @property
    def full_path(self):
        """Return full category path"""
        if self.parent:
            return f"{self.parent.full_path} → {self.name}"
        return self.name

    @property
    def level(self):
        """Return depth level (0 = root)"""
        if self.parent is None:
            return 0
        return self.parent.level + 1

    @property
    def ancestors(self):
        """Return all ancestors from root to parent"""
        ancestors = []
        current = self.parent
        while current:
            ancestors.insert(0, current)
            current = current.parent
        return ancestors

    @property
    def descendants(self):
        """Return all descendants recursively"""
        result = []
        for child in self.children.filter(is_active=True):
            result.append(child)
            result.extend(child.descendants)
        return result

    @property
    def is_root(self):
        return self.parent is None

    @property
    def is_leaf(self):
        return not self.children.filter(is_active=True).exists()

    def get_all_products(self):
        """Get products from this category and all descendants"""
        category_ids = [self.id] + [d.id for d in self.descendants]
        return Product.objects.filter(
            category__id__in=category_ids,
            is_active=True
        )


class Product(TimeStampedModel):
    """
    A product or menu item in a business catalog
    Works for restaurants (menu items) and
    logistics (service types)
    """
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('out_of_stock', 'Out of Stock'),
        ('coming_soon', 'Coming Soon'),
    )

    TYPE_CHOICES = (
        ('simple', 'Simple Product'),
        ('variable', 'Variable Product'),
        ('bundle', 'Bundle'),
        ('service', 'Service'),
    )

    # Business
    business = models.ForeignKey(
        'marketplace.Business',
        on_delete=models.CASCADE,
        related_name='products'
    )

    # Category
    category = models.ForeignKey(
        ProductCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products'
    )

    # Basic info
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255)
    description = models.TextField(blank=True, null=True)
    short_description = models.CharField(
        max_length=500,
        blank=True,
        null=True
    )

    # Type
    product_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default='simple'
    )

    # Pricing
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    compare_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )  # Original price before discount
    cost_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )  # Cost to make/buy

    # Stock
    track_stock = models.BooleanField(default=False)
    stock_quantity = models.IntegerField(default=0)
    low_stock_threshold = models.IntegerField(default=5)
    allow_backorder = models.BooleanField(default=False)

    # Physical properties
    weight = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True
    )
    preparation_time = models.IntegerField(
        default=0
    )  # minutes for restaurants

    # Media
    cover_image = models.ImageField(
        upload_to='catalog/products/',
        null=True,
        blank=True
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active'
    )
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    is_available = models.BooleanField(default=True)

    # Stats
    total_sold = models.IntegerField(default=0)
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

    # Tags and meta
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

    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', '-is_featured', 'name']
        unique_together = ('business', 'slug')

    def __str__(self):
        return f"{self.name} — {self.business.name}"

    @property
    def is_on_sale(self):
        return (
            self.compare_price is not None and
            self.compare_price > self.price
        )

    @property
    def discount_percentage(self):
        if self.is_on_sale:
            discount = (
                (self.compare_price - self.price) /
                self.compare_price * 100
            )
            return round(discount, 1)
        return 0

    @property
    def in_stock(self):
        if not self.track_stock:
            return True
        return self.stock_quantity > 0 or self.allow_backorder

    @property
    def effective_price(self):
        """Get price from variants or base price"""
        if self.product_type == 'variable':
            variants = self.variants.filter(is_active=True)
            if variants.exists():
                return variants.order_by('price').first().price
        return self.price


class ProductImage(TimeStampedModel):
    """Multiple images for a product"""
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='images'
    )
    image = models.ImageField(
        upload_to='catalog/products/gallery/'
    )
    alt_text = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )
    is_primary = models.BooleanField(default=False)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.product.name} image {self.id}"


class ProductVariantOption(TimeStampedModel):
    """
    Variant option types
    e.g Size, Color, Spice Level, Protein
    """
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='variant_options'
    )
    name = models.CharField(max_length=100)
    # e.g 'Size', 'Color', 'Spice Level'
    is_required = models.BooleanField(default=False)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order']
        unique_together = ('product', 'name')

    def __str__(self):
        return f"{self.product.name} - {self.name}"


class ProductVariant(TimeStampedModel):
    """
    Product variants
    e.g Small Jollof Rice, Large Egusi Soup
    or Express Delivery, Standard Delivery
    """
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='variants'
    )
    option = models.ForeignKey(
        ProductVariantOption,
        on_delete=models.CASCADE,
        related_name='variants',
        null=True,
        blank=True
    )

    name = models.CharField(max_length=255)
    # e.g 'Small', 'Large', 'Extra Spicy'
    sku = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        unique=True
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    compare_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    cost_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )

    # Stock
    track_stock = models.BooleanField(default=False)
    stock_quantity = models.IntegerField(default=0)

    # Image
    image = models.ImageField(
        upload_to='catalog/variants/',
        null=True,
        blank=True
    )

    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'price']

    def __str__(self):
        return f"{self.product.name} - {self.name}"

    @property
    def in_stock(self):
        if not self.track_stock:
            return True
        return self.stock_quantity > 0


class ProductAddon(TimeStampedModel):
    """
    Optional add-ons for products
    e.g Extra cheese, Extra meat, Sauce
    """
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='addons'
    )
    name = models.CharField(max_length=255)
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    is_required = models.BooleanField(default=False)
    max_quantity = models.IntegerField(default=1)
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.product.name} + {self.name}"

class ProductTag(TimeStampedModel):
    """
    Reusable tags for products
    e.g 'Spicy', 'Vegan', 'Best Seller', 'New'
    """
    business = models.ForeignKey(
        'marketplace.Business',
        on_delete=models.CASCADE,
        related_name='product_tags',
        null=True,
        blank=True
    )  # null = platform-wide tag
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100)
    color = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )  # for UI badge color
    icon = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )
    is_active = models.BooleanField(default=True)

    # Products using this tag
    products = models.ManyToManyField(
        Product,
        blank=True,
        related_name='product_tags'
    )

    class Meta:
        ordering = ['name']
        unique_together = ('business', 'slug')

    def __str__(self):
        return self.name


class ProductAttribute(TimeStampedModel):
    """
    Product attributes for filtering and display
    e.g Cuisine Type, Allergens, Calories, Ingredients
    """
    ATTRIBUTE_TYPE_CHOICES = (
        ('text', 'Text'),
        ('number', 'Number'),
        ('boolean', 'Boolean'),
        ('list', 'List'),
        ('color', 'Color'),
    )

    business = models.ForeignKey(
        'marketplace.Business',
        on_delete=models.CASCADE,
        related_name='product_attributes',
        null=True,
        blank=True
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='attributes'
    )
    name = models.CharField(max_length=100)
    # e.g 'Calories', 'Allergens', 'Cuisine'
    value = models.TextField()
    # e.g '450 kcal', 'Nuts, Dairy', 'Nigerian'
    attribute_type = models.CharField(
        max_length=20,
        choices=ATTRIBUTE_TYPE_CHOICES,
        default='text'
    )
    unit = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )  # e.g 'kcal', 'g', 'ml'
    is_visible = models.BooleanField(default=True)
    is_filterable = models.BooleanField(default=False)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']
        unique_together = ('product', 'name')

    def __str__(self):
        return f"{self.product.name} - {self.name}: {self.value}"

    def get_value(self):
        """Return typed value"""
        import json
        try:
            if self.attribute_type == 'number':
                return float(self.value)
            elif self.attribute_type == 'boolean':
                return self.value.lower() in ('true', '1', 'yes')
            elif self.attribute_type == 'list':
                return json.loads(self.value)
            return self.value
        except Exception:
            return self.value


class ProductVariantValue(TimeStampedModel):
    """
    Specific values for variant options
    e.g Size option → Small, Medium, Large
    Color option → Red, Blue, Green
    Spice Level → Mild, Medium, Hot, Extra Hot
    """
    option = models.ForeignKey(
        ProductVariantOption,
        on_delete=models.CASCADE,
        related_name='values'
    )
    value = models.CharField(max_length=100)
    # e.g 'Small', 'Red', 'Mild'
    display_name = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )  # Optional display override
    color_hex = models.CharField(
        max_length=10,
        blank=True,
        null=True
    )  # For color variants
    image = models.ImageField(
        upload_to='catalog/variant_values/',
        null=True,
        blank=True
    )
    price_modifier = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )  # +/- from base price
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'value']
        unique_together = ('option', 'value')

    def __str__(self):
        return f"{self.option.name}: {self.value}"

    @property
    def label(self):
        return self.display_name or self.value


class ProductAddonGroup(TimeStampedModel):
    """
    Groups of add-ons for a product
    e.g 'Extra Protein' group → Chicken, Beef, Fish
    'Sauce' group → Tomato, Pepper, Onion
    'Drinks' group → Coke, Fanta, Water
    """
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='addon_groups'
    )
    name = models.CharField(max_length=255)
    # e.g 'Extra Protein', 'Choose Sauce', 'Add Drinks'
    description = models.TextField(blank=True, null=True)

    # Selection rules
    is_required = models.BooleanField(default=False)
    min_selections = models.IntegerField(default=0)
    max_selections = models.IntegerField(default=1)
    # 0 = unlimited

    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return f"{self.product.name} - {self.name}"

    @property
    def addons(self):
        return self.group_addons.filter(is_active=True)


class ProductAddonItem(TimeStampedModel):
    """
    Individual items within an addon group
    """
    group = models.ForeignKey(
        ProductAddonGroup,
        on_delete=models.CASCADE,
        related_name='group_addons'
    )
    name = models.CharField(max_length=255)
    description = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    image = models.ImageField(
        upload_to='catalog/addons/',
        null=True,
        blank=True
    )
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    order = models.IntegerField(default=0)

    # Stock
    track_stock = models.BooleanField(default=False)
    stock_quantity = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return f"{self.group.name} → {self.name}"

    @property
    def in_stock(self):
        if not self.track_stock:
            return True
        return self.stock_quantity > 0


class InventoryMovement(TimeStampedModel):
    """
    Track all stock movements for products and variants
    """
    MOVEMENT_TYPE_CHOICES = (
        ('purchase', 'Purchase/Restock'),
        ('sale', 'Sale'),
        ('adjustment', 'Manual Adjustment'),
        ('return', 'Customer Return'),
        ('damage', 'Damaged/Loss'),
        ('transfer', 'Transfer'),
        ('opening', 'Opening Stock'),
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='inventory_movements'
    )
    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
        related_name='inventory_movements',
        null=True,
        blank=True
    )
    movement_type = models.CharField(
        max_length=20,
        choices=MOVEMENT_TYPE_CHOICES
    )

    # Quantity
    quantity = models.IntegerField()
    # positive = stock in, negative = stock out
    quantity_before = models.IntegerField(default=0)
    quantity_after = models.IntegerField(default=0)

    # Reference
    reference = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )  # e.g order number
    notes = models.TextField(blank=True, null=True)

    # Who did it
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='inventory_movements'
    )

    # Cost
    unit_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    total_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        direction = '+' if self.quantity > 0 else ''
        return f"{self.product.name} {direction}{self.quantity} ({self.movement_type})"

    def save(self, *args, **kwargs):
        # Auto calculate total cost
        if self.unit_cost and self.quantity:
            self.total_cost = (
                abs(self.quantity) *
                self.unit_cost
            )
        super().save(*args, **kwargs)

        # Update product/variant stock
        if self.variant:
            self.variant.stock_quantity = self.quantity_after
            self.variant.save()
        else:
            self.product.stock_quantity = self.quantity_after
            self.product.save()


class ProductCollection(TimeStampedModel):
    """
    Curated collections of products
    e.g 'Best Sellers', 'Today's Special',
        'Staff Picks', 'Happy Hour Deals'
    """
    business = models.ForeignKey(
        'marketplace.Business',
        on_delete=models.CASCADE,
        related_name='collections'
    )
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255)
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(
        upload_to='catalog/collections/',
        null=True,
        blank=True
    )
    banner_image = models.ImageField(
        upload_to='catalog/collections/banners/',
        null=True,
        blank=True
    )

    # Products in this collection
    products = models.ManyToManyField(
        Product,
        blank=True,
        related_name='collections',
        through='CollectionProduct'
    )

    # Schedule
    starts_at = models.DateTimeField(
        null=True,
        blank=True
    )
    ends_at = models.DateTimeField(
        null=True,
        blank=True
    )

    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    is_automated = models.BooleanField(default=False)
    # If True use rules instead of manual products
    automation_rules = models.JSONField(
        default=dict,
        blank=True
    )
    # e.g {"min_rating": 4.5, "tags": ["bestseller"]}

    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', '-created_at']
        unique_together = ('business', 'slug')

    def __str__(self):
        return f"{self.business.name} - {self.name}"

    @property
    def is_active_now(self):
        from django.utils import timezone
        now = timezone.now()
        if not self.is_active:
            return False
        if self.starts_at and now < self.starts_at:
            return False
        if self.ends_at and now > self.ends_at:
            return False
        return True

    @property
    def product_count(self):
        return self.products.filter(
            is_active=True,
            status='active'
        ).count()

    def get_products(self):
        """Get products based on manual or automated rules"""
        if self.is_automated and self.automation_rules:
            return self._get_automated_products()
        return self.products.filter(
            is_active=True,
            status='active'
        ).order_by('collectionproduct__order')

    def _get_automated_products(self):
        """Apply automation rules to get products"""
        rules = self.automation_rules
        products = Product.objects.filter(
            business=self.business,
            is_active=True,
            status='active'
        )
        if rules.get('min_rating'):
            products = products.filter(
                rating__gte=rules['min_rating']
            )
        if rules.get('is_featured'):
            products = products.filter(is_featured=True)
        if rules.get('tags'):
            for tag in rules['tags']:
                products = products.filter(
                    tags__icontains=tag
                )
        if rules.get('category_id'):
            products = products.filter(
                category__id=rules['category_id']
            )
        if rules.get('max_price'):
            products = products.filter(
                price__lte=rules['max_price']
            )
        if rules.get('min_sold'):
            products = products.filter(
                total_sold__gte=rules['min_sold']
            )
        return products


class CollectionProduct(TimeStampedModel):
    """
    Through model for ProductCollection products
    Allows ordering products within a collection
    """
    collection = models.ForeignKey(
        ProductCollection,
        on_delete=models.CASCADE
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE
    )
    order = models.IntegerField(default=0)
    notes = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    class Meta:
        ordering = ['order']
        unique_together = ('collection', 'product')

    def __str__(self):
        return f"{self.collection.name} → {self.product.name}"