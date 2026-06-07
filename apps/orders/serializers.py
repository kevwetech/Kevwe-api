from rest_framework import serializers
from .models import Cart, CartItem, Order, OrderItem
from apps.products.models import Product


class CartItemSerializer(serializers.ModelSerializer):
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
        source='product.image',
        read_only=True
    )
    subtotal = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True
    )

    class Meta:
        model = CartItem
        fields = (
            'id',
            'product',
            'product_name',
            'product_price',
            'product_image',
            'quantity',
            'subtotal',
        )


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True
    )
    total_items = serializers.IntegerField(read_only=True)

    class Meta:
        model = Cart
        fields = (
            'id',
            'items',
            'total_items',
            'total',
        )


class AddToCartSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1, default=1)

    def validate_product_id(self, value):
        try:
            Product.objects.get(pk=value, is_active=True)
        except Product.DoesNotExist:
            raise serializers.ValidationError('Product not found')
        return value


class UpdateCartItemSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1)


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = (
            'id',
            'product',
            'product_name',
            'product_price',
            'quantity',
            'subtotal',
        )


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = (
            'id',
            'reference',
            'status',
            'payment_status',
            'shipping_address',
            'shipping_city',
            'shipping_state',
            'shipping_country',
            'phone',
            'subtotal',
            'shipping_fee',
            'total',
            'notes',
            'items',
            'created_at',
            'updated_at',
        )
        read_only_fields = (
            'id',
            'reference',
            'status',
            'payment_status',
            'subtotal',
            'shipping_fee',
            'total',
            'created_at',
            'updated_at',
        )


class CreateOrderSerializer(serializers.Serializer):
    shipping_address = serializers.CharField()
    shipping_city = serializers.CharField()
    shipping_state = serializers.CharField()
    shipping_country = serializers.CharField(default='Nigeria')
    phone = serializers.CharField()
    notes = serializers.CharField(required=False, allow_blank=True)