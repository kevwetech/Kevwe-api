from rest_framework import serializers
from .models import Cart, CartItem, Order, OrderItem, OrderTracking
from apps.catalog.serializers import ProductSerializer


class CartItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(
        source='product.name',
        read_only=True
    )
    product_image = serializers.ImageField(
        source='product.cover_image',
        read_only=True
    )
    variant_name = serializers.CharField(
        source='variant.name',
        read_only=True
    )
    variant_price = serializers.DecimalField(
        source='variant.price',
        max_digits=10,
        decimal_places=2,
        read_only=True
    )
    item_price = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True
    )
    subtotal = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True
    )
    business_name = serializers.CharField(
        source='cart.business.name',
        read_only=True
    )

    class Meta:
        model = CartItem
        fields = (
            'id',
            'product',
            'product_name',
            'product_image',
            'variant',
            'variant_name',
            'variant_price',
            'quantity',
            'item_price',
            'addon_price',
            'subtotal',
            'selected_addons',
            'special_instructions',
            'business_name',
            'created_at',
        )
        read_only_fields = (
            'id',
            'item_price',
            'subtotal',
            'created_at',
        )


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True
    )
    total_items = serializers.IntegerField(read_only=True)
    business_name = serializers.CharField(
        source='business.name',
        read_only=True
    )
    business_logo = serializers.ImageField(
        source='business.logo',
        read_only=True
    )
    delivery_fee = serializers.DecimalField(
        source='business.delivery_fee',
        max_digits=10,
        decimal_places=2,
        read_only=True
    )
    min_order_amount = serializers.DecimalField(
        source='business.min_order_amount',
        max_digits=10,
        decimal_places=2,
        read_only=True
    )

    class Meta:
        model = Cart
        fields = (
            'id',
            'business',
            'business_name',
            'business_logo',
            'delivery_fee',
            'min_order_amount',
            'items',
            'total',
            'total_items',
            'created_at',
        )
        read_only_fields = (
            'id',
            'total',
            'total_items',
            'created_at',
        )


class AddToCartSerializer(serializers.Serializer):
    business_id = serializers.IntegerField()
    product_id = serializers.IntegerField()
    variant_id = serializers.IntegerField(required=False, allow_null=True)
    quantity = serializers.IntegerField(default=1, min_value=1)
    selected_addons = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        default=list
    )
    special_instructions = serializers.CharField(
        required=False,
        allow_blank=True
    )


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = (
            'id',
            'product',
            'variant',
            'product_name',
            'variant_name',
            'product_image',
            'unit_price',
            'addon_price',
            'quantity',
            'subtotal',
            'selected_addons',
            'special_instructions',
            'is_available',
            'unavailability_reason',
        )
        read_only_fields = ('id', 'subtotal')


