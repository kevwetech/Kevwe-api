from rest_framework import serializers
from .models import (
    ProductCategory, Product,
    ProductImage, ProductVariantOption,
    ProductVariant, ProductAddon, ProductTag,
    ProductAttribute, ProductVariantValue, ProductAddonItem, 
    ProductAddonGroup, InventoryMovement, CollectionProduct,
    ProductCollection
)


class ProductCategorySerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()
    parent_name = serializers.CharField(
        source='parent.name',
        read_only=True
    )
    full_path = serializers.CharField(read_only=True)
    level = serializers.IntegerField(read_only=True)
    is_root = serializers.BooleanField(read_only=True)
    is_leaf = serializers.BooleanField(read_only=True)
    product_count = serializers.SerializerMethodField()
    ancestors = serializers.SerializerMethodField()

    class Meta:
        model = ProductCategory
        fields = (
            'id',
            'business',
            'parent',
            'parent_name',
            'name',
            'slug',
            'description',
            'image',
            'icon',
            'is_active',
            'is_featured',
            'order',
            'full_path',
            'level',
            'is_root',
            'is_leaf',
            'ancestors',
            'children',
            'product_count',
            'created_at',
        )
        read_only_fields = ('id', 'created_at')

    def get_children(self, obj):
        """Recursively serialize children"""
        children = obj.children.filter(is_active=True)
        if children.exists():
            return ProductCategorySerializer(
                children,
                many=True,
                context=self.context
            ).data
        return []

    def get_product_count(self, obj):
        return obj.products.filter(
            is_active=True,
            status='active'
        ).count()

    def get_ancestors(self, obj):
        return [
            {
                'id': a.id,
                'name': a.name,
                'slug': a.slug,
            }
            for a in obj.ancestors
        ]


class FlatCategorySerializer(serializers.ModelSerializer):
    """Flat (non-nested) category serializer for lists"""
    parent_name = serializers.CharField(
        source='parent.name',
        read_only=True
    )
    full_path = serializers.CharField(read_only=True)
    level = serializers.IntegerField(read_only=True)
    product_count = serializers.SerializerMethodField()

    class Meta:
        model = ProductCategory
        fields = (
            'id',
            'business',
            'parent',
            'parent_name',
            'name',
            'slug',
            'description',
            'image',
            'icon',
            'is_active',
            'is_featured',
            'order',
            'full_path',
            'level',
            'product_count',
            'created_at',
        )
        read_only_fields = ('id', 'created_at')

    def get_product_count(self, obj):
        return obj.products.filter(
            is_active=True,
            status='active'
        ).count()


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = (
            'id',
            'image',
            'alt_text',
            'is_primary',
            'order',
        )
        read_only_fields = ('id',)


class ProductVariantValueSerializer(serializers.ModelSerializer):
    label = serializers.SerializerMethodField()

    class Meta:
        model = ProductVariantValue
        fields = (
            'id',
            'option',
            'value',
            'display_name',
            'label',
            'color_hex',
            'image',
            'price_modifier',
            'is_active',
            'is_default',
            'order',
        )
        read_only_fields = (
            'id',
            'option',
            'label',
        )

    def get_label(self, obj):
        return obj.display_name or obj.value


class ProductVariantOptionSerializer(serializers.ModelSerializer):
    values = serializers.SerializerMethodField()
    class Meta:
        model = ProductVariantOption
        fields = (
            'id',
            'name',         
            'is_required',
            'order',
            'values',
        )
        read_only_fields = ('id',)

    def get_values(self, obj):
        values = obj.values.filter(is_active=True)
        return ProductVariantValueSerializer(
            values,
            many=True,
            context=self.context
        ).data



class ProductVariantSerializer(serializers.ModelSerializer):
    option_name = serializers.CharField(
        source='option.name',
        read_only=True
    )
    in_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = ProductVariant
        fields = (
            'id',
            'option',
            'option_name',
            'name',
            'sku',
            'price',
            'compare_price',
            'cost_price',
            'track_stock',
            'stock_quantity',
            'image',
            'is_active',
            'is_default',
            'order',
            'in_stock',
        )
        read_only_fields = ('id',)


class ProductAddonItemSerializer(serializers.ModelSerializer):
    in_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = ProductAddonItem
        fields = (
            'id',
            'name',
            'description',
            'price',
            'image',
            'is_active',
            'is_default',
            'order',
            'track_stock',
            'stock_quantity',
            'in_stock',
        )
        read_only_fields = ('id', 'in_stock')


class ProductAddonGroupSerializer(serializers.ModelSerializer):
    addons = ProductAddonItemSerializer(
        source='group_addons',
        many=True,
        read_only=True
    )

    class Meta:
        model = ProductAddonGroup
        fields = (
            'id',
            'product',
            'name',
            'description',
            'is_required',
            'min_selections',
            'max_selections',
            'is_active',
            'order',
            'addons',
        )
        read_only_fields = (
            'id',
            'product',
        )

class ProductAddonSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductAddon
        fields = (
            'id',
            'name',
            'price',
            'is_required',
            'max_quantity',
            'is_active',
            'order',
        )
        read_only_fields = ('id',)


