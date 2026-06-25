from rest_framework import serializers
from .models import Currency, CurrencyRateHistory


class CurrencyRateHistorySerializer(serializers.ModelSerializer):
    currency_code = serializers.CharField(
        source='currency.code', read_only=True
    )
    recorded_by_name = serializers.CharField(
        source='recorded_by.full_name', read_only=True
    )

    class Meta:
        model = CurrencyRateHistory
        fields = (
            'id',
            'currency',
            'currency_code',
            'rate_to_ngn',
            'convert_from_ngn',
            'source',
            'recorded_by',
            'recorded_by_name',
            'note',
            'created_at',
        )
        read_only_fields = ('id', 'created_at')


class CurrencySerializer(serializers.ModelSerializer):
    class Meta:
        model = Currency
        fields = (
            'id',
            'code',
            'name',
            'symbol',
            'country',
            'rate_to_ngn',
            'convert_from_ngn',
            'preferred_currency',
            'rate_source',
            'is_active',
            'is_default',
            'auto_update',
            'manual_override',
            'rate_updated_at',
            'created_at',
            'updated_at',
        )
        read_only_fields = (
            'id',
            'convert_from_ngn',
            'rate_updated_at',
            'created_at',
            'updated_at',
        )