from django.contrib import admin
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


@admin.register(SearchAnalytics)
class SearchAnalyticsAdmin(admin.ModelAdmin):
    list_display = (
        'query', 'results_count', 'converted',
        'device_type', 'date', 'created_at'
    )
    list_filter = ('converted', 'device_type', 'date')
    search_fields = ('query',)
    ordering = ('-created_at',)


@admin.register(CategoryAnalytics)
class CategoryAnalyticsAdmin(admin.ModelAdmin):
    list_display = (
        'category', 'business', 'date',
        'views', 'units_sold', 'revenue'
    )
    list_filter = ('date',)
    search_fields = ('category__name', 'business__name')
    ordering = ('-date',)


@admin.register(DriverAnalytics)
class DriverAnalyticsAdmin(admin.ModelAdmin):
    list_display = (
        'driver', 'date', 'total_deliveries',
        'total_earnings', 'avg_rating',
        'completion_rate'
    )
    list_filter = ('date',)
    ordering = ('-date',)


@admin.register(VendorPerformance)
class VendorPerformanceAdmin(admin.ModelAdmin):
    list_display = (
        'business', 'period', 'period_start',
        'overall_score', 'performance_tier',
        'rank', 'commission_discount'
    )
    list_filter = ('period', 'performance_tier')
    search_fields = ('business__name',)
    ordering = ('-period_start',)


@admin.register(SubscriptionAnalytics)
class SubscriptionAnalyticsAdmin(admin.ModelAdmin):
    list_display = (
        'date', 'total_subscribers', 'mrr',
        'arr', 'churn_rate', 'growth_rate'
    )
    ordering = ('-date',)


@admin.register(PromotionAnalytics)
class PromotionAnalyticsAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'promotion_type', 'code',
        'business', 'total_uses',
        'total_discount_given',
        'total_revenue_generated',
        'roi', 'is_active'
    )
    list_filter = ('promotion_type', 'is_active')
    search_fields = ('name', 'code', 'business__name')
    ordering = ('-created_at',)