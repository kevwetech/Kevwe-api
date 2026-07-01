from rest_framework import serializers
from .models import (
    ServiceCategory, Service, ServiceProvider,
    ServiceProviderAvailability, ProviderSkill,
    ProviderCertification, ProviderVehicle,
    ServiceRequest, ServiceRequestAttachment,
    ServiceRequestOffer, ServiceQuote, ServicePart,
    CompletionEvidence, ServiceRequestTracking,
    ServiceRating,
)


class ServiceCategorySerializer(serializers.ModelSerializer):
    services_count = serializers.SerializerMethodField()

    class Meta:
        model = ServiceCategory
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')

    def get_services_count(self, obj):
        return obj.services.filter(is_active=True).count()


class ServiceSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(
        source='category.name', read_only=True
    )
    providers_count = serializers.SerializerMethodField()

    class Meta:
        model = Service
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')

    def get_providers_count(self, obj):
        return obj.providers.filter(status='verified').count()


class ServiceProviderAvailabilitySerializer(
    serializers.ModelSerializer
):
    class Meta:
        model = ServiceProviderAvailability
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')


class ProviderSkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProviderSkill
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')


class ProviderCertificationSerializer(
    serializers.ModelSerializer
):
    class Meta:
        model = ProviderCertification
        fields = '__all__'
        read_only_fields = (
            'id', 'status', 'verified_by',
            'verified_at', 'created_at', 'updated_at'
        )


class ProviderVehicleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProviderVehicle
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')


class ServiceProviderSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(
        source='user.full_name', read_only=True
    )
    user_email = serializers.CharField(
        source='user.email', read_only=True
    )
    user_phone = serializers.CharField(
        source='user.phone', read_only=True
    )
    services_detail = ServiceSerializer(
        source='services', many=True, read_only=True
    )
    availability_schedule = (
        ServiceProviderAvailabilitySerializer(
            many=True, read_only=True
        )
    )
    skills = ProviderSkillSerializer(many=True, read_only=True)
    certifications = ProviderCertificationSerializer(
        many=True, read_only=True
    )
    vehicles = ProviderVehicleSerializer(
        many=True, read_only=True
    )
    is_verified = serializers.BooleanField(read_only=True)

    class Meta:
        model = ServiceProvider
        fields = '__all__'
        read_only_fields = (
            'id', 'status', 'rating', 'total_ratings',
            'total_jobs_completed', 'total_earnings',
            'created_at', 'updated_at'
        )


class ServicePartSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServicePart
        fields = '__all__'
        read_only_fields = (
            'id', 'total_price',
            'created_at', 'updated_at'
        )


class ServiceQuoteSerializer(serializers.ModelSerializer):
    parts = ServicePartSerializer(many=True, read_only=True)
    revisions_count = serializers.SerializerMethodField()

    class Meta:
        model = ServiceQuote
        fields = '__all__'
        read_only_fields = (
            'id', 'revision_number', 'status',
            'responded_at', 'created_at', 'updated_at'
        )

    def get_revisions_count(self, obj):
        return obj.revisions.count()


class ServiceRequestAttachmentSerializer(
    serializers.ModelSerializer
):
    class Meta:
        model = ServiceRequestAttachment
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')


class ServiceRequestOfferSerializer(
    serializers.ModelSerializer
):
    provider_name = serializers.CharField(
        source='provider.business_name', read_only=True
    )
    provider_rating = serializers.DecimalField(
        source='provider.rating',
        max_digits=3, decimal_places=2,
        read_only=True
    )

    class Meta:
        model = ServiceRequestOffer
        fields = '__all__'
        read_only_fields = (
            'id', 'sent_at', 'responded_at',
            'created_at', 'updated_at'
        )


class ServiceRequestTrackingSerializer(
    serializers.ModelSerializer
):
    updated_by_name = serializers.CharField(
        source='updated_by.full_name', read_only=True
    )

    class Meta:
        model = ServiceRequestTracking
        fields = '__all__'
        read_only_fields = ('id', 'created_at')


class ServiceRatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceRating
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')


class CompletionEvidenceSerializer(
    serializers.ModelSerializer
):
    class Meta:
        model = CompletionEvidence
        fields = '__all__'
        read_only_fields = (
            'id', 'otp_verified', 'otp_verified_at',
            'created_at', 'updated_at'
        )


class ServiceRequestSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(
        source='customer.full_name', read_only=True
    )
    customer_phone = serializers.CharField(
        source='customer.phone', read_only=True
    )
    service_name = serializers.CharField(
        source='service.name', read_only=True
    )
    provider_name = serializers.CharField(
        source='provider.business_name', read_only=True
    )
    provider_phone = serializers.CharField(
        source='provider.user.phone', read_only=True
    )
    provider_rating = serializers.DecimalField(
        source='provider.rating',
        max_digits=3, decimal_places=2,
        read_only=True
    )
    quotes = ServiceQuoteSerializer(many=True, read_only=True)
    tracking = ServiceRequestTrackingSerializer(
        many=True, read_only=True
    )
    attachments = ServiceRequestAttachmentSerializer(
        many=True, read_only=True
    )
    offers_count = serializers.SerializerMethodField()

    class Meta:
        model = ServiceRequest
        fields = '__all__'
        read_only_fields = (
            'id', 'reference', 'status', 'provider',
            'accepted_at', 'provider_arrived_at',
            'started_at', 'completed_at',
            'final_total', 'platform_commission',
            'provider_earnings', 'payment_status',
            'created_at', 'updated_at'
        )

    def get_offers_count(self, obj):
        return obj.offers.count()


class CreateServiceRequestSerializer(serializers.Serializer):
    service_id = serializers.IntegerField()
    description = serializers.CharField()
    urgency = serializers.ChoiceField(
        choices=['low', 'medium', 'high', 'emergency'],
        default='medium'
    )
    budget = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False
    )
    location_address = serializers.CharField()
    location_lat = serializers.DecimalField(
        max_digits=9, decimal_places=6
    )
    location_lng = serializers.DecimalField(
        max_digits=9, decimal_places=6
    )
    scheduled_date = serializers.DateField(required=False)
    scheduled_time = serializers.TimeField(required=False)