class ProductSerializer(serializers.ModelSerializer):
    business_name = serializers.CharField(
        source='business.name',
        read_only=True
    )
    category_name = serializers.CharField(
        source='category.name',
        read_only=True
    )
    category_path = serializers.CharField(
        source='category.full_path',
        read_only=True
    )
    images = ProductImageSerializer(
        many=True,
        read_only=True
    )
    variants = ProductVariantSerializer(
        many=True,
        read_only=True
    )
    variant_options = ProductVariantOptionSerializer(
        many=True,
        read_only=True
    )
    addons = ProductAddonSerializer(
        many=True,
        read_only=True
    )
    addon_groups = ProductAddonGroupSerializer(    # ← explicit serializer
        many=True,
        read_only=True
    )
    is_on_sale = serializers.BooleanField(read_only=True)
    discount_percentage = serializers.FloatField(read_only=True)
    in_stock = serializers.BooleanField(read_only=True)
    effective_price = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True
    )

    class Meta:
        model = Product
        fields = (
            'id',
            'business',
            'business_name',
            'category',
            'category_name',
            'category_path',
            'name',
            'slug',
            'description',
            'short_description',
            'product_type',
            'price',
            'compare_price',
            'cost_price',
            'effective_price',
            'is_on_sale',
            'discount_percentage',
            'track_stock',
            'stock_quantity',
            'low_stock_threshold',
            'allow_backorder',
            'in_stock',
            'weight',
            'preparation_time',
            'cover_image',
            'images',
            'variants',
            'variant_options',
            'addons',
            'addon_groups',
            'status',
            'is_active',
            'is_featured',
            'is_available',
            'total_sold',
            'total_revenue',
            'rating',
            'total_ratings',
            'tags',
            'order',
            'created_at',
        )
        read_only_fields = (
            'id',
            'total_sold',
            'total_revenue',
            'rating',
            'total_ratings',
            'created_at',
        )

class CreateProductSerializer(serializers.Serializer):
    category_id = serializers.IntegerField(required=False)
    name = serializers.CharField()
    slug = serializers.SlugField()
    description = serializers.CharField(
        required=False,
        allow_blank=True
    )
    short_description = serializers.CharField(
        required=False,
        allow_blank=True
    )
    product_type = serializers.ChoiceField(
        choices=['simple', 'variable', 'bundle', 'service'],
        default='simple'
    )
    price = serializers.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    compare_price = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False
    )
    cost_price = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False
    )
    track_stock = serializers.BooleanField(default=False)
    stock_quantity = serializers.IntegerField(default=0)
    weight = serializers.DecimalField(
        max_digits=8,
        decimal_places=2,
        required=False
    )
    preparation_time = serializers.IntegerField(default=0)
    is_featured = serializers.BooleanField(default=False)
    tags = serializers.ListField(
        child=serializers.CharField(),
        required=False
    )
    order = serializers.IntegerField(default=0)

class ProductTagSerializer(serializers.ModelSerializer):
    product_count = serializers.SerializerMethodField()

    class Meta:
        model = ProductTag
        fields = (
            'id',
            'business',
            'name',
            'slug',
            'color',
            'icon',
            'is_active',
            'product_count',
            'created_at',
        )
        read_only_fields = ('id', 'created_at')

    def get_product_count(self, obj):
        return obj.products.filter(
            is_active=True,
            status='active'
        ).count()


class ProductAttributeSerializer(serializers.ModelSerializer):
    typed_value = serializers.SerializerMethodField()

    class Meta:
        model = ProductAttribute
        fields = (
            'id',
            'name',
            'value',
            'typed_value',
            'attribute_type',
            'unit',
            'is_visible',
            'is_filterable',
            'order',
            'created_at',
        )
        read_only_fields = ('id', 'typed_value', 'created_at')

    def get_typed_value(self, obj):
        return obj.get_value()


class InventoryMovementSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(
        source='product.name',
        read_only=True
    )
    variant_name = serializers.CharField(
        source='variant.name',
        read_only=True
    )
    performed_by_name = serializers.CharField(
        source='performed_by.full_name',
        read_only=True
    )

    class Meta:
        model = InventoryMovement
        fields = (
            'id',
            'product',
            'product_name',
            'variant',
            'variant_name',
            'movement_type',
            'quantity',
            'quantity_before',
            'quantity_after',
            'reference',
            'notes',
            'performed_by',
            'performed_by_name',
            'unit_cost',
            'total_cost',
            'created_at',
        )
        read_only_fields = (
            'id',
            'total_cost',
            'created_at',
        )


class CollectionProductSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(
        source='product.name',
        read_only=True
    )
    product_price = serializers.DecimalField(
        source='product.price',
        max_digits=10,
        decimal_places=2,
        read_only=True
    )
    product_image = serializers.ImageField(
        source='product.cover_image',
        read_only=True
    )

    class Meta:
        model = CollectionProduct
        fields = (
            'id',
            'product',
            'product_name',
            'product_price',
            'product_image',
            'order',
            'notes',
        )
        read_only_fields = ('id',)


class ProductCollectionSerializer(serializers.ModelSerializer):
    business_name = serializers.CharField(
        source='business.name',
        read_only=True
    )
    product_count = serializers.IntegerField(read_only=True)
    is_active_now = serializers.BooleanField(read_only=True)
    items = serializers.SerializerMethodField()

    class Meta:
        model = ProductCollection
        fields = (
            'id',
            'business',
            'business_name',
            'name',
            'slug',
            'description',
            'image',
            'banner_image',
            'starts_at',
            'ends_at',
            'is_active',
            'is_featured',
            'is_automated',
            'automation_rules',
            'order',
            'product_count',
            'is_active_now',
            'items',
            'created_at',
        )
        read_only_fields = (
            'id',
            'product_count',
            'is_active_now',
            'created_at',
        )

    def get_items(self, obj):
        products = obj.get_products()
        return ProductSerializer(
            products,
            many=True,
            context=self.context
        ).data