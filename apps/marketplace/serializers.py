from rest_framework import serializers
from .models import (
    Industry, BusinessCategory, Business,
    BusinessHours, BusinessImage, BusinessDocument,
    BusinessSettings, OrderSettings,
    BookingSettings, ServiceSettings,
)


class IndustrySerializer(serializers.ModelSerializer):
    businesses_count = serializers.SerializerMethodField()
    categories_count = serializers.SerializerMethodField()

    class Meta:
        model = Industry
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')

    def get_businesses_count(self, obj):
        return obj.businesses.filter(
            status='active', is_active=True
        ).count()

    def get_categories_count(self, obj):
        return obj.categories.filter(is_active=True).count()


class BusinessCategorySerializer(serializers.ModelSerializer):
    industry_name = serializers.CharField(
        source='industry.name', read_only=True
    )
    effective_interaction_type = serializers.CharField(
        read_only=True
    )
    businesses_count = serializers.SerializerMethodField()

    class Meta:
        model = BusinessCategory
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')

    def get_businesses_count(self, obj):
        return obj.businesses.filter(
            status='active', is_active=True
        ).count()


class BusinessHoursSerializer(serializers.ModelSerializer):
    day_name = serializers.CharField(
        source='get_day_display', read_only=True
    )

    class Meta:
        model = BusinessHours
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')


class BusinessImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessImage
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')


class BusinessDocumentSerializer(serializers.ModelSerializer):
    verified_by_name = serializers.CharField(
        source='verified_by.full_name', read_only=True
    )

    class Meta:
        model = BusinessDocument
        fields = '__all__'
        read_only_fields = (
            'id', 'status', 'verified_by',
            'verified_at', 'created_at', 'updated_at'
        )


class BusinessSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessSettings
        fields = '__all__'
        read_only_fields = ('id', 'business', 'created_at', 'updated_at')


class OrderSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderSettings
        fields = '__all__'
        read_only_fields = ('id', 'business', 'created_at', 'updated_at')


class BookingSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = BookingSettings
        fields = '__all__'
        read_only_fields = ('id', 'business', 'created_at', 'updated_at')


class ServiceSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceSettings
        fields = '__all__'
        read_only_fields = ('id', 'business', 'created_at', 'updated_at')


class BusinessSerializer(serializers.ModelSerializer):
    industry_name = serializers.CharField(
        source='industry.name', read_only=True
    )
    industry_interaction_type = serializers.CharField(
        source='industry.interaction_type', read_only=True
    )
    category_name = serializers.CharField(
        source='category.name', read_only=True
    )
    owner_name = serializers.CharField(
        source='owner.full_name', read_only=True
    )
    city_name = serializers.CharField(
        source='city.name', read_only=True
    )
    state_name = serializers.CharField(
        source='state.name', read_only=True
    )
    country_name = serializers.CharField(
        source='country.name', read_only=True
    )
    hours = BusinessHoursSerializer(many=True, read_only=True)
    images = BusinessImageSerializer(many=True, read_only=True)
    is_open = serializers.BooleanField(read_only=True)
    interaction_type = serializers.CharField(read_only=True)
    commission_rate = serializers.DecimalField(
        max_digits=5, decimal_places=2, read_only=True
    )

    # Nested settings (shown if they exist)
    settings = BusinessSettingsSerializer(read_only=True)
    order_settings = OrderSettingsSerializer(read_only=True)
    booking_settings = BookingSettingsSerializer(read_only=True)
    service_settings = ServiceSettingsSerializer(read_only=True)

    class Meta:
        model = Business
        fields = '__all__'
        read_only_fields = (
            'id', 'slug', 'status', 'approved_at',
            'approved_by', 'is_verified',
            'created_at', 'updated_at'
        )


class CreateBusinessSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    slug = serializers.SlugField()
    industry_id = serializers.IntegerField()
    category_id = serializers.IntegerField(required=False)
    description = serializers.CharField(required=False)
    tagline = serializers.CharField(required=False)
    phone = serializers.CharField()
    email = serializers.EmailField(required=False)
    whatsapp = serializers.CharField(required=False)
    website = serializers.URLField(required=False)
    address = serializers.CharField()
    city_id = serializers.IntegerField(required=False)
    state_id = serializers.IntegerField(required=False)
    country_id = serializers.IntegerField(required=False)
    latitude = serializers.DecimalField(
        max_digits=9, decimal_places=6, required=False
    )
    longitude = serializers.DecimalField(
        max_digits=9, decimal_places=6, required=False
    )
    tags = serializers.ListField(
        child=serializers.CharField(), required=False
    )