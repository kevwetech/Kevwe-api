from django.urls import path
from .views import (
    BusinessAnalyticsView,
    ProductAnalyticsView,
    PlatformAnalyticsView,
    CustomerAnalyticsView,
    TrackEventView,
    QuickStatsView,
    SearchAnalyticsView,
    CategoryAnalyticsView,
    DriverAnalyticsView,
    VendorPerformanceView,
    SubscriptionAnalyticsView,
    PromotionAnalyticsView,
    PromotionDetailView,
)

urlpatterns = [
    # Business analytics
    path('business/<int:business_id>/', BusinessAnalyticsView.as_view(), name='business_analytics'),
    path('business/<int:business_id>/generate/', BusinessAnalyticsView.as_view(), name='generate_business_analytics'),
    path('business/<int:business_id>/quick-stats/', QuickStatsView.as_view(), name='quick_stats'),

    # Product analytics
    path('business/<int:business_id>/products/<int:product_id>/', ProductAnalyticsView.as_view(), name='product_analytics'),

    # Category analytics
    path('business/<int:business_id>/categories/', CategoryAnalyticsView.as_view(), name='category_analytics'),

    # Vendor performance
    path('business/<int:business_id>/performance/', VendorPerformanceView.as_view(), name='vendor_performance'),

    # Platform analytics (admin)
    path('platform/', PlatformAnalyticsView.as_view(), name='platform_analytics'),

    # Customer analytics
    path('customer/', CustomerAnalyticsView.as_view(), name='customer_analytics'),

    # Driver analytics
    path('driver/', DriverAnalyticsView.as_view(), name='driver_analytics'),
    path('driver/<int:driver_id>/', DriverAnalyticsView.as_view(), name='driver_analytics_detail'),

    # Search analytics
    path('search/', SearchAnalyticsView.as_view(), name='search_analytics'),

    # Subscription analytics
    path('subscriptions/', SubscriptionAnalyticsView.as_view(), name='subscription_analytics'),

    # Promotions
    path('promotions/', PromotionAnalyticsView.as_view(), name='promotions'),
    path('promotions/<int:pk>/', PromotionDetailView.as_view(), name='promotion_detail'),

    # Event tracking
    path('track/', TrackEventView.as_view(), name='track_event'),
]