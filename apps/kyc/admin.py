from django.contrib import admin
from .models import (
    KYCConfiguration, KYCRequirement, KYCProfile,
    KYCSession, KYCDocument, KYCSelfie, KYCMatch,
    KYCIdentity, KYCAddress, KYCWatchlist, KYCConsent,
    KYCWebhook, BusinessKYC, BusinessKYCDocument,
    KYCDuplicateIdentity, KYCReviewLog,
)


@admin.register(KYCConfiguration)
class KYCConfigurationAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'kyc_version', 'max_retry_count',
        'auto_approve_threshold', 'kyc_expiry_days',
        'is_active'
    )


@admin.register(KYCRequirement)
class KYCRequirementAdmin(admin.ModelAdmin):
    list_display = (
        'use_case', 'required_documents', 'is_active'
    )


@admin.register(KYCProfile)
class KYCProfileAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'use_case', 'status',
        'verification_method', 'confidence_score',
        'retry_count', 'approved_at', 'created_at'
    )
    list_filter = ('status', 'use_case', 'verification_method')
    search_fields = ('user__email', 'sumsub_applicant_id')
    readonly_fields = (
        'sumsub_applicant_id', 'sumsub_review_result',
        'last_webhook', 'approved_at', 'reviewed_at',
        'submitted_at', 'processing_started_at',
        'created_at', 'updated_at'
    )


@admin.register(KYCSession)
class KYCSessionAdmin(admin.ModelAdmin):
    list_display = (
        'kyc_profile', 'status', 'ip_address',
        'browser', 'started_at', 'completed_at'
    )
    list_filter = ('status',)


@admin.register(KYCDocument)
class KYCDocumentAdmin(admin.ModelAdmin):
    list_display = (
        'kyc_profile', 'document_type', 'status',
        'verified', 'created_at'
    )
    list_filter = ('document_type', 'status', 'verified')
    search_fields = ('kyc_profile__user__email',)


@admin.register(KYCSelfie)
class KYCSelfieAdmin(admin.ModelAdmin):
    list_display = (
        'kyc_profile', 'status', 'liveness_score',
        'face_match_score', 'created_at'
    )
    list_filter = ('status',)


@admin.register(KYCMatch)
class KYCMatchAdmin(admin.ModelAdmin):
    list_display = (
        'kyc_profile', 'score', 'passed',
        'method', 'created_at'
    )
    list_filter = ('passed', 'method')


@admin.register(KYCIdentity)
class KYCIdentityAdmin(admin.ModelAdmin):
    list_display = (
        'document_type', 'document_number_masked',
        'country', 'verified', 'is_duplicate',
        'first_seen_at'
    )
    list_filter = ('document_type', 'verified')
    search_fields = ('document_number_masked',)


@admin.register(KYCAddress)
class KYCAddressAdmin(admin.ModelAdmin):
    list_display = (
        'kyc_profile', 'city', 'country',
        'status', 'verified'
    )
    list_filter = ('status', 'verified')


@admin.register(KYCWatchlist)
class KYCWatchlistAdmin(admin.ModelAdmin):
    list_display = (
        'kyc_profile', 'watchlist_type', 'status',
        'matched', 'confidence', 'source'
    )
    list_filter = ('watchlist_type', 'status', 'matched')


@admin.register(KYCConsent)
class KYCConsentAdmin(admin.ModelAdmin):
    list_display = (
        'kyc_profile', 'accepted', 'consent_version',
        'ip_address', 'accepted_at'
    )
    list_filter = ('accepted', 'consent_version')


@admin.register(KYCWebhook)
class KYCWebhookAdmin(admin.ModelAdmin):
    list_display = (
        'source', 'event_type', 'applicant_id',
        'processed', 'received_at', 'processed_at'
    )
    list_filter = ('source', 'processed')
    search_fields = ('applicant_id', 'event_type')
    readonly_fields = ('received_at', 'payload')


@admin.register(BusinessKYC)
class BusinessKYCAdmin(admin.ModelAdmin):
    list_display = (
        'business', 'status', 'submitted_by',
        'approved_at', 'created_at'
    )
    list_filter = ('status',)
    search_fields = ('business__name',)


@admin.register(BusinessKYCDocument)
class BusinessKYCDocumentAdmin(admin.ModelAdmin):
    list_display = (
        'business_kyc', 'document_type', 'status',
        'verified', 'expiry_date'
    )
    list_filter = ('document_type', 'status', 'verified')


@admin.register(KYCDuplicateIdentity)
class KYCDuplicateIdentityAdmin(admin.ModelAdmin):
    list_display = (
        'identity', 'status', 'confidence',
        'fraud_alert', 'created_at'
    )
    list_filter = ('status',)


@admin.register(KYCReviewLog)
class KYCReviewLogAdmin(admin.ModelAdmin):
    list_display = (
        'kyc_profile', 'action', 'performed_by',
        'is_system_action', 'created_at'
    )
    list_filter = ('action', 'is_system_action')
    search_fields = ('kyc_profile__user__email',)