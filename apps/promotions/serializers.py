from rest_framework import serializers
from .models import Promotion


class PromotionSerializer(serializers.ModelSerializer):
    is_valid_now = serializers.ReadOnlyField()
    usage_percentage = serializers.ReadOnlyField()
    promotion_type_display = serializers.CharField(
        source='get_promotion_type_display', read_only=True)

    class Meta:
        model = Promotion
        fields = [
            'id', 'name', 'description', 'promotion_type', 'promotion_type_display',
            'code', 'business', 'item', 'min_nights',
            'discount_type', 'discount_value', 'max_discount_amount', 'min_order_amount',
            'usage_limit', 'per_user_limit', 'total_uses', 'usage_percentage',
            'starts_at', 'ends_at', 'status', 'is_active', 'is_valid_now',
        ]
        read_only_fields = ['total_uses', 'total_discount_given']


class PromotionValidateSerializer(serializers.Serializer):
    '''What checkout posts to redeem a code.'''
    code = serializers.CharField(max_length=50)
    business_id = serializers.IntegerField(required=False)
    order_amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False)

    def validate(self, data):
        qs = Promotion.objects.filter(code__iexact=data['code'])
        if data.get('business_id'):
            from django.db.models import Q
            qs = qs.filter(Q(business_id=data['business_id']) | Q(business__isnull=True))

        promo = qs.first()
        if not promo:
            raise serializers.ValidationError({'code': 'No such promotion code.'})
        if not promo.is_valid_now:
            raise serializers.ValidationError({'code': 'This code is no longer valid.'})

        order_amount = data.get('order_amount')
        if order_amount is not None and promo.min_order_amount and order_amount < promo.min_order_amount:
            raise serializers.ValidationError({
                'order_amount': f'Minimum order amount is {promo.min_order_amount}.'
            })

        data['promotion'] = promo
        return data