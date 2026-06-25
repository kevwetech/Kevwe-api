from django.contrib import admin
from .models import Currency, CurrencyRateHistory


@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = (
        'code', 'name', 'symbol', 'country',
        'rate_to_ngn', 'convert_from_ngn',
        'rate_source', 'preferred_currency',
        'is_default', 'is_active',
        'manual_override', 'rate_updated_at'
    )
    list_filter = (
        'is_active', 'is_default', 'preferred_currency',
        'manual_override', 'auto_update', 'rate_source'
    )
    search_fields = ('code', 'name', 'country')
    readonly_fields = (
        'convert_from_ngn', 'rate_updated_at',
        'created_at', 'updated_at'
    )


@admin.register(CurrencyRateHistory)
class CurrencyRateHistoryAdmin(admin.ModelAdmin):
    list_display = (
        'currency', 'rate_to_ngn', 'convert_from_ngn',
        'source', 'recorded_by', 'created_at'
    )
    list_filter = ('source', 'currency')
    search_fields = ('currency__code',)
    readonly_fields = ('created_at', 'updated_at')