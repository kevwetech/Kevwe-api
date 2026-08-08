from rest_framework import serializers
from .models import (
    Industry, BusinessCategory, Business,
    BusinessHours, BusinessImage, BusinessDocument,
    BusinessSettings, OrderSettings,
    BookingSettings, ServiceSettings,
    BusinessSubtype, AppointmentSettings,
    RideSettings, ShipmentSettings,
    BusinessFAQ, BusinessPromotion,
    BusinessPolicy, BusinessContentBlock,
    InteractionForm
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

class BusinessSubtypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessSubtype
        fields = ['id', 'name', 'slug', 'icon', 'interaction_type']

class OrderSettingsSerializer(serializers.ModelSerializer):
    subtype = BusinessSubtypeSerializer(read_only=True)
    subtype_id = serializers.PrimaryKeyRelatedField(
        queryset=BusinessSubtype.objects.filter(interaction_type='orders'),
        source='subtype', write_only=True, required=False
    )
    class Meta:
        model = OrderSettings
        fields = '__all__'
        read_only_fields = ('id', 'business', 'created_at', 'updated_at')
    
class BookingSettingsSerializer(serializers.ModelSerializer):
    subtype = BusinessSubtypeSerializer(read_only=True)
    subtype_id = serializers.PrimaryKeyRelatedField(
        queryset=BusinessSubtype.objects.filter(interaction_type='bookings'),
        source='subtype', write_only=True, required=False
    )
    class Meta:
        model = BookingSettings
        fields = '__all__'
        read_only_fields = ('id', 'business', 'created_at', 'updated_at')

class ServiceSettingsSerializer(serializers.ModelSerializer):
    subtype = BusinessSubtypeSerializer(read_only=True)
    subtype_id = serializers.PrimaryKeyRelatedField(
        queryset=BusinessSubtype.objects.filter(interaction_type='services'),
        source='subtype', write_only=True, required=False
    )
    class Meta:
        model = ServiceSettings
        fields = '__all__'
        read_only_fields = ('id', 'business', 'created_at', 'updated_at')

class AppointmentSettingsSerializer(serializers.ModelSerializer):
    subtype = BusinessSubtypeSerializer(read_only=True)
    subtype_id = serializers.PrimaryKeyRelatedField(
        queryset=BusinessSubtype.objects.filter(interaction_type='appointments'),
        source='subtype', write_only=True, required=False
    )
    class Meta:
        model = AppointmentSettings
        fields = '__all__'
        read_only_fields = ('id', 'business', 'created_at', 'updated_at')

class RideSettingsSerializer(serializers.ModelSerializer):
    subtype = BusinessSubtypeSerializer(read_only=True)
    subtype_id = serializers.PrimaryKeyRelatedField(
        queryset=BusinessSubtype.objects.filter(interaction_type='rides'),
        source='subtype', write_only=True, required=False
    )
    class Meta:
        model = RideSettings
        fields = '__all__'
        read_only_fields = ('id', 'business', 'created_at', 'updated_at')

class ShipmentSettingsSerializer(serializers.ModelSerializer):
    subtype = BusinessSubtypeSerializer(read_only=True)
    subtype_id = serializers.PrimaryKeyRelatedField(
        queryset=BusinessSubtype.objects.filter(interaction_type='scheduled_services'),
        source='subtype', write_only=True, required=False
    )
    class Meta:
        model = ShipmentSettings
        fields = '__all__'
        read_only_fields = ('id', 'business', 'created_at', 'updated_at')

class BusinessSerializer(serializers.ModelSerializer):
    industry_name = serializers.CharField(
        source='industry.name', read_only=True
    )
    industry_interaction_type = serializers.CharField(
        source='industry.interaction_type', read_only=True
    )
    interaction_types = serializers.ReadOnlyField()
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
    faqs = serializers.SerializerMethodField()
    page_promotions = serializers.SerializerMethodField()
    policies = serializers.SerializerMethodField()
    content_blocks = serializers.SerializerMethodField()

    # Nested settings (shown if they exist)
    settings = BusinessSettingsSerializer(read_only=True)
    order_settings = OrderSettingsSerializer(read_only=True)
    booking_settings = BookingSettingsSerializer(read_only=True)
    service_settings = ServiceSettingsSerializer(read_only=True)
    appointment_settings = AppointmentSettingsSerializer(read_only=True)
    ride_settings = RideSettingsSerializer(read_only=True)
    shipment_settings = ShipmentSettingsSerializer(read_only=True)
    verified_badges = serializers.ReadOnlyField()

    class Meta:
        model = Business
        fields = '__all__'
        read_only_fields = (
            'id', 'slug', 'status', 'approved_at',
            'approved_by', 'is_verified',
            'created_at', 'updated_at'
        )

    def get_faqs(self, obj):
        qs = obj.faqs.filter(is_active=True)
        return BusinessFAQSerializer(qs, many=True, context=self.context).data

    def get_page_promotions(self, obj):
        from django.utils import timezone
        from django.db.models import Q
        now = timezone.now()
        qs = obj.page_promotions.filter(is_active=True).filter(
            Q(starts_at__isnull=True) | Q(starts_at__lte=now)
        ).filter(
            Q(ends_at__isnull=True) | Q(ends_at__gte=now)
        )
        return BusinessPromotionSerializer(qs, many=True, context=self.context).data

    def get_policies(self, obj):
        qs = obj.policies.filter(is_active=True)
        return BusinessPolicySerializer(qs, many=True, context=self.context).data

    def get_content_blocks(self, obj):
        qs = obj.content_blocks.filter(is_active=True)
        return BusinessContentBlockSerializer(qs, many=True, context=self.context).data


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
    booking_type = serializers.ChoiceField(
        choices=['hotel','apartment','event_center','resort','guesthouse','coworking'],
        required=False,
        default='hotel',
    )
    latitude = serializers.DecimalField(
        max_digits=9, decimal_places=6, required=False
    )
    longitude = serializers.DecimalField(
        max_digits=9, decimal_places=6, required=False
    )
    tags = serializers.ListField(
        child=serializers.CharField(), required=False
    )

class BusinessFAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessFAQ
        fields = ['id', 'business', 'question', 'answer', 'order', 'is_active']
        read_only_fields = ['business']


class BusinessPromotionSerializer(serializers.ModelSerializer):
    is_live = serializers.ReadOnlyField()

    class Meta:
        model = BusinessPromotion
        fields = ['id', 'business', 'kind', 'title', 'description', 'icon',
                  'image', 'starts_at', 'ends_at', 'cta_label', 'cta_url',
                  'order', 'is_active', 'is_live']
        read_only_fields = ['business']


class BusinessPolicySerializer(serializers.ModelSerializer):
    policy_type_display = serializers.CharField(
        source='get_policy_type_display', read_only=True)

    class Meta:
        model = BusinessPolicy
        fields = ['id', 'business', 'policy_type', 'policy_type_display',
                  'title', 'content', 'icon', 'order', 'is_active']
        read_only_fields = ['business']


class BusinessContentBlockSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessContentBlock
        fields = ['id', 'business', 'title', 'content', 'image',
                  'order', 'is_active']
        read_only_fields = ['business']


class InteractionFormSerializer(serializers.ModelSerializer):
    interaction_type_display = serializers.CharField(
        source='get_interaction_type_display', read_only=True)
    scope_label = serializers.SerializerMethodField()
    industry_name = serializers.CharField(source='industry.name', read_only=True, default=None)
    category_name = serializers.CharField(source='category.name', read_only=True, default=None)
    business_name = serializers.CharField(source='business.name', read_only=True, default=None)

    class Meta:
        model = InteractionForm
        fields = [
            'id', 'interaction_type', 'interaction_type_display',
            'industry', 'industry_name', 'category', 'category_name',
            'business', 'business_name', 'form_key', 'name', 'schema',
            'scope_label', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_scope_label(self, obj):
        return str(obj.business or obj.category or obj.industry or 'unscoped')

    def validate(self, data):
        industry = data.get('industry', getattr(self.instance, 'industry', None))
        category = data.get('category', getattr(self.instance, 'category', None))
        business = data.get('business', getattr(self.instance, 'business', None))
        scopes = [bool(industry), bool(category), bool(business)]
        if sum(scopes) != 1:
            raise serializers.ValidationError(
                'Set exactly one of industry, category or business — '
                'that decides how widely this form applies.')
        return data


class InteractionFormResolveSerializer(serializers.Serializer):
    '''What GET /marketplace/interaction-forms/resolve/ returns —
    the SAME shape business.interaction_forms produces internally,
    exposed standalone for admin preview / debugging.'''
    interaction_type = serializers.CharField()
    form_key = serializers.CharField(allow_null=True)
    name = serializers.CharField(allow_null=True)
    schema = serializers.JSONField(allow_null=True)
    resolved_from = serializers.CharField(allow_null=True)