from rest_framework import serializers
from .models import (
    KYCConfiguration, KYCRequirement, KYCProfile,
    KYCSession, KYCDocument, KYCSelfie, KYCMatch,
    KYCIdentity, KYCAddress, KYCWatchlist, KYCConsent,
    KYCWebhook, BusinessKYC, BusinessKYCDocument,
    KYCDuplicateIdentity, KYCReviewLog,
)


class KYCConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = KYCConfiguration
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')


class KYCRequirementSerializer(serializers.ModelSerializer):
    class Meta:
        model = KYCRequirement
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')


class KYCDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = KYCDocument
        fields = '__all__'
        read_only_fields = (
            'id', 'sumsub_document_id', 'status',
            'verified', 'rejection_reason',
            'extracted_name', 'extracted_dob',
            'extracted_expiry', 'created_at', 'updated_at'
        )


class KYCSelfieSerializer(serializers.ModelSerializer):
    class Meta:
        model = KYCSelfie
        fields = '__all__'
        read_only_fields = (
            'id', 'sumsub_selfie_id', 'status',
            'liveness_score', 'face_match_score',
            'rejection_reason', 'created_at', 'updated_at'
        )


class KYCMatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = KYCMatch
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')


class KYCSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = KYCSession
        fields = '__all__'
        read_only_fields = (
            'id', 'started_at', 'created_at', 'updated_at'
        )


class KYCConsentSerializer(serializers.ModelSerializer):
    class Meta:
        model = KYCConsent
        fields = '__all__'
        read_only_fields = (
            'id', 'accepted_at', 'created_at', 'updated_at'
        )


class KYCAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = KYCAddress
        fields = '__all__'
        read_only_fields = (
            'id', 'status', 'verified',
            'created_at', 'updated_at'
        )


class KYCWatchlistSerializer(serializers.ModelSerializer):
    reviewed_by_name = serializers.CharField(
        source='reviewed_by.full_name', read_only=True
    )

    class Meta:
        model = KYCWatchlist
        fields = '__all__'
        read_only_fields = (
            'id', 'created_at', 'updated_at'
        )


class KYCWebhookSerializer(serializers.ModelSerializer):
    class Meta:
        model = KYCWebhook
        fields = '__all__'
        read_only_fields = (
            'id', 'received_at', 'processed_at',
            'created_at', 'updated_at'
        )


class KYCReviewLogSerializer(serializers.ModelSerializer):
    performed_by_name = serializers.CharField(
        source='performed_by.full_name', read_only=True
    )

    class Meta:
        model = KYCReviewLog
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')


class KYCIdentitySerializer(serializers.ModelSerializer):
    accounts_count = serializers.SerializerMethodField()
    is_duplicate = serializers.BooleanField(read_only=True)

    class Meta:
        model = KYCIdentity
        exclude = ('document_hash', 'users')
        read_only_fields = (
            'id', 'first_seen_at', 'last_seen_at',
            'created_at', 'updated_at'
        )

    def get_accounts_count(self, obj):
        return obj.users.count()


class KYCDuplicateIdentitySerializer(
    serializers.ModelSerializer
):
    identity_type = serializers.CharField(
        source='identity.document_type', read_only=True
    )
    identity_masked = serializers.CharField(
        source='identity.document_number_masked',
        read_only=True
    )
    users_count = serializers.SerializerMethodField()

    class Meta:
        model = KYCDuplicateIdentity
        fields = '__all__'
        read_only_fields = (
            'id', 'created_at', 'updated_at'
        )

    def get_users_count(self, obj):
        return obj.users.count()


class BusinessKYCDocumentSerializer(
    serializers.ModelSerializer
):
    class Meta:
        model = BusinessKYCDocument
        fields = '__all__'
        read_only_fields = (
            'id', 'status', 'verified',
            'rejection_reason', 'created_at', 'updated_at'
        )


class BusinessKYCSerializer(serializers.ModelSerializer):
    business_name = serializers.CharField(
        source='business.name', read_only=True
    )
    submitted_by_name = serializers.CharField(
        source='submitted_by.full_name', read_only=True
    )
    reviewed_by_name = serializers.CharField(
        source='reviewed_by.full_name', read_only=True
    )
    documents = BusinessKYCDocumentSerializer(
        many=True, read_only=True
    )
    is_verified = serializers.BooleanField(read_only=True)

    class Meta:
        model = BusinessKYC
        fields = '__all__'
        read_only_fields = (
            'id', 'sumsub_company_id', 'approved_at',
            'reviewed_at', 'created_at', 'updated_at'
        )


class KYCProfileSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(
        source='user.email', read_only=True
    )
    user_name = serializers.CharField(
        source='user.full_name', read_only=True
    )
    documents = KYCDocumentSerializer(
        many=True, read_only=True
    )
    selfies = KYCSelfieSerializer(
        many=True, read_only=True
    )
    sessions_count = serializers.SerializerMethodField()
    is_verified = serializers.BooleanField(read_only=True)
    is_pending = serializers.BooleanField(read_only=True)

    class Meta:
        model = KYCProfile
        fields = '__all__'
        read_only_fields = (
            'id', 'sumsub_applicant_id',
            'sumsub_inspection_id',
            'sumsub_correlation_id',
            'sumsub_review_result', 'last_webhook',
            'rejection_labels', 'reviewed_by',
            'reviewed_at', 'approved_at', 'risk_level',
            'verified_first_name', 'verified_last_name',
            'verified_dob', 'verified_gender',
            'verified_address', 'verified_nationality',
            'submitted_at', 'processing_started_at',
            'created_at', 'updated_at'
        )

    def get_sessions_count(self, obj):
        return obj.sessions.count()