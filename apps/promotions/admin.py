from django.contrib import admin
from .models import Promotion


@admin.register(Promotion)
class PromotionAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'promotion_type', 'business',
                     'discount_type', 'discount_value', 'status',
                     'total_uses', 'usage_limit', 'is_valid_now_display')
    list_filter = ('promotion_type', 'discount_type', 'status', 'is_active')
    search_fields = ('name', 'code', 'business__name')

    fieldsets = (
        (None, {'fields': ('name', 'description', 'promotion_type', 'code',
                           'business', 'item', 'status', 'is_active')}),
        ('Discount', {'fields': ('discount_type', 'discount_value',
                                 'max_discount_amount', 'min_order_amount', 'min_nights')}),
        ('Limits', {'fields': ('usage_limit', 'per_user_limit', 'total_uses',
                               'total_discount_given')}),
        ('Schedule', {'fields': ('starts_at', 'ends_at')}),
    )
    readonly_fields = ('total_uses', 'total_discount_given')

    def is_valid_now_display(self, obj):
        return obj.is_valid_now
    is_valid_now_display.boolean = True
    is_valid_now_display.short_description = 'Live'