class OrderTrackingSerializer(serializers.ModelSerializer):
    updated_by_name = serializers.CharField(
        source='updated_by.full_name',
        read_only=True
    )

    class Meta:
        model = OrderTracking
        fields = (
            'id',
            'status',
            'description',
            'location',
            'latitude',
            'longitude',
            'updated_by',
            'updated_by_name',
            'created_at',
        )
        read_only_fields = ('id', 'created_at')


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    tracking = OrderTrackingSerializer(many=True, read_only=True)
    user_name = serializers.CharField(
        source='user.full_name',
        read_only=True
    )
    user_phone = serializers.CharField(
        source='user.phone',
        read_only=True
    )
    business_name = serializers.CharField(
        source='business.name',
        read_only=True
    )
    business_logo = serializers.ImageField(
        source='business.logo',
        read_only=True
    )
    driver_name = serializers.CharField(
        source='driver.user.full_name',
        read_only=True
    )
    driver_phone = serializers.CharField(
        source='driver.user.phone',
        read_only=True
    )
    total_items = serializers.SerializerMethodField()
    delivery_info = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = (
            'id',
            'user',
            'user_name',
            'user_phone',
            'business',
            'business_name',
            'business_logo',
            'reference',
            'order_number',
            'order_type',
            'status',
            'payment_status',
            'payment_method',
            'delivery_address_ref',
            'delivery_name',
            'delivery_phone',
            'delivery_address',
            'delivery_city',
            'delivery_state',
            'delivery_lat',
            'delivery_lng',
            'driver',
            'driver_name',
            'driver_phone',
            'subtotal',
            'delivery_fee',
            'discount_amount',
            'tax_amount',
            'total',
            'platform_commission',
            'business_earnings',
            'driver_earnings',
            'estimated_delivery_time',
            'scheduled_time',
            'confirmed_at',
            'preparing_at',
            'ready_at',
            'picked_up_at',
            'delivered_at',
            'cancelled_at',
            'cancellation_reason',
            'rating',
            'review',
            'special_instructions',
            'delivery_info',
            'notes',
            'items',
            'tracking',
            'total_items',
            'created_at',
        )
        read_only_fields = (
            'id',
            'reference',
            'order_number',
            'subtotal',
            'total',
            'platform_commission',
            'business_earnings',
            'driver_earnings',
            'confirmed_at',
            'preparing_at',
            'ready_at',
            'picked_up_at',
            'delivered_at',
            'cancelled_at',
            'created_at',
        )

    def get_total_items(self, obj):
        return obj.items.count()

    def get_delivery_info(self, obj):
        if hasattr(obj, 'delivery') and obj.delivery:
            d = obj.delivery
            return {
                'id': d.id,
                'tracking_number': d.tracking_number,
                'status': d.status,
                'dispatcher_name': (
                    d.driver.user.full_name
                    if d.driver else None
                ),
                'dispatcher_phone': (
                    d.driver.user.phone
                    if d.driver else None
                ),
            }
        return None


class CreateOrderSerializer(serializers.Serializer):
    order_type = serializers.ChoiceField(
        choices=[
            'delivery', 'pickup',
            'dine_in', 'service', 'digital'
        ],
        default='delivery'
    )
    payment_method = serializers.ChoiceField(
        choices=[
            'wallet', 'paystack',
            'flutterwave', 'cash', 'transfer'
        ],
        default='wallet'
    )
    # Option C address
    delivery_address_id = serializers.IntegerField(required=False)
    delivery_name = serializers.CharField(
        required=False,
        allow_blank=True
    )
    delivery_phone = serializers.CharField(
        required=False,
        allow_blank=True
    )
    delivery_address = serializers.CharField(
        required=False,
        allow_blank=True
    )
    delivery_city = serializers.CharField(
        required=False,
        allow_blank=True
    )
    delivery_state = serializers.CharField(
        required=False,
        allow_blank=True
    )
    delivery_lat = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        required=False
    )
    delivery_lng = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        required=False
    )
    city_id = serializers.IntegerField(required=False)
    zone_id = serializers.IntegerField(required=False)
    scheduled_time = serializers.DateTimeField(required=False)
    special_instructions = serializers.CharField(
        required=False,
        allow_blank=True
    )
    notes = serializers.CharField(
        required=False,
        allow_blank=True
    )

    def validate(self, data):
        if data.get('order_type') == 'delivery':
            if not data.get('delivery_address_id'):
                if not data.get('delivery_address'):
                    raise serializers.ValidationError(
                        'delivery_address is required for delivery orders'
                    )
                if not data.get('delivery_name'):
                    raise serializers.ValidationError(
                        'delivery_name is required for delivery orders'
                    )
                if not data.get('delivery_phone'):
                    raise serializers.ValidationError(
                        'delivery_phone is required for delivery orders'
                    )
        return data


class RateOrderSerializer(serializers.Serializer):
    rating = serializers.IntegerField(min_value=1, max_value=5)
    review = serializers.CharField(
        required=False,
        allow_blank=True
    )