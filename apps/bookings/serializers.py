from rest_framework import serializers
from django.utils import timezone
from .models import BookableItem, Booking


class BookableItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = BookableItem
        fields = (
            'id',
            'name',
            'description',
            'item_type',
            'price_per_unit',
            'unit_label',
            'capacity',
            'image',
            'is_available',
            'is_active',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')


class BookingSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(
        source='item.name',
        read_only=True
    )
    item_type = serializers.CharField(
        source='item.item_type',
        read_only=True
    )

    class Meta:
        model = Booking
        fields = (
            'id',
            'reference',
            'item',
            'item_name',
            'item_type',
            'status',
            'payment_status',
            'check_in',
            'check_out',
            'duration',
            'guests',
            'guest_name',
            'guest_email',
            'guest_phone',
            'price_per_unit',
            'total',
            'special_requests',
            'created_at',
            'updated_at',
        )
        read_only_fields = (
            'id',
            'reference',
            'status',
            'payment_status',
            'duration',
            'price_per_unit',
            'total',
            'created_at',
            'updated_at',
        )


class CreateBookingSerializer(serializers.Serializer):
    item_id = serializers.IntegerField()
    check_in = serializers.DateField()
    check_out = serializers.DateField()
    guests = serializers.IntegerField(min_value=1, default=1)
    guest_name = serializers.CharField()
    guest_email = serializers.EmailField()
    guest_phone = serializers.CharField()
    special_requests = serializers.CharField(
        required=False,
        allow_blank=True
    )

    def validate(self, attrs):
        check_in = attrs['check_in']
        check_out = attrs['check_out']

        # Check dates
        if check_in >= check_out:
            raise serializers.ValidationError(
                'Check out must be after check in'
            )

        if check_in < timezone.now().date():
            raise serializers.ValidationError(
                'Check in cannot be in the past'
            )

        return attrs

    def validate_item_id(self, value):
        try:
            item = BookableItem.objects.get(
                pk=value,
                is_active=True,
                is_available=True
            )
        except BookableItem.DoesNotExist:
            raise serializers.ValidationError(
                'Item not found or not available'
            )
        return value