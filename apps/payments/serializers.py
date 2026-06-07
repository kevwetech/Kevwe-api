from rest_framework import serializers
from .models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = (
            'id',
            'reference',
            'gateway',
            'gateway_reference',
            'status',
            'payment_for',
            'object_id',
            'amount',
            'currency',
            'metadata',
            'failure_reason',
            'created_at',
            'updated_at',
        )
        read_only_fields = (
            'id',
            'reference',
            'gateway_reference',
            'status',
            'created_at',
            'updated_at',
        )


class InitializePaymentSerializer(serializers.Serializer):
    payment_for = serializers.ChoiceField(
        choices=['order', 'booking', 'ride', 'shipment', 'wallet']
    )
    object_id = serializers.IntegerField()
    gateway = serializers.ChoiceField(
        choices=['paystack', 'flutterwave'],
        default='paystack'
    )
    callback_url = serializers.URLField(required=False)
    redirect_url = serializers.URLField(required=False)


class VerifyPaymentSerializer(serializers.Serializer):
    reference = serializers.CharField()
    gateway = serializers.ChoiceField(
        choices=['paystack', 'flutterwave'],
        default='paystack'
    )
    transaction_id = serializers.CharField(required=False)


class RefundPaymentSerializer(serializers.Serializer):
    reference = serializers.CharField()
    gateway = serializers.ChoiceField(
        choices=['paystack', 'flutterwave']
    )
    amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False
    )
    transaction_id = serializers.CharField(required=False)