from rest_framework import serializers
from .models import (
    BusinessAnalytics,
    ProductAnalytics,
    PlatformAnalytics,
    CustomerAnalytics,
    AnalyticsEvent,
    SearchAnalytics,
    CategoryAnalytics,
    DriverAnalytics,
    VendorPerformance,
    SubscriptionAnalytics,
    PromotionAnalytics,
)


class BusinessAnalyticsSerializer(serializers.ModelSerializer):
    business_name = serializers.CharField(
        source='business.name',
        read_only=True
    )

    class Meta:
        model = BusinessAnalytics
        fields = (
            'id',
            'business',
            'business_name',
            'date',
            'total_orders',
            'completed_orders',
            'cancelled_orders',
            'pending_orders',
            'completion_rate',
            'gross_revenue',
            'net_revenue',
            'delivery_revenue',
            'refunds',
            'platform_commission',
            'total_customers',
            'new_customers',
            'returning_customers',
            'total_items_sold',
            'top_products',
            'avg_order_value',
            'avg_preparation_time',
            'avg_delivery_time',
            'avg_rating',
            'total_reviews',
            'profile_views',
            'catalog_views',
            'created_at',
        )
        read_only_fields = ('id', 'created_at')


class ProductAnalyticsSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(
        source='product.name',
        read_only=True
    )
    business_name = serializers.CharField(
        source='business.name',
        read_only=True
    )

    class Meta:
        model = ProductAnalytics
        fields = (
            'id',
            'product',
            'product_name',
            'business',
            'business_name',
            'date',
            'units_sold',
            'revenue',
            'refunds',
            'cart_adds',
            'cart_removals',
            'conversion_rate',
            'views',
            'avg_rating',
            'new_reviews',
            'created_at',
        )
        read_only_fields = ('id', 'created_at')


class PlatformAnalyticsSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlatformAnalytics
        fields = '__all__'
        read_only_fields = ('id', 'created_at')


class CustomerAnalyticsSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(
        source='user.full_name',
        read_only=True
    )
    user_email = serializers.CharField(
        source='user.email',
        read_only=True
    )

    class Meta:
        model = CustomerAnalytics
        fields = (
            'id',
            'user',
            'user_name',
            'user_email',
            'date',
            'total_orders',
            'completed_orders',
            'cancelled_orders',
            'total_spent',
            'avg_order_value',
            'favorite_businesses',
            'favorite_products',
            'created_at',
        )
        read_only_fields = ('id', 'created_at')


class AnalyticsEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalyticsEvent
        fields = (
            'id',
            'user',
            'event_type',
            'object_type',
            'object_id',
            'session_id',
            'device_type',
            'metadata',
            'created_at',
        )
        read_only_fields = ('id', 'created_at')

class SearchAnalyticsSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(
        source='user.full_name',
        read_only=True
    )
    business_name = serializers.CharField(
        source='business.name',
        read_only=True
    )

    class Meta:
        model = SearchAnalytics
        fields = (
            'id',
            'user',
            'user_name',
            'query',
            'results_count',
            'clicked_result_id',
            'clicked_result_type',
            'business',
            'business_name',
            'converted',
            'ip_address',
            'device_type',
            'date',
            'created_at',
        )
        read_only_fields = ('id', 'created_at')


class CategoryAnalyticsSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(
        source='category.name',
        read_only=True
    )
    category_path = serializers.CharField(
        source='category.full_path',
        read_only=True
    )
    business_name = serializers.CharField(
        source='business.name',
        read_only=True
    )

    class Meta:
        model = CategoryAnalytics
        fields = (
            'id',
            'category',
            'category_name',
            'category_path',
            'business',
            'business_name',
            'date',
            'views',
            'unique_visitors',
            'total_orders',
            'units_sold',
            'revenue',
            'total_products',
            'active_products',
            'top_product_id',
            'top_product_name',
            'add_to_cart_count',
            'conversion_rate',
            'avg_rating',
            'created_at',
        )
        read_only_fields = ('id', 'created_at')


