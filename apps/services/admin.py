from django.contrib import admin
from .models import (
    ServiceCategory, Service, ServiceProvider,
    ServiceProviderAvailability, ProviderSkill,
    ProviderCertification, ProviderVehicle,
    ServiceRequest, ServiceRequestAttachment,
    ServiceRequestOffer, ServiceQuote, ServicePart,
    CompletionEvidence, ServiceRequestTracking,
    ServiceRating,
)

admin.site.register(ServiceCategory)
admin.site.register(Service)

@admin.register(ServiceProvider)
class ServiceProviderAdmin(admin.ModelAdmin):
    list_display = (
        'business_name', 'user', 'provider_type',
        'status', 'rating', 'total_jobs_completed',
        'is_available', 'is_online'
    )
    list_filter = ('status', 'provider_type', 'is_available')
    search_fields = ('business_name', 'user__email')

admin.site.register(ServiceProviderAvailability)
admin.site.register(ProviderSkill)
admin.site.register(ProviderCertification)
admin.site.register(ProviderVehicle)

@admin.register(ServiceRequest)
class ServiceRequestAdmin(admin.ModelAdmin):
    list_display = (
        'reference', 'service', 'customer',
        'provider', 'status', 'urgency',
        'final_total', 'created_at'
    )
    list_filter = ('status', 'urgency', 'pricing_type')
    search_fields = ('reference', 'customer__email')

admin.site.register(ServiceRequestAttachment)
admin.site.register(ServiceRequestOffer)

@admin.register(ServiceQuote)
class ServiceQuoteAdmin(admin.ModelAdmin):
    list_display = (
        'service_request', 'revision_number',
        'total', 'status', 'created_at'
    )
    list_filter = ('status',)

admin.site.register(ServicePart)
admin.site.register(CompletionEvidence)
admin.site.register(ServiceRequestTracking)
admin.site.register(ServiceRating)