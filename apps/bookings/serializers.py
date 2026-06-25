from rest_framework import serializers
from .models import (
    BookableItem,
    BookableItemAvailability,
    BookingPolicy,
    Booking,
    BookingTracking,
    BookingAddOn,
    BookingPayment,
    BookingGuest,
    BookingCoupon,
    CouponUsage,
    BookingInvoice,
    BookingReminder,
)


class BookingPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = BookingPolicy
        fields = (
            'id',
            'item',
            'booking_mode',
            'slots_per_day',
            'slot_duration_minutes',
            'slots_start_time',
            'slots_end_time',
            'break_between_slots',
            'total_seats',
            'allow_same_day_checkout_checkin',
            'buffer_hours',
            'free_cancellation_hours',
            'cancellation_fee_percentage',
            'created_at',
        )
        read_only_fields = ('id', 'created_at')


class BookableItemAvailabilitySerializer(
    serializers.ModelSerializer
):
    class Meta:
        model = BookableItemAvailability
        fields = (
            'id',
            'item',
            'date',
            'is_available',
            'custom_price',
            'notes',
        )
        read_only_fields = ('id',)


class BookableItemSerializer(serializers.ModelSerializer):
    business_name = serializers.CharField(
        source='business.name',
        read_only=True
    )
    category_name = serializers.CharField(
        source='category.name',
        read_only=True
    )
    policy = BookingPolicySerializer(read_only=True)
    effective_commission_rate = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        read_only=True
    )

    class Meta:
        model = BookableItem
        fields = (
            'id',
            'business',
            'business_name',
            'category',
            'category_name',
            'name',
            'slug',
            'description',
            'short_description',
            'item_type',
            'price_per_unit',
            'unit_label',
            'min_units',
            'max_units',
            'capacity',
            'image',
            'images',
            'is_available',
            'is_active',
            'status',
            'advance_booking_days',
            'max_advance_booking_days',
            'cancellation_hours',
            'auto_confirm',
            'location',
            'floor',
            'amenities',
            'tags',
            'total_bookings',
            'total_revenue',
            'rating',
            'total_ratings',
            'is_featured',
            'order',
            'policy',
            'effective_commission_rate',
            'created_at',
        )
        read_only_fields = (
            'id',
            'total_bookings',
            'total_revenue',
            'rating',
            'total_ratings',
            'effective_commission_rate',
            'created_at',
        )


class BookingAddOnSerializer(serializers.ModelSerializer):
    class Meta:
        model = BookingAddOn
        fields = (
            'id',
            'name',
            'price',
            'quantity',
            'subtotal',
            'notes',
        )
        read_only_fields = ('id', 'subtotal')


class BookingTrackingSerializer(serializers.ModelSerializer):
    updated_by_name = serializers.CharField(
        source='updated_by.full_name',
        read_only=True
    )

    class Meta:
        model = BookingTracking
        fields = (
            'id',
            'status',
            'description',
            'updated_by',
            'updated_by_name',
            'created_at',
        )
        read_only_fields = ('id', 'created_at')


class BookingSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(
        source='user.full_name',
        read_only=True
    )
    user_phone = serializers.CharField(
        source='user.phone',
        read_only=True
    )
    business_name = serializers.CharField(
        source='business.name',
        read_only=True
    )
    item_name = serializers.CharField(
        source='item.name',
        read_only=True
    )
    item_type = serializers.CharField(
        source='item.item_type',
        read_only=True
    )
    tracking = BookingTrackingSerializer(
        many=True,
        read_only=True
    )
    addons = BookingAddOnSerializer(
        many=True,
        read_only=True
    )
    booking_mode = serializers.CharField(
        source='item.policy.booking_mode',
        read_only=True
    )

    class Meta:
        model = Booking
        fields = (
            'id',
            'user',
            'user_name',
            'user_phone',
            'business',
            'business_name',
            'item',
            'item_name',
            'item_type',
            'booking_mode',
            'reference',
            'booking_number',
            'status',
            'payment_status',
            'payment_method',
            'check_in',
            'check_out',
            'check_in_time',
            'check_out_time',
            'duration',
            'actual_check_in',
            'actual_check_out',
            'guests',
            'guest_name',
            'guest_email',
            'guest_phone',
            'guest_id_type',
            'guest_id_number',
            'price_per_unit',
            'subtotal',
            'discount_amount',
            'tax_amount',
            'total',
            'platform_commission',
            'business_earnings',
            'special_requests',
            'notes',
            'cancelled_at',
            'cancellation_reason',
            'rating',
            'review',
            'rated_at',
            'tracking',
            'addons',
            'created_at',
        )
        read_only_fields = (
            'id',
            'reference',
            'booking_number',
            'subtotal',
            'platform_commission',
            'business_earnings',
            'cancelled_at',
            'rated_at',
            'created_at',
        )