class DriverAnalyticsSerializer(serializers.ModelSerializer):
    driver_name = serializers.SerializerMethodField()
    earnings_per_hour = serializers.FloatField(read_only=True)

    class Meta:
        model = DriverAnalytics
        fields = (
            'id',
            'driver',
            'driver_name',
            'date',
            'total_deliveries',
            'completed_deliveries',
            'cancelled_deliveries',
            'failed_deliveries',
            'completion_rate',
            'total_rides',
            'completed_rides',
            'cancelled_rides',
            'delivery_earnings',
            'ride_earnings',
            'bonus_earnings',
            'total_earnings',
            'tips',
            'avg_delivery_time',
            'avg_pickup_time',
            'total_distance_km',
            'online_hours',
            'earnings_per_hour',
            'avg_rating',
            'total_ratings',
            'new_ratings',
            'late_deliveries',
            'complaints',
            'created_at',
        )
        read_only_fields = ('id', 'earnings_per_hour', 'created_at')

    def get_driver_name(self, obj):
        try:
            return obj.driver.user.full_name
        except Exception:
            return None


class VendorPerformanceSerializer(serializers.ModelSerializer):
    business_name = serializers.CharField(
        source='business.name',
        read_only=True
    )

    class Meta:
        model = VendorPerformance
        fields = (
            'id',
            'business',
            'business_name',
            'period',
            'period_start',
            'period_end',
            'order_completion_score',
            'rating_score',
            'response_time_score',
            'cancellation_score',
            'preparation_time_score',
            'overall_score',
            'performance_tier',
            'total_orders',
            'completed_orders',
            'cancelled_orders',
            'avg_rating',
            'total_revenue',
            'bonus_earned',
            'commission_discount',
            'rank',
            'created_at',
        )
        read_only_fields = (
            'id',
            'overall_score',
            'performance_tier',
            'commission_discount',
            'created_at',
        )


class SubscriptionAnalyticsSerializer(serializers.ModelSerializer):
    net_new_mrr = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True
    )

    class Meta:
        model = SubscriptionAnalytics
        fields = (
            'id',
            'date',
            'total_subscribers',
            'new_subscribers',
            'churned_subscribers',
            'reactivated_subscribers',
            'mrr',
            'arr',
            'new_mrr',
            'churned_mrr',
            'expansion_mrr',
            'net_new_mrr',
            'churn_rate',
            'growth_rate',
            'plan_breakdown',
            'trial_starts',
            'trial_conversions',
            'trial_conversion_rate',
            'created_at',
        )
        read_only_fields = ('id', 'net_new_mrr', 'created_at')


class PromotionAnalyticsSerializer(serializers.ModelSerializer):
    business_name = serializers.CharField(
        source='business.name',
        read_only=True
    )
    created_by_name = serializers.CharField(
        source='created_by.full_name',
        read_only=True
    )
    is_valid_now = serializers.BooleanField(read_only=True)
    usage_percentage = serializers.FloatField(read_only=True)

    class Meta:
        model = PromotionAnalytics
        fields = (
            'id',
            'name',
            'promotion_type',
            'code',
            'business',
            'business_name',
            'discount_type',
            'discount_value',
            'min_order_amount',
            'max_discount_amount',
            'usage_limit',
            'per_user_limit',
            'starts_at',
            'ends_at',
            'total_uses',
            'unique_users',
            'total_discount_given',
            'total_revenue_generated',
            'total_orders',
            'avg_order_value',
            'roi',
            'new_customer_uses',
            'returning_customer_uses',
            'is_active',
            'is_valid_now',
            'usage_percentage',
            'created_by',
            'created_by_name',
            'created_at',
        )
        read_only_fields = (
            'id',
            'total_uses',
            'unique_users',
            'total_discount_given',
            'total_revenue_generated',
            'total_orders',
            'avg_order_value',
            'roi',
            'new_customer_uses',
            'returning_customer_uses',
            'is_valid_now',
            'usage_percentage',
            'created_at',
        )