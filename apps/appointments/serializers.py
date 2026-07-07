from rest_framework import serializers
from .models import (
    AppointmentService, AppointmentStaff, AppointmentSlot,
    AppointmentBlock, AppointmentAvailabilityException,
    Appointment, AppointmentTracking, AppointmentPayment,
    AppointmentRating, AppointmentWaitlist, AppointmentReminder,
)


class AppointmentServiceSerializer(serializers.ModelSerializer):
    total_duration_minutes = serializers.IntegerField(read_only=True)

    class Meta:
        model = AppointmentService
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')


class AppointmentStaffSerializer(serializers.ModelSerializer):
    computed_rating = serializers.SerializerMethodField()

    class Meta:
        model = AppointmentStaff
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')

    def get_computed_rating(self, obj):
        return obj.get_rating()


class AppointmentSlotSerializer(serializers.ModelSerializer):
    day_name = serializers.CharField(source='get_day_display', read_only=True)

    class Meta:
        model = AppointmentSlot
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')


class AppointmentBlockSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppointmentBlock
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')


class AppointmentAvailabilityExceptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppointmentAvailabilityException
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')


class AppointmentTrackingSerializer(serializers.ModelSerializer):
    updated_by_name = serializers.CharField(
        source='updated_by.full_name', read_only=True
    )

    class Meta:
        model = AppointmentTracking
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')


class AppointmentPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppointmentPayment
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')


class AppointmentRatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppointmentRating
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')


class AppointmentReminderSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppointmentReminder
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')


class AppointmentWaitlistSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(
        source='customer.full_name', read_only=True
    )
    service_name = serializers.CharField(
        source='service.name', read_only=True
    )

    class Meta:
        model = AppointmentWaitlist
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')


class AppointmentSerializer(serializers.ModelSerializer):
    tracking = AppointmentTrackingSerializer(many=True, read_only=True)
    payments = AppointmentPaymentSerializer(many=True, read_only=True)
    rating   = AppointmentRatingSerializer(read_only=True)
    reminders = AppointmentReminderSerializer(many=True, read_only=True)

    class Meta:
        model = Appointment
        fields = '__all__'
        read_only_fields = (
            'id', 'reference', 'check_in_code',
            'service_name', 'service_price',
            'staff_name', 'customer_name',
            'customer_phone', 'customer_email',
            'platform_commission', 'business_earnings',
            'staff_commission', 'created_at', 'updated_at',
        )


# ── Input serializers ─────────────────────────────
class BookAppointmentSerializer(serializers.Serializer):
    business_id   = serializers.IntegerField()
    service_id    = serializers.IntegerField()
    staff_id      = serializers.IntegerField(required=False)
    date          = serializers.DateField()
    start_time    = serializers.TimeField()
    payment_method= serializers.ChoiceField(
        choices=['card', 'wallet', 'cash', 'transfer'],
        default='card'
    )
    customer_note = serializers.CharField(required=False, allow_blank=True)


class CheckInSerializer(serializers.Serializer):
    check_in_code = serializers.CharField()


class RateAppointmentSerializer(serializers.Serializer):
    overall_rating     = serializers.IntegerField(min_value=1, max_value=5)
    staff_rating       = serializers.IntegerField(min_value=1, max_value=5, required=False)
    cleanliness_rating = serializers.IntegerField(min_value=1, max_value=5, required=False)
    value_rating       = serializers.IntegerField(min_value=1, max_value=5, required=False)
    review             = serializers.CharField(required=False, allow_blank=True)