class CreateBookingSerializer(serializers.Serializer):
    item_id = serializers.IntegerField()
    check_in = serializers.DateField()
    check_out = serializers.DateField()
    check_in_time = serializers.TimeField(required=False)
    guests = serializers.IntegerField(default=1)
    guest_name = serializers.CharField()
    guest_email = serializers.EmailField()
    guest_phone = serializers.CharField()
    guest_id_type = serializers.CharField(
        required=False,
        allow_blank=True
    )
    guest_id_number = serializers.CharField(
        required=False,
        allow_blank=True
    )
    payment_method = serializers.ChoiceField(
        choices=[
            'wallet', 'paystack',
            'flutterwave', 'cash', 'transfer'
        ],
        default='wallet'
    )
    special_requests = serializers.CharField(
        required=False,
        allow_blank=True
    )
    addons = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        default=list
    )

    def validate(self, data):
        from datetime import date
        if data['check_in'] < date.today():
            raise serializers.ValidationError(
                'Check-in date cannot be in the past'
            )
        if data['check_out'] <= data['check_in']:
            raise serializers.ValidationError(
                'Check-out must be after check-in'
            )
        return data


class CheckAvailabilitySerializer(serializers.Serializer):
    item_id = serializers.IntegerField()
    check_in = serializers.DateField()
    check_out = serializers.DateField()
    guests = serializers.IntegerField(default=1)


class BookingPaymentSerializer(serializers.ModelSerializer):
    paid_by_name = serializers.CharField(
        source='paid_by.full_name',
        read_only=True
    )
    booking_number = serializers.CharField(
        source='booking.booking_number',
        read_only=True
    )
    net_amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True
    )

    class Meta:
        model = BookingPayment
        fields = (
            'id',
            'booking',
            'booking_number',
            'payment_type',
            'gateway',
            'amount',
            'currency',
            'reference',
            'gateway_reference',
            'status',
            'paid_by',
            'paid_by_name',
            'paid_at',
            'refunded_amount',
            'refunded_at',
            'refund_reason',
            'net_amount',
            'notes',
            'created_at',
        )
        read_only_fields = (
            'id',
            'reference',
            'net_amount',
            'created_at',
        )


class BookingGuestSerializer(serializers.ModelSerializer):
    class Meta:
        model = BookingGuest
        fields = (
            'id',
            'booking',
            'guest_type',
            'full_name',
            'email',
            'phone',
            'date_of_birth',
            'id_type',
            'id_number',
            'nationality',
            'special_needs',
            'created_at',
        )
        read_only_fields = ('id', 'created_at')


class BookingCouponSerializer(serializers.ModelSerializer):
    business_name = serializers.CharField(
        source='business.name',
        read_only=True
    )
    item_name = serializers.CharField(
        source='item.name',
        read_only=True
    )
    is_valid = serializers.BooleanField(read_only=True)
    created_by_name = serializers.CharField(
        source='created_by.full_name',
        read_only=True
    )

    class Meta:
        model = BookingCoupon
        fields = (
            'id',
            'business',
            'business_name',
            'item',
            'item_name',
            'code',
            'name',
            'description',
            'discount_type',
            'discount_value',
            'max_discount_amount',
            'min_booking_amount',
            'min_nights',
            'usage_limit',
            'per_user_limit',
            'total_uses',
            'valid_from',
            'valid_until',
            'status',
            'total_discount_given',
            'total_revenue_generated',
            'is_valid',
            'created_by',
            'created_by_name',
            'created_at',
        )
        read_only_fields = (
            'id',
            'total_uses',
            'total_discount_given',
            'total_revenue_generated',
            'is_valid',
            'created_at',
        )


class CouponUsageSerializer(serializers.ModelSerializer):
    coupon_code = serializers.CharField(
        source='coupon.code',
        read_only=True
    )
    user_name = serializers.CharField(
        source='user.full_name',
        read_only=True
    )

    class Meta:
        model = CouponUsage
        fields = (
            'id',
            'coupon',
            'coupon_code',
            'booking',
            'user',
            'user_name',
            'discount_amount',
            'created_at',
        )
        read_only_fields = ('id', 'created_at')


class BookingInvoiceSerializer(serializers.ModelSerializer):
    booking_number = serializers.CharField(
        source='booking.booking_number',
        read_only=True
    )

    class Meta:
        model = BookingInvoice
        fields = (
            'id',
            'booking',
            'booking_number',
            'invoice_number',
            'status',
            'billed_to_name',
            'billed_to_email',
            'billed_to_phone',
            'billed_to_address',
            'business_name',
            'business_address',
            'business_phone',
            'business_email',
            'line_items',
            'subtotal',
            'discount_amount',
            'tax_rate',
            'tax_amount',
            'total',
            'currency',
            'issue_date',
            'due_date',
            'paid_date',
            'pdf_url',
            'notes',
            'terms',
            'created_at',
        )
        read_only_fields = (
            'id',
            'invoice_number',
            'created_at',
        )


class BookingReminderSerializer(serializers.ModelSerializer):
    recipient_name = serializers.CharField(
        source='recipient.full_name',
        read_only=True
    )
    booking_number = serializers.CharField(
        source='booking.booking_number',
        read_only=True
    )

    class Meta:
        model = BookingReminder
        fields = (
            'id',
            'booking',
            'booking_number',
            'reminder_type',
            'channel',
            'send_at',
            'title',
            'message',
            'status',
            'sent_at',
            'error_message',
            'recipient',
            'recipient_name',
            'created_at',
        )
        read_only_fields = (
            'id',
            'status',
            'sent_at',
            'error_message',
            'created_at',
        )