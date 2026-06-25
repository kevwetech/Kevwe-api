from rest_framework import serializers
from .models import (
    Industry, Business, BusinessHours, BusinessImage,
    BusinessDocument, Permission, BusinessRole, BusinessStaff,
)


class IndustrySerializer(serializers.ModelSerializer):
    business_count = serializers.SerializerMethodField()

    class Meta:
        model = Industry
        fields = (
            'id',
            'name',
            'slug',
            'description',
            'icon',
            'image',
            'status',
            'platform_commission',
            'driver_commission',
            'vendor_commission',
            'is_featured',
            'order',
            'business_count',
            'created_at',
        )
        read_only_fields = ('id', 'created_at')

    def get_business_count(self, obj):
        return obj.businesses.filter(
            status='active',
            is_active=True
        ).count()


class BusinessHoursSerializer(serializers.ModelSerializer):
    day_name = serializers.CharField(
        source='get_day_display',
        read_only=True
    )

    class Meta:
        model = BusinessHours
        fields = (
            'id',
            'day',
            'day_name',
            'is_open',
            'opening_time',
            'closing_time',
        )
        read_only_fields = ('id',)


class BusinessImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessImage
        fields = (
            'id',
            'image',
            'caption',
            'is_primary',
            'order',
        )
        read_only_fields = ('id',)


class BusinessDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessDocument
        fields = (
            'id',
            'document_type',
            'document_file',
            'status',
            'notes',
            'created_at',
        )
        read_only_fields = ('id', 'status', 'notes', 'created_at')





class BusinessSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(
        source='owner.full_name',
        read_only=True
    )
    industry_name = serializers.CharField(
        source='industry.name',
        read_only=True
    )
    industry_icon = serializers.CharField(
        source='industry.icon',
        read_only=True
    )
    city_name = serializers.CharField(
        source='city.name',
        read_only=True
    )
    state_name = serializers.CharField(
        source='state.name',
        read_only=True
    )
    hours = BusinessHoursSerializer(
        many=True,
        read_only=True
    )
    images = BusinessImageSerializer(
        many=True,
        read_only=True
    )
    commission_rate = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        read_only=True
    )

    class Meta:
        model = Business
        fields = (
            'id',
            'owner',
            'owner_name',
            'industry',
            'industry_name',
            'industry_icon',
            'name',
            'slug',
            'description',
            'tagline',
            'logo',
            'cover_image',
            'email',
            'phone',
            'whatsapp',
            'website',
            'address',
            'country',
            'state',
            'state_name',
            'city',
            'city_name',
            'zone',
            'latitude',
            'longitude',
            'opening_time',
            'closing_time',
            'working_days',
            'is_open_now',
            'accepts_orders',
            'delivery_available',
            'pickup_available',
            'min_order_amount',
            'delivery_time_minutes',
            'delivery_radius_km',
            'delivery_fee',
            'commission_rate',
            'status',
            'total_orders',
            'total_revenue',
            'rating',
            'total_ratings',
            'is_featured',
            'is_verified',
            'is_active',
            'tags',
            'hours',
            'images',
            'created_at',
        )
        read_only_fields = (
            'id',
            'status',
            'total_orders',
            'total_revenue',
            'rating',
            'total_ratings',
            'is_verified',
            'created_at',
        )



class CreateBusinessSerializer(serializers.Serializer):
    industry_id = serializers.IntegerField()
    name = serializers.CharField()
    slug = serializers.SlugField()
    description = serializers.CharField(
        required=False,
        allow_blank=True
    )
    tagline = serializers.CharField(
        required=False,
        allow_blank=True
    )
    email = serializers.EmailField(required=False)
    phone = serializers.CharField()
    whatsapp = serializers.CharField(
        required=False,
        allow_blank=True
    )
    address = serializers.CharField()
    city_id = serializers.IntegerField(required=False)
    state_id = serializers.IntegerField(required=False)
    country_id = serializers.IntegerField(required=False)
    latitude = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        required=False
    )
    longitude = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        required=False
    )
    delivery_available = serializers.BooleanField(
        default=True
    )
    pickup_available = serializers.BooleanField(
        default=True
    )
    min_order_amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    delivery_fee = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    delivery_time_minutes = serializers.IntegerField(
        default=30
    )
    delivery_radius_km = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=5.00
    )
    tags = serializers.ListField(
        child=serializers.CharField(),
        required=False
    )



class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Permission
        fields = '__all__'


class BusinessRoleSerializer(serializers.ModelSerializer):
    permissions = PermissionSerializer(many=True, read_only=True)
    permission_ids = serializers.PrimaryKeyRelatedField(
        queryset=Permission.objects.filter(is_active=True),
        many=True,
        write_only=True,
        source='permissions',
        required=False,
    )

    class Meta:
        model  = BusinessRole
        fields = [
            'id', 'business', 'name', 'description',
            'permissions', 'permission_ids',
            'is_active', 'is_default',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['business']

    def create(self, validated_data):
        permissions = validated_data.pop('permissions', [])
        role = BusinessRole.objects.create(**validated_data)
        role.permissions.set(permissions)
        return role

    def update(self, instance, validated_data):
        permissions = validated_data.pop('permissions', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if permissions is not None:
            instance.permissions.set(permissions)
        return instance


class BusinessStaffSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(
        source='user.full_name',
        read_only=True
    )
    user_email = serializers.CharField(
        source='user.email',
        read_only=True
    )
    user_phone = serializers.CharField(
        source='user.phone',
        read_only=True
    )
    user_avatar = serializers.ImageField(
        source='user.avatar',
        read_only=True
    )
    business_name = serializers.CharField(
        source='business.name',
        read_only=True
    )
    invited_by_name = serializers.CharField(
        source='invited_by.full_name',
        read_only=True
    )
    is_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = BusinessStaff
        fields = (
            'id',
            'business',
            'business_name',
            'user',
            'user_name',
            'user_email',
            'user_phone',
            'user_avatar',
            'role',
            'status',
            'can_manage_menu',
            'can_manage_orders',
            'can_manage_staff',
            'can_view_reports',
            'can_manage_settings',
            'can_process_refunds',
            'invitation_status',
            'invited_by',
            'invited_by_name',
            'invitation_expires_at',
            'joined_at',
            'notes',
            'is_active',
            'created_at',
        )
        read_only_fields = (
            'id',
            'invitation_token',
            'invitation_status',
            'joined_at',
            'created_at',
        )


class InviteStaffSerializer(serializers.Serializer):
    email   = serializers.EmailField()
    role_id = serializers.PrimaryKeyRelatedField(
        queryset=BusinessRole.objects.filter(is_active=True)
    )
    notes   = serializers.CharField(required=False, allow_blank=True)
    