from rest_framework import serializers
from .models import( 
    Wallet, 
    WalletTransaction, 
    BankAccount, 
    WithdrawalRequest, 
    VendorWallet, 
    VendorTransaction,
    VendorWithdrawalRequest,
    EarningsSummary,
    BankAccount,
)


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
        extra_kwargs = {
            'account_name': {'required': False, 'allow_blank': True}
        }


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



class VendorWalletSerializer(serializers.ModelSerializer):
    business_name = serializers.CharField(
        source='business.name',
        read_only=True
    )
    total_balance = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True
    )
    default_bank = serializers.SerializerMethodField()

    class Meta:
        model = VendorWallet
        fields = (
            'id',
            'business',
            'business_name',
            'user',
            'available_balance',
            'pending_balance',
            'reserved_balance',
            'total_balance',
            'total_earned',
            'total_withdrawn',
            'total_refunded',
            'settlement_period_days',
            'auto_withdraw',
            'auto_withdraw_threshold',
            'default_bank',
            'status',
            'created_at',
        )
        read_only_fields = (
            'id',
            'user',
            'total_balance',
            'total_earned',
            'total_withdrawn',
            'total_refunded',
            'created_at',
        )

    def get_default_bank(self, obj):
        if obj.default_bank_account:
            return {
                'id': obj.default_bank_account.id,
                'bank_name': obj.default_bank_account.bank_name,
                'account_number': obj.default_bank_account.account_number,
                'account_name': obj.default_bank_account.account_name,
            }
        return None


class VendorTransactionSerializer(serializers.ModelSerializer):
    business_name = serializers.CharField(
        source='vendor_wallet.business.name',
        read_only=True
    )
    order_number = serializers.CharField(
        source='order.order_number',
        read_only=True
    )
    booking_number = serializers.CharField(
        source='booking.booking_number',
        read_only=True
    )

    class Meta:
        model = VendorTransaction
        fields = (
            'id',
            'vendor_wallet',
            'business_name',
            'transaction_type',
            'amount',
            'available_balance_after',
            'pending_balance_after',
            'description',
            'reference',
            'order',
            'order_number',
            'booking',
            'booking_number',
            'settlement_due',
            'settled_at',
            'status',
            'created_at',
        )
        read_only_fields = ('id', 'created_at')


class VendorWithdrawalRequestSerializer(
    serializers.ModelSerializer
):
    vendor_name = serializers.CharField(
        source='vendor.full_name',
        read_only=True
    )
    business_name = serializers.CharField(
        source='business.name',
        read_only=True
    )
    bank_name = serializers.CharField(
        source='bank_account.bank_name',
        read_only=True
    )
    account_number = serializers.CharField(
        source='bank_account.account_number',
        read_only=True
    )
    account_name = serializers.CharField(
        source='bank_account.account_name',
        read_only=True
    )
    reviewed_by_name = serializers.CharField(
        source='reviewed_by.full_name',
        read_only=True
    )
    approved_by_name = serializers.CharField(
        source='approved_by.full_name',
        read_only=True
    )
    rejected_by_name = serializers.CharField(
        source='rejected_by.full_name',
        read_only=True
    )
    is_cancellable = serializers.BooleanField(
        read_only=True
    )
    available_balance = serializers.DecimalField(
        source='vendor_wallet.available_balance',
        max_digits=12,
        decimal_places=2,
        read_only=True
    )

    class Meta:
        model = VendorWithdrawalRequest
        fields = (
            'id',
            'vendor',
            'vendor_name',
            'business',
            'business_name',
            'vendor_wallet',
            'bank_account',
            'bank_name',
            'account_number',
            'account_name',
            'available_balance',
            'amount',
            'fee',
            'net_amount',
            'reference',
            'gateway_reference',
            'status',
            'reviewed_by',
            'reviewed_by_name',
            'reviewed_at',
            'approved_by',
            'approved_by_name',
            'approved_at',
            'rejection_reason',
            'rejection_notes',
            'rejected_by',
            'rejected_by_name',
            'rejected_at',
            'processed_at',
            'completed_at',
            'failure_reason',
            'is_cancellable',
            'notes',
            'created_at',
        )
        read_only_fields = (
            'id',
            'vendor',
            'reference',
            'fee',
            'net_amount',
            'status',
            'reviewed_by',
            'reviewed_at',
            'approved_by',
            'approved_at',
            'rejected_by',
            'rejected_at',
            'processed_at',
            'completed_at',
            'is_cancellable',
            'created_at',
        )


class CreateWithdrawalSerializer(serializers.Serializer):
    business_id     = serializers.IntegerField()
    bank_account_id = serializers.IntegerField()
    amount          = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=1000
    )
    gateway = serializers.ChoiceField(
        choices=['paystack', 'flutterwave'],
        default='paystack'
    )
    notes = serializers.CharField(
        required=False,
        allow_blank=True
    )

    def validate_amount(self, value):
        from decimal import Decimal
        if value < Decimal('1000'):
            raise serializers.ValidationError(
                'Minimum withdrawal amount is ₦1,000'
            )
        return value


class EarningsSummarySerializer(serializers.ModelSerializer):
    business_name = serializers.CharField(
        source='vendor_wallet.business.name',
        read_only=True
    )

    class Meta:
        model = EarningsSummary
        fields = (
            'id',
            'vendor_wallet',
            'business_name',
            'period',
            'period_start',
            'period_end',
            'total_orders',
            'total_bookings',
            'gross_earnings',
            'platform_commission',
            'net_earnings',
            'refunds',
            'adjustments',
            'final_earnings',
            'total_withdrawn',
            'pending_withdrawal',
            'created_at',
        )
        read_only_fields = ('id', 'created_at')