from rest_framework import serializers
from .models import Wallet, WalletTransaction, BankAccount, WithdrawalRequest


class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = (
            'id',
            'balance',
            'total_credited',
            'total_debited',
            'is_active',
            'is_pin_set',
            'created_at',
        )
        read_only_fields = (
            'id',
            'balance',
            'total_credited',
            'total_debited',
            'created_at',
        )


class WalletTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WalletTransaction
        fields = (
            'id',
            'transaction_type',
            'category',
            'amount',
            'balance_after',
            'description',
            'reference',
            'status',
            'metadata',
            'created_at',
        )
        read_only_fields = ('id', 'created_at')


class BankAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankAccount
        fields = (
            'id',
            'bank_name',
            'bank_code',
            'account_number',
            'account_name',
            'is_default',
            'is_verified',
            'created_at',
        )
        read_only_fields = (
            'id',
            'is_verified',
            'created_at',
        )


class WithdrawalRequestSerializer(serializers.ModelSerializer):
    bank_account_details = BankAccountSerializer(
        source='bank_account',
        read_only=True
    )

    class Meta:
        model = WithdrawalRequest
        fields = (
            'id',
            'amount',
            'fee',
            'net_amount',
            'reference',
            'status',
            'bank_account_details',
            'gateway_reference',
            'notes',
            'created_at',
        )
        read_only_fields = (
            'id',
            'fee',
            'net_amount',
            'reference',
            'status',
            'gateway_reference',
            'created_at',
        )


class TopUpSerializer(serializers.Serializer):
    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=100
    )
    gateway = serializers.ChoiceField(
        choices=['paystack', 'flutterwave'],
        default='paystack'
    )
    callback_url = serializers.URLField(required=False)


class PayWithWalletSerializer(serializers.Serializer):
    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2
    )
    description = serializers.CharField()
    payment_for = serializers.ChoiceField(
        choices=['order', 'booking', 'ride', 'shipment', 'delivery', 'subscription']
    )
    object_id = serializers.IntegerField()
    pin = serializers.CharField(
        max_length=6,
        required=False
    )


class TransferSerializer(serializers.Serializer):
    recipient_email = serializers.EmailField()
    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=100
    )
    description = serializers.CharField(
        required=False,
        allow_blank=True
    )
    pin = serializers.CharField(max_length=6)


class WithdrawalSerializer(serializers.Serializer):
    bank_account_id = serializers.IntegerField()
    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=500
    )
    pin = serializers.CharField(max_length=6)


class SetPinSerializer(serializers.Serializer):
    pin = serializers.CharField(max_length=6, min_length=4)
    confirm_pin = serializers.CharField(max_length=6, min_length=4)

    def validate(self, attrs):
        if attrs['pin'] != attrs['confirm_pin']:
            raise serializers.ValidationError(
                {'pin': 'PINs do not match'}
            )
        if not attrs['pin'].isdigit():
            raise serializers.ValidationError(
                {'pin': 'PIN must be numeric'}
            )
        return attrs


class ChangePinSerializer(serializers.Serializer):
    old_pin = serializers.CharField(max_length=6)
    new_pin = serializers.CharField(max_length=6, min_length=4)
    confirm_pin = serializers.CharField(max_length=6)

    def validate(self, attrs):
        if attrs['new_pin'] != attrs['confirm_pin']:
            raise serializers.ValidationError(
                {'pin': 'New PINs do not match'}
            )
        if not attrs['new_pin'].isdigit():
            raise serializers.ValidationError(
                {'pin': 'PIN must be numeric'}
            )
        return